#
# Copyright (C) 2026 Dan Brown
# SPDX-License-Identifier: GPL-3.0-or-later
#
# The broker (DESIGN.md, Runtime, The broker): the only process that holds
# this module's NS8 credentials on behalf of the API service. It runs in its
# own container (dnsapi-broker.service), with agent.env mounted read-only;
# the API container, which faces the internet, has no credentials and asks it
# over a Unix socket in a directory both mount to run a task. It runs only the
# tasks the API needs:
#
#   request  {"target": "dnshelper" | "self", "action", "data"}   one JSON line
#   answer   {"exit_code", "output", "error"}  or  {"refused": why}  or  {"unavailable": why}
#            (why: dnshelper_missing, not_granted, timeout, api_server, broker_error)
#
# A compromised service can then do what its API allows, and nothing else:
# no Traefik route, no other action of this module, no other module.

import json
import logging
import os
import signal
import socketserver
import sys
import threading

from . import apiclient

log = logging.getLogger("dnsapi-broker")

MAX_REQUEST = 2 * 1024 * 1024
MAX_TASKS = 16

DNSHELPER_READ = {"list-zones", "get-records", "list-owners", "check-propagation", "list-providers"}
DNSHELPER_WRITE = {"append-records", "set-records", "delete-records", "apply-changes"}
# As one of dnshelper's delegates (DESIGN.md, Phase 2): domains added through the API with
# the customer's credentials. dnshelper limits them to dnsapi's own credentials and zones.
# update-zone points a hosted zone at new credentials; update-credential is left out
# (dnsapi replaces a credential rather than changing it in place).
DNSHELPER_DELEGATE = {"validate-zone", "list-provider-zones", "add-credential", "remove-credential",
                      "add-zone", "update-zone", "remove-zone"}
SELF_ACTIONS = {"add-tenant", "update-tenant", "remove-tenant", "assign-zone", "unassign-zone",
                "create-key", "update-key", "revoke-key", "revoke-exposed-key"}


def check(target, action, data):
    """None when the request is allowed, else why it is refused."""
    if not isinstance(data, dict):
        return "data must be an object"
    if target == "dnshelper":
        if action in DNSHELPER_READ or action in DNSHELPER_DELEGATE:
            return None
        if action in DNSHELPER_WRITE:
            # Records written through the API are the tenant's, never dnsapi's own.
            behalf = data.get("on_behalf_of")
            if not isinstance(behalf, str) or not behalf:
                return f"{action} without on_behalf_of"
            return None
        return f"dnshelper action {action} is not allowed"
    if target == "self":
        if action not in SELF_ACTIONS:
            return f"action {action} is not allowed"
        if action == "create-key" and data.get("owner") == "operator":
            return "operator keys are made by an administrator"
        return None
    return f"unknown target {target}"


class Broker:
    def __init__(self, find_dnshelper, self_agent, client, max_tasks=MAX_TASKS):
        self.find_dnshelper = find_dnshelper  # () -> "module/dnshelper1" or None
        self.self_agent = self_agent  # () -> "module/dnsapi1"
        self.client = client
        self.slots = threading.BoundedSemaphore(max_tasks)

    def handle(self, request):
        target = request.get("target")
        action = request.get("action")
        data = request.get("data", {})
        why = check(target, action, data)
        if why:
            log.warning("refused: %s", why)
            return {"refused": why}
        if target == "dnshelper":
            agent_id = self.find_dnshelper()
            if not agent_id:
                return {"unavailable": "dnshelper_missing"}
        else:
            agent_id = self.self_agent()
        with self.slots:
            try:
                return self.client.run(agent_id, action, data)
            except apiclient.Timeout as exc:
                log.error("%s", exc)
                return {"unavailable": "timeout"}
            except apiclient.Unreachable as exc:
                log.error("%s", exc)
                if exc.status == 403:
                    # The api-server refused the action itself: this module's role on
                    # that dnshelper does not include it (an older dnshelper).
                    return {"unavailable": "not_granted"}
                return {"unavailable": "api_server"}


class Handler(socketserver.StreamRequestHandler):
    def handle(self):
        line = self.rfile.readline(MAX_REQUEST + 1)
        try:
            if len(line) > MAX_REQUEST:
                raise ValueError("request too large")
            request = json.loads(line)
            if not isinstance(request, dict):
                raise ValueError("not an object")
            answer = self.server.broker.handle(request)
        except ValueError as exc:
            answer = {"refused": f"bad request: {exc}"}
        except Exception:
            log.exception("broker error")
            answer = {"unavailable": "broker_error"}
        self.wfile.write(json.dumps(answer).encode() + b"\n")


class Server(socketserver.ThreadingUnixStreamServer):
    daemon_threads = True

    def __init__(self, path, broker):
        if os.path.exists(path):
            os.unlink(path)
        old = os.umask(0o177)  # the socket is 0600: only this module's uid connects
        try:
            super().__init__(path, Handler)
        finally:
            os.umask(old)
        self.broker = broker


def main(argv):
    import argparse

    parser = argparse.ArgumentParser(prog="dnsapi-server broker")
    parser.add_argument("--socket", default="/run/broker/broker.sock")
    parser.add_argument("--credentials", default="/run/credentials/agent.env")
    parser.add_argument("--runtime", default="/srv/state/runtime.json",
                        help="written by bin/discover-runtime on the host: the dnshelper instance")
    parser.add_argument("--endpoint", default="http://cluster-leader:9311")
    args = parser.parse_args(argv)
    logging.basicConfig(stream=sys.stderr, level=logging.INFO, format="%(levelname)s %(message)s")

    client = apiclient.ApiClient(args.credentials, args.endpoint)

    def find_dnshelper():
        try:
            with open(args.runtime) as fp:
                return json.load(fp).get("dnshelper")
        except (OSError, ValueError):
            return None

    def self_agent():
        return client.credentials()[0]  # REDIS_USER is this module's agent id

    server = Server(args.socket, Broker(find_dnshelper, self_agent, client))
    signal.signal(signal.SIGTERM, lambda *a: threading.Thread(target=server.shutdown, daemon=True).start())
    log.info("listening on %s", args.socket)
    server.serve_forever()
    server.server_close()
    return 0
