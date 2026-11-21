#
# Copyright (C) 2026 Dan Brown
# SPDX-License-Identifier: GPL-3.0-or-later
#
# The API host name's own DNS record (DESIGN.md, The API host name in DNS):
# a CNAME from the host name to the node's host name, added through
# dnshelper when the host name is in a zone it manages and its rules let
# dnsapi write that CNAME. Another record at the name is never overwritten.
# Nothing here raises: the result is a status for the Status and Settings
# pages, kept in state/host-record.json.
#
# dnshelper calls (schemas read 2026-11-21, dnshelper 0.7.0):
#   has-zone {"name", "records": [{"name": <full name>, "type"}]}
#     -> {"managed", "zone", "records": [{"read", "write"}]}, from the rules only
#   get-records {"zone", "name"} -> {"records": [...]}, the ones dnsapi may read
#   append-records {"zone", "records"}: no on_behalf_of, so dnsapi is the owner
#   check-propagation {"zone", "name", "type"} -> {"servers": [{"status": same|different|error}]}

import time

from . import dnshelper, state

STATUS_FILE = "host-record.json"
PROPAGATION_TIMEOUT = 90
PROPAGATION_INTERVAL = 10
TTL = 300


def node_fqdn():
    """The node's host name, from its get-fqdn action (role node:reader)."""
    import agent
    import agent.tasks

    response = agent.tasks.run(agent.resolve_agent_id("node"), action="get-fqdn", data={},
                               extra={"isNotificationHidden": True})
    if response["exit_code"] != 0:
        raise dnshelper.DnshelperError("unavailable", "node/get-fqdn failed")
    out = response["output"]
    return f"{out['hostname']}.{out['domain']}".lower().rstrip(".")


def _norm(name):
    return (name or "").strip().lower().rstrip(".")


def ensure(host, target_fqdn, call, wait=False, sleep=time.sleep, clock=time.monotonic):
    """Make sure `host` has a CNAME to `target_fqdn`. `call(action, data)` runs a dnshelper
    action and returns its output or raises dnshelper.DnshelperError. Returns the status dict."""
    host = _norm(host)
    target = _norm(target_fqdn)
    result = {"host": host, "target": target, "zone": None, "status": "error",
              "existing": [], "message": "", "checked": state.now()}
    try:
        answer = call("has-zone", {"name": host, "records": [{"name": host, "type": "CNAME"}]})
        zone = answer.get("zone")
        result["zone"] = zone
        if not answer.get("managed"):
            result["status"] = "not_managed"
            return result
        if _norm(zone) == host:
            result["status"] = "apex"
            return result
        checks = answer.get("records") or [{}]
        if not checks[0].get("write"):
            result["status"] = "not_permitted"
            return result
        name = host[: -len(zone) - 1]
        existing = call("get-records", {"zone": zone, "name": name}).get("records", [])
        existing = [r for r in existing if _norm(r.get("name")) == name]
        result["existing"] = [f"{r['type']} {r['data']}" for r in existing]
        cnames = [r for r in existing if r["type"].upper() == "CNAME"]
        if cnames and all(_norm(r["data"]) == target for r in cnames) and len(cnames) == len(existing):
            result["status"] = "ok"
            return result
        if existing:
            result["status"] = "conflict"
            return result
        try:
            call("append-records", {"zone": zone, "records": [
                {"name": name, "type": "CNAME", "ttl": TTL, "data": target + "."}]})
        except dnshelper.DnshelperError as exc:
            if exc.code == "conflict":
                # a record dnsapi may not read is at the name
                result["status"] = "conflict"
                result["message"] = exc.message
                return result
            raise
        result["status"] = "created"
        if wait:
            result["propagated"] = _wait(call, zone, name, sleep, clock)
        return result
    except dnshelper.DnshelperError as exc:
        result["status"] = "not_permitted" if exc.code == "not_permitted" else "error"
        result["message"] = exc.message or exc.code
        return result


def _wait(call, zone, name, sleep, clock):
    """True once the zone's name servers answer with the record (at most PROPAGATION_TIMEOUT)."""
    deadline = clock() + PROPAGATION_TIMEOUT
    while True:
        try:
            servers = call("check-propagation", {"zone": zone, "name": name, "type": "CNAME"}).get("servers", [])
            statuses = [s.get("status") for s in servers]
            if "same" in statuses and "different" not in statuses:
                return True
        except dnshelper.DnshelperError:
            pass
        if clock() + PROPAGATION_INTERVAL > deadline:
            return False
        sleep(PROPAGATION_INTERVAL)


def load():
    return state.load(STATUS_FILE, None)


def save(result):
    state.save(STATUS_FILE, result)
