#
# Copyright (C) 2026 Dan Brown
# SPDX-License-Identifier: GPL-3.0-or-later
#
# The dnsapi HTTP service (DESIGN.md, API v1). Traefik terminates TLS and
# forwards plain HTTP to this process, which the systemd unit publishes on
# 127.0.0.1 only.
#
# Standard library only: the service has no third-party dependencies to pin
# or to keep up to date.

import json
import logging
import signal
import sys
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

log = logging.getLogger("dnsapi")


class ApiError(Exception):
    """An error answered as {"error": {"code", "message", "field"}}."""

    def __init__(self, status, code, message, field=None, headers=None):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.field = field
        self.headers = headers or {}


def route_status(handler):
    # Liveness only: it says nothing about zones, tenants or dnshelper, and
    # needs no key.
    return HTTPStatus.OK, {"status": "ok"}


# path -> {method: function}. HEAD is answered wherever GET is.
ROUTES = {
    "/v1/status": {"GET": route_status},
}


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    # A client that opens a connection and sends nothing must not hold a
    # thread forever.
    timeout = 30

    def version_string(self):
        # No Python or library version in the Server header.
        return "dnsapi"

    def do_GET(self):
        self._dispatch("GET")

    def do_HEAD(self):
        self._dispatch("HEAD")

    def do_POST(self):
        self._dispatch("POST")

    def do_PUT(self):
        self._dispatch("PUT")

    def do_PATCH(self):
        self._dispatch("PATCH")

    def do_DELETE(self):
        self._dispatch("DELETE")

    def _dispatch(self, method):
        path = self.path.split("?", 1)[0]
        try:
            methods = ROUTES.get(path)
            if methods is None:
                raise ApiError(HTTPStatus.NOT_FOUND, "not_found", "No such endpoint")
            func = methods.get("GET" if method == "HEAD" else method)
            if func is None:
                allowed = sorted(set(methods) | ({"HEAD"} if "GET" in methods else set()))
                raise ApiError(
                    HTTPStatus.METHOD_NOT_ALLOWED,
                    "method_not_allowed",
                    f"{method} is not allowed here",
                    headers={"Allow": ", ".join(allowed)},
                )
            status, body = func(self)
            self._send_json(status, body, head=(method == "HEAD"))
        except ApiError as exc:
            error = {"code": exc.code, "message": exc.message, "field": exc.field}
            self._send_json(exc.status, {"error": error}, exc.headers, head=(method == "HEAD"))
        except Exception:
            log.exception("unhandled error on %s %s", method, path)
            error = {"code": "internal_error", "message": "Internal error", "field": None}
            self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": error}, head=(method == "HEAD"))

    def _send_json(self, status, body, headers=None, head=False):
        payload = json.dumps(body).encode() + b"\n"
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        if not head:
            self.wfile.write(payload)

    def log_request(self, code="-", size="-"):
        # The liveness probe runs often (the unit's start check, monitoring):
        # don't fill the journal with it.
        if self.path.split("?", 1)[0] == "/v1/status" and str(code).startswith("2"):
            return
        super().log_request(code, size)

    def log_message(self, format, *args):
        # The client address is Traefik's until the forwarded address is
        # handled (DESIGN.md, Security, per-key IP allowlist).
        log.info("%s %s", self.address_string(), format % args)


def make_server(host, port):
    server = ThreadingHTTPServer((host, port), Handler)
    server.daemon_threads = True
    return server


def main(argv=None):
    import argparse

    parser = argparse.ArgumentParser(prog="dnsapi-server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args(argv)

    logging.basicConfig(stream=sys.stderr, level=logging.INFO, format="%(levelname)s %(message)s")
    server = make_server(args.host, args.port)

    def stop(signum, frame):
        # shutdown() waits for serve_forever() to return, so it can't run in
        # the thread that is serving.
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    log.info("listening on %s:%d", args.host, args.port)
    server.serve_forever()
    server.server_close()
    log.info("stopped")
    return 0
