#
# Copyright (C) 2026 Dan Brown
# SPDX-License-Identifier: GPL-3.0-or-later
#
# The dnsapi HTTP service (DESIGN.md, API v1). Traefik terminates TLS and
# forwards plain HTTP to this process, which listens on 127.0.0.1 only.
#
# Standard library only: the service has no third-party dependencies to pin
# or to keep up to date.

import json
import logging
import os
import signal
import sys
import threading
import urllib.parse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import keys as keyfmt
from .api import Api, ApiError, Request, client_address, match_route
from .backend import Backend
from .limits import SlidingWindow
from .store import Store

log = logging.getLogger("dnsapi")

MAX_BODY = 1024 * 1024  # DESIGN.md, Security, Limits
MAX_CONNECTIONS = 64     # DESIGN.md, Security, Concurrency limits
OPENAPI_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "openapi.json")


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    # A client that opens a connection and sends nothing must not hold a
    # thread forever.
    timeout = 30
    api = None  # set by make_server

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
        split = urllib.parse.urlsplit(self.path)
        path = split.path
        head = method == "HEAD"
        try:
            if path == "/v1/status":
                # Liveness only: no key, nothing about zones or dnshelper.
                self._discard_body()
                if method not in ("GET", "HEAD"):
                    raise self._not_allowed(method, {"GET"})
                self._send_json(HTTPStatus.OK, {"status": "ok"}, head=head)
                return
            if path == "/v1/openapi.json":
                # The API's description needs no key.
                self._discard_body()
                if method not in ("GET", "HEAD"):
                    raise self._not_allowed(method, {"GET"})
                with open(OPENAPI_PATH) as fp:
                    self._send_json(HTTPStatus.OK, json.load(fp), head=head)
                return
            self._require_https()
            body = self._read_body()
            api = self.api
            runtime = api.store.runtime()
            req = Request(
                method,
                path,
                {k: v[0] for k, v in urllib.parse.parse_qs(split.query).items()},
                body,
                client_address(self.client_address[0], self.headers.get_all("X-Forwarded-For") or [],
                               int(runtime.get("proxies_depth") or 0)),
            )
            self.client_ip = req.client_ip
            api.authenticate(req, self.headers.get("Authorization"))
            api.enter(req)
            try:
                methods, params = match_route(path)
                if methods is None:
                    raise ApiError(HTTPStatus.NOT_FOUND, "not_found", "No such endpoint")
                name = methods.get("GET" if head else method)
                if name is None:
                    raise self._not_allowed(method, set(methods))
                req.params = {k: urllib.parse.unquote(v) for k, v in params.items()}
                status, payload = getattr(api, name)(req)
            finally:
                api.leave(req)
            self._send_json(status, payload, head=head)
        except ApiError as exc:
            error = {"code": exc.code, "message": exc.message, "field": exc.field}
            self._send_json(exc.status, {"error": error}, exc.headers, head=head)
        except Exception:
            log.exception("unhandled error on %s %s", method, path)
            error = {"code": "internal_error", "message": "Internal error", "field": None}
            self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": error}, head=head)

    def _require_https(self):
        """Refuse a request Traefik received over plain HTTP (DESIGN.md, Security, HTTPS
        only). Traefik sets X-Forwarded-Proto; a request without it comes straight from the
        node. The key, if any, has crossed the network in the clear: log its id."""
        proto = (self.headers.get("X-Forwarded-Proto") or "").split(",")[0].strip().lower()
        if not proto or proto == "https":
            return
        scheme, _, key = (self.headers.get("Authorization") or "").partition(" ")
        key_id = keyfmt.parse_key(key.strip()) if scheme.lower() == "bearer" else None
        if key_id:
            log.warning("key %s was sent over plain HTTP from %s: revoke it if the network may be watched",
                        key_id, self.headers.get("X-Forwarded-For") or self.client_address[0])
        self.close_connection = True
        raise ApiError(HTTPStatus.FORBIDDEN, "https_required", "Use https://: the API refuses plain HTTP")

    @staticmethod
    def _not_allowed(method, methods):
        allowed = set(methods) | ({"HEAD"} if "GET" in methods else set())
        return ApiError(HTTPStatus.METHOD_NOT_ALLOWED, "method_not_allowed",
                        f"{method} is not allowed here", headers={"Allow": ", ".join(sorted(allowed))})

    def _too_large(self):
        self.close_connection = True
        return ApiError(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "body_too_large",
                        f"The request body is limited to {MAX_BODY} bytes")

    def _raw_body(self):
        if "chunked" in self.headers.get("Transfer-Encoding", "").lower():
            chunks, size = [], 0
            while True:
                line = self.rfile.readline(1024)
                length = int(line.split(b";", 1)[0].strip() or b"0", 16)
                if length == 0:
                    while self.rfile.readline(1024) not in (b"\r\n", b"\n", b""):
                        pass
                    break
                size += length
                if size > MAX_BODY:
                    raise self._too_large()
                chunks.append(self.rfile.read(length))
                self.rfile.readline(1024)
            return b"".join(chunks)
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            raise ApiError(HTTPStatus.BAD_REQUEST, "invalid_request", "Bad Content-Length")
        if length > MAX_BODY:
            raise self._too_large()
        return self.rfile.read(length) if length > 0 else b""

    def _discard_body(self):
        try:
            self._raw_body()
        except ApiError:
            self.close_connection = True

    def _read_body(self):
        raw = self._raw_body()
        if not raw.strip():
            return None
        try:
            return json.loads(raw)
        except ValueError:
            raise ApiError(HTTPStatus.BAD_REQUEST, "invalid_json", "The request body is not valid JSON")

    def _send_json(self, status, body, headers=None, head=False):
        payload = b"" if body is None else json.dumps(body).encode() + b"\n"
        self.send_response(status)
        if body is not None:
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
        address = getattr(self, "client_ip", None) or self.address_string()
        log.info("%s %s", address, format % args)


