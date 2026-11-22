#
# Copyright (C) 2026 Dan Brown
# SPDX-License-Identifier: GPL-3.0-or-later
#
# NS8 tasks, through the broker (DESIGN.md, Runtime, The broker). The
# service holds no NS8 credentials: it sends one JSON line per request to
# the broker's Unix socket, and the broker, on the host, runs the task if it
# is one the API needs:
#
#   request  {"target": "dnshelper" | "self", "action", "data"}
#   answer   {"exit_code", "output", "error"}  or  {"refused": why}  or  {"unavailable": why}

import json
import logging
import socket

log = logging.getLogger("dnsapi")

MAX_ANSWER = 16 * 1024 * 1024


class TaskRefused(Exception):
    """The task ended with validation errors: [{"field", "error", "value", "message"?}]."""

    def __init__(self, errors):
        super().__init__(errors[0].get("error") if errors else "validation-failed")
        self.errors = errors


class TaskFailed(Exception):
    """The task failed for a reason the caller cannot fix (provider outage, step error)."""


class TaskTimeout(Exception):
    pass


class Unavailable(Exception):
    """The broker or the api-server cannot be reached."""


class DnshelperMissing(Unavailable):
    """No dnshelper is installed."""


class Backend:
    def __init__(self, socket_path="/run/broker/broker.sock", timeout=170.0):
        self.socket_path = socket_path
        # longer than the broker's own wait for a task (150 s)
        self.timeout = timeout

    def _ask(self, request):
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
                sock.settimeout(self.timeout)
                sock.connect(self.socket_path)
                sock.sendall(json.dumps(request).encode() + b"\n")
                with sock.makefile("rb") as fp:
                    line = fp.readline(MAX_ANSWER)
        except socket.timeout:
            raise TaskTimeout(f"no answer from the broker for {request['action']}")
        except OSError as exc:
            raise Unavailable(f"broker unreachable: {exc}")
        try:
            return json.loads(line)
        except ValueError:
            raise Unavailable("the broker gave no answer")

    def run(self, target, action, data):
        """Run a task on "dnshelper" or "self" (this module) and return its output;
        raise TaskRefused, TaskFailed, TaskTimeout, DnshelperMissing or Unavailable."""
        answer = self._ask({"target": target, "action": action, "data": data})
        if "refused" in answer:
            # The service asked for something the broker does not run: a bug here.
            log.error("the broker refused %s %s: %s", target, action, answer["refused"])
            raise TaskFailed(f"{action} refused by the broker")
        if "unavailable" in answer:
            reason = answer["unavailable"]
            if reason == "dnshelper_missing":
                raise DnshelperMissing("dnshelper is not installed")
            if reason == "timeout":
                raise TaskTimeout(f"{target}/{action} did not end in time")
            raise Unavailable(f"{target}/{action}: {reason}")
        if answer.get("exit_code") == 0:
            return answer.get("output")
        output = answer.get("output")
        if isinstance(output, list) and output:
            raise TaskRefused(output)
        log.error("%s/%s failed (exit %s)", target, action, answer.get("exit_code"))
        raise TaskFailed(f"{action} failed")
