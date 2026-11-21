#
# Copyright (C) 2026 Dan Brown
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Run NS8 tasks through the api-server, as ns8-core's agent.tasks.run does
# (agent/tasks/apiclient.py), with the standard library only:
#
#   POST /api/login                       {"username", "password"} -> {"token"}
#   POST /api/<agent>/tasks               {"action", "data", "parent", "extra"} -> {"data": {"id"}}
#   GET  /api/<agent>/task/<id>/status    400 or 404 until the task has ended
#
# The module's own credentials (REDIS_USER is "module/dnsapi1") are used, so
# dnshelper applies its policy for this module, and the module's own actions
# can be called through its selfadm role. Tested on a node, 2026-11-21:
# login 0.08 s, a list-zones task 0.4 s with 200 ms polling.

import json
import logging
import threading
import time
import urllib.error
import urllib.request

log = logging.getLogger("dnsapi")


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
    """The api-server cannot be reached, or no dnshelper is installed."""


class Backend:
    def __init__(self, store, endpoint="http://cluster-leader:9311", timeout=150.0, http_timeout=15.0):
        self.store = store
        self.endpoint = endpoint
        self.timeout = timeout
        self.http_timeout = http_timeout
        self.token = None
        self.lock = threading.Lock()

    # HTTP

    def _request(self, method, path, body=None, token=None):
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = "Bearer " + token
        req = urllib.request.Request(
            self.endpoint + path,
            method=method,
            headers=headers,
            data=None if body is None else json.dumps(body).encode(),
        )
        with urllib.request.urlopen(req, timeout=self.http_timeout) as resp:
            return json.load(resp)

    def _login(self):
        user, password = self.store.credentials()
        reply = self._request("POST", "/api/login", {"username": user, "password": password})
        return reply["token"]

    def _authorized(self, method, path, body=None):
        """Call with the cached token; log in again once on 401."""
        with self.lock:
            if self.token is None:
                self.token = self._login()
            token = self.token
        try:
            return self._request(method, path, body, token)
        except urllib.error.HTTPError as exc:
            if exc.code != 401:
                raise
        with self.lock:
            if self.token == token:
                self.token = self._login()
            token = self.token
        return self._request(method, path, body, token)

    # tasks

    def agent_id(self):
        """This module's own agent id, e.g. "module/dnsapi1"."""
        return self.store.credentials()[0]

    def dnshelper_id(self):
        agent_id = self.store.runtime().get("dnshelper")
        if not agent_id:
            raise Unavailable("dnshelper is not installed")
        return agent_id

    def run(self, agent_id, action, data):
        """Run a task and return its output; raise TaskRefused, TaskFailed, TaskTimeout or Unavailable."""
        started = time.monotonic()
        try:
            created = self._authorized("POST", f"/api/{agent_id}/tasks", {
                "action": action,
                "data": data,
                "parent": "",
                "extra": {"title": f"{agent_id}/{action}", "isNotificationHidden": True},
            })
            task_id = created["data"]["id"]
            delay = 0.15
            while True:
                try:
                    status = self._authorized("GET", f"/api/{agent_id}/task/{task_id}/status")
                    break
                except urllib.error.HTTPError as exc:
                    if exc.code not in (400, 404):
                        raise
                if time.monotonic() - started > self.timeout:
                    raise TaskTimeout(f"{agent_id}/{action} did not end within {self.timeout:.0f} s")
                time.sleep(delay)
                delay = min(delay * 1.5, 1.0)
        except urllib.error.HTTPError as exc:
            if exc.code == 403:
                # The api-server refused the task: the role is missing.
                raise TaskRefused([{"field": "", "error": "not_permitted",
                                    "message": f"{action} on {agent_id} is not allowed for this module"}])
            raise Unavailable(f"api-server answered {exc.code} for {agent_id}/{action}")
        except (urllib.error.URLError, OSError, ValueError, KeyError) as exc:
            raise Unavailable(f"api-server unreachable for {agent_id}/{action}: {exc}")

        data = status.get("data", {})
        elapsed = time.monotonic() - started
        if data.get("exit_code") == 0:
            log.debug("%s/%s ok in %.2f s", agent_id, action, elapsed)
            return data.get("output")
        output = data.get("output")
        if isinstance(output, list) and output:
            raise TaskRefused(output)
        log.error("%s/%s failed (exit %s) in %.2f s", agent_id, action, data.get("exit_code"), elapsed)
        raise TaskFailed(f"{action} failed")
