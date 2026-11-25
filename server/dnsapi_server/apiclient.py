#
# Copyright (C) 2026 Dan Brown
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Run NS8 tasks through the api-server with the standard library, for the
# broker (broker.py), which runs in its own container without ns8-core's
# agent package. (agent.tasks.run() could not be used from the broker's
# threads anyway: it installs a SIGTERM handler with
# loop.add_signal_handler(), which only works in the main thread.)
#
#   POST /api/login                       {"username", "password"} -> {"token"}
#   POST /api/<agent>/tasks               {"action", "data", "parent", "extra"} -> {"data": {"id"}}
#   GET  /api/<agent>/task/<id>/status    400 or 404 until the task has ended
#
# The credentials are this module's, REDIS_USER and REDIS_PASSWORD from
# agent.env, mounted read-only into the broker's container only. Only those
# two are read: the file also sets PATH and PYTHONPATH. Measured on a node: login 0.08 s, a short
# task 0.07 to 0.4 s with this polling.

import json
import threading
import time
import urllib.error
import urllib.request


class Unreachable(Exception):
    """The api-server could not be reached or refused the call itself."""

    def __init__(self, message, status=None):
        super().__init__(message)
        self.status = status  # the api-server's HTTP status, when it answered


class Timeout(Exception):
    pass


class ApiClient:
    def __init__(self, credentials_path, endpoint="http://cluster-leader:9311", timeout=150.0,
                 http_timeout=15.0):
        self.credentials_path = credentials_path
        self.endpoint = endpoint
        self.timeout = timeout
        self.http_timeout = http_timeout
        self.token = None
        self.lock = threading.Lock()

    def _request(self, method, path, body=None, token=None):
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = "Bearer " + token
        req = urllib.request.Request(self.endpoint + path, method=method, headers=headers,
                                     data=None if body is None else json.dumps(body).encode())
        with urllib.request.urlopen(req, timeout=self.http_timeout) as resp:
            return json.load(resp)

    def credentials(self):
        """REDIS_USER and REDIS_PASSWORD from agent.env, read on each login (they can rotate)."""
        values = {}
        with open(self.credentials_path) as fp:
            for line in fp:
                name, sep, value = line.rstrip("\n").partition("=")
                if sep and name in ("REDIS_USER", "REDIS_PASSWORD"):
                    values[name] = value
        return values["REDIS_USER"], values["REDIS_PASSWORD"]

    def _login(self):
        user, password = self.credentials()
        reply = self._request("POST", "/api/login", {"username": user, "password": password})
        return reply["token"]

    def _authorized(self, method, path, body=None):
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

    def run(self, agent_id, action, data):
        """Run a task; return its status {"exit_code", "output", "error"}."""
        started = time.monotonic()
        try:
            created = self._authorized("POST", f"/api/{agent_id}/tasks", {
                "action": action, "data": data, "parent": "",
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
                    raise Timeout(f"{agent_id}/{action} did not end within {self.timeout:.0f} s")
                time.sleep(delay)
                delay = min(delay * 1.5, 1.0)
        except urllib.error.HTTPError as exc:
            raise Unreachable(f"api-server answered {exc.code} for {agent_id}/{action}", exc.code)
        except (urllib.error.URLError, OSError, ValueError, KeyError) as exc:
            raise Unreachable(f"api-server unreachable for {agent_id}/{action}: {exc}")
        data = status.get("data", {})
        return {"exit_code": data.get("exit_code"), "output": data.get("output"), "error": data.get("error")}