def make_api(state_dir, usage_dir=None, broker="/run/broker/broker.sock", backend=None):
    store = Store(state_dir, usage_dir)
    backend = backend or Backend(broker)
    return Api(store, backend, SlidingWindow(60.0), SlidingWindow(60.0))


BUSY = json.dumps({"error": {"code": "busy", "message": "Too many connections; try again", "field": None}}).encode()


class Server(ThreadingHTTPServer):
    """A thread per connection, at most max_connections at once: one more is answered
    503 and closed (DESIGN.md, Security, Concurrency limits)."""

    daemon_threads = True

    def __init__(self, address, handler, max_connections=MAX_CONNECTIONS):
        self.slots = threading.BoundedSemaphore(max_connections)
        super().__init__(address, handler)

    def process_request(self, request, client_address):
        if not self.slots.acquire(blocking=False):
            try:
                request.sendall(b"HTTP/1.1 503 Service Unavailable\r\nContent-Type: application/json\r\n"
                                b"Retry-After: 5\r\nConnection: close\r\nContent-Length: "
                                + str(len(BUSY)).encode() + b"\r\n\r\n" + BUSY)
            except OSError:
                pass
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except Exception:
            self.slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.slots.release()


def make_server(host, port, api, max_connections=MAX_CONNECTIONS):
    handler = type("BoundHandler", (Handler,), {"api": api})
    return Server((host, port), handler, max_connections)


def main(argv=None):
    import argparse

    parser = argparse.ArgumentParser(prog="dnsapi-server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--state-dir", default="/srv/state")
    parser.add_argument("--usage-dir", default="/srv/usage")
    parser.add_argument("--broker", default="/run/broker/broker.sock")
    args = parser.parse_args(argv)

    logging.basicConfig(stream=sys.stderr, level=logging.INFO, format="%(levelname)s %(message)s")
    api = make_api(args.state_dir, args.usage_dir, args.broker)
    server = make_server(args.host, args.port, api)
    stopping = threading.Event()

    def flush_loop():
        while not stopping.wait(30):
            api.store.flush_usage()

    threading.Thread(target=flush_loop, daemon=True).start()

    def stop(signum, frame):
        # shutdown() waits for serve_forever() to return, so it can't run in
        # the thread that is serving.
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    log.info("listening on %s:%d", args.host, args.port)
    server.serve_forever()
    stopping.set()
    api.store.flush_usage()
    server.server_close()
    log.info("stopped")
    return 0
