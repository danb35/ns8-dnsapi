#
# Copyright (C) 2026 Dan Brown
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Run with: cd server && python3 -m unittest discover -s tests
# build-images.sh runs them inside the built image.

import http.client
import json
import re
import logging
import os
import shutil
import tempfile
import threading
import time
import unittest

from dnsapi_server import keys as keyfmt
from dnsapi_server.api import Api, client_address
from dnsapi_server.app import make_api, make_server
from dnsapi_server.backend import Backend, DnshelperMissing, TaskFailed, TaskRefused, Unavailable
from dnsapi_server.limits import SlidingWindow
from dnsapi_server.store import Store

ZONES = [
    {"zone": "acme.test", "credential": "c1", "provider": "cloudflare", "access": "write", "full": True},
    {"zone": "beta.test", "credential": "c1", "provider": "cloudflare", "access": "write", "full": True},
    {"zone": "free.test", "credential": "c1", "provider": "cloudflare", "access": "write", "full": True},
    {"zone": "partial.test", "credential": "c1", "provider": "cloudflare", "access": "write", "full": False},
    {"zone": "readonly.test", "credential": "c1", "provider": "cloudflare", "access": "read", "full": False},
]
RECORDS = {
    "acme.test": [
        {"name": "@", "type": "MX", "ttl": 300, "data": "10 mail.acme.test."},
        {"name": "www", "type": "A", "ttl": 300, "data": "192.0.2.1"},
    ],
}
OWNERS = {
    "acme.test": [{"name": "@", "type": "MX", "data": "10 mail.acme.test.", "callers": ["module/mail1"],
                   "removed": [], "time": "2026-11-21T00:00:00Z"}],
}


def write_json(directory, name, data):
    with open(os.path.join(directory, name), "w") as fp:
        json.dump(data, fp)


class FakeBackend:
    """dnshelper and this module's own actions, as the broker would run them, without NS8."""

    def __init__(self, store):
        self.store = store
        self.calls = []
        self.fail_with = None

    def run(self, agent_id, action, data):
        self.calls.append((agent_id, action, data))
        if self.fail_with:
            raise self.fail_with
        state = self.store.state_dir
        if agent_id == "dnshelper":
            if action == "list-zones":
                return {"zones": ZONES}
            if action == "get-records":
                return {"records": [dict(r) for r in RECORDS.get(data["zone"], [])]}
            if action == "list-owners":
                return {"zone": data["zone"], "owners": OWNERS.get(data["zone"], [])}
            existing = RECORDS.get(data.get("zone"), [])

            def same(a, b):
                return all(a.get(k) == b.get(k) for k in ("name", "type", "data") if k in a)

            def result(add, remove):
                add = [{"ttl": 300, **r} for r in add]
                return {"dry_run": data.get("dry_run", False), "changes": {"add": add, "remove": remove},
                        "records": [r for r in existing if r not in remove] + add}

            if action == "append-records":
                return result(data["records"], [])
            if action == "apply-changes":
                remove = []
                for wanted in data.get("remove", []):
                    found = [r for r in existing if same(wanted, r)]
                    if not found:
                        raise TaskRefused([{"field": "remove", "error": "stale", "value": "",
                                            "message": "a record to remove is no longer in the zone"}])
                    remove += found
                return result(data.get("add", []), remove)
            if action == "set-records":
                keys = {(r["name"], r["type"]) for r in data["records"]}
                return result(data["records"], [r for r in existing if (r["name"], r["type"]) in keys])
            if action == "delete-records":
                return result([], [r for r in existing if any(same(w, r) for w in data["records"])])
            if action == "check-propagation":
                return {"zone": data["zone"], "name": data["name"], "type": data["type"],
                        "records": [], "servers_from": "dns", "servers": []}
        if agent_id == "self":
            tenants = json.load(open(os.path.join(state, "tenants.json")))
            keys = json.load(open(os.path.join(state, "keys.json")))
            if action == "add-tenant":
                tenants["tenants"]["t00000009"] = {"name": data["name"], "enabled": True, "zones": [],
                                                   "created": "2026-11-21T00:00:00Z"}
                write_json(state, "tenants.json", tenants)
                return {"id": "t00000009"}
            if action == "assign-zone":
                for tenant_id, tenant in tenants["tenants"].items():
                    if data["zone"] in tenant["zones"] and tenant_id != data["tenant"]:
                        raise TaskRefused([{"field": "zone", "error": "zone_assigned", "value": data["zone"],
                                            "message": "the zone belongs to another tenant"}])
                tenants["tenants"][data["tenant"]]["zones"].append(data["zone"])
                write_json(state, "tenants.json", tenants)
                return {}
            if action == "create-key":
                keys["keys"][data["id"]] = {"owner": data["owner"], "scope": data["scope"], "hash": data["hash"],
                                            "label": data.get("label", ""), "allowlist": [], "expires": None,
                                            "created": "2026-11-21T00:00:00Z"}
                write_json(state, "keys.json", keys)
                return {}
            if action == "revoke-key":
                del keys["keys"][data["id"]]
                write_json(state, "keys.json", keys)
                return {}
        raise TaskFailed(f"unexpected {agent_id} {action}")


class ApiTest(unittest.TestCase):
    def setUp(self):
        logging.disable(logging.CRITICAL)
        self.dir = tempfile.mkdtemp()
        self.usage = os.path.join(self.dir, "usage")
        os.mkdir(self.usage)
        with open(os.path.join(self.dir, "agent.env"), "w") as fp:
            fp.write("PATH=/x\nREDIS_USER=module/dnsapi1\nREDIS_PASSWORD=secret\n")
        write_json(self.dir, "runtime.json", {"dnshelper": "module/dnshelper1", "proxies_depth": 0})
        write_json(self.dir, "settings.json", {"host": "api.test", "rate_limit": 60})
        write_json(self.dir, "tenants.json", {"tenants": {
            "t00000001": {"name": "Acme", "enabled": True, "zones": ["acme.test"], "created": None},
            "t00000002": {"name": "Beta", "enabled": True, "zones": ["beta.test"], "created": None},
            "t00000003": {"name": "Off", "enabled": False, "zones": [], "created": None},
        }})
        self.keys = {}
        records = {}
        for name, owner, scope, extra in [
            ("operator", "operator", "write", {}),
            ("operator_ro", "operator", "read", {}),
            ("acme", "t00000001", "write", {}),
            ("acme_ro", "t00000001", "read", {}),
            ("beta", "t00000002", "write", {}),
            ("off", "t00000003", "write", {}),
            ("expired", "operator", "write", {"expires": "2020-01-01T00:00:00Z"}),
            ("fenced", "operator", "write", {"allowlist": ["203.0.113.0/24"]}),
            ("acme_host", "t00000001", "write",
             {"restrict": {"names": ["_acme-challenge", "_acme-challenge.*"], "types": ["TXT"]}}),
            ("op_acme", "operator", "write",
             {"restrict": {"names": ["_acme-challenge", "_acme-challenge.*"], "types": ["TXT"]}}),
            ("www_any", "t00000001", "write", {"restrict": {"names": ["www"], "types": ["*"]}}),
        ]:
            key_id, key, key_hash = keyfmt.new_key()
            self.keys[name] = key
            records[key_id] = {"owner": owner, "scope": scope, "hash": key_hash, "label": name,
                               "allowlist": [], "expires": None, "created": None, **extra}
        write_json(self.dir, "keys.json", {"keys": records})

        store = Store(self.dir, self.usage)
        self.backend = FakeBackend(store)
        self.api = Api(store, self.backend, SlidingWindow(60.0), SlidingWindow(60.0))
        self.server = make_server("127.0.0.1", 0, self.api)
        self.port = self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        shutil.rmtree(self.dir)
        logging.disable(logging.NOTSET)

    def request(self, method, path, key=None, body=None, headers=None, raw=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        hdrs = dict(headers or {})
        if key:
            hdrs["Authorization"] = "Bearer " + self.keys.get(key, key)
        data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
        if data is not None:
            hdrs["Content-Type"] = "application/json"
        try:
            conn.request(method, path, body=data, headers=hdrs)
            resp = conn.getresponse()
            payload = resp.read()
            return resp, (json.loads(payload) if payload else None)
        finally:
            conn.close()

    def assertError(self, resp, body, status, code):
        self.assertEqual(resp.status, status, body)
        self.assertEqual(body["error"]["code"], code)

    # status and plumbing

    def test_status_needs_no_key(self):
        resp, body = self.request("GET", "/v1/status")
        self.assertEqual(resp.status, 200)
        self.assertEqual(body, {"status": "ok"})
        self.assertEqual(resp.getheader("Server"), "dnsapi")

    def test_openapi_document(self):
        resp, body = self.request("GET", "/v1/openapi.json")
        self.assertEqual(resp.status, 200)
        self.assertEqual(body["openapi"], "3.1.0")
        # every route of the service is described, with the same methods
        from dnsapi_server.api import ROUTES
        described = {}
        for path, item in body["paths"].items():
            pattern = re.sub(r"\{[a-z_]+\}", "[^/]+", path)
            described[pattern] = {m.upper() for m in item if m in ("get", "post", "put", "patch", "delete")}
        for route, methods in ROUTES:
            pattern = re.sub(r"\(\?P<[a-z]+>\[\^/\]\+\)", "[^/]+", route)
            self.assertIn(pattern, described, route)
            self.assertEqual(described[pattern], set(methods), route)

    def test_status_head_and_method(self):
        resp, body = self.request("HEAD", "/v1/status")
        self.assertEqual(resp.status, 200)
        resp, body = self.request("POST", "/v1/status", body={})
        self.assertError(resp, body, 405, "method_not_allowed")
        self.assertEqual(resp.getheader("Allow"), "GET, HEAD")

    def test_unknown_path_needs_a_key_first(self):
        resp, body = self.request("GET", "/v1/nothing")
        self.assertError(resp, body, 401, "missing_key")
        resp, body = self.request("GET", "/v1/nothing", "operator")
        self.assertError(resp, body, 404, "not_found")

    def test_body_limits(self):
        resp, body = self.request("POST", "/v1/tenants", "operator", raw=b"{not json")
        self.assertError(resp, body, 400, "invalid_json")
        # Refused from the Content-Length, before the body is read.
        import socket
        with socket.create_connection(("127.0.0.1", self.port), timeout=5) as sock:
            sock.sendall(("POST /v1/tenants HTTP/1.1\r\nHost: x\r\nAuthorization: Bearer %s\r\n"
                          "Content-Length: %d\r\n\r\n" % (self.keys["operator"], 1024 * 1024 + 1)).encode())
            chunks = []
            while True:  # the server closes the connection after a 413
                chunk = sock.recv(65536)
                if not chunk:
                    break
                chunks.append(chunk)
            reply = b"".join(chunks).decode()
        self.assertTrue(reply.startswith("HTTP/1.1 413"), reply)
        self.assertIn('"body_too_large"', reply)

    # authentication

    def test_bad_keys(self):
        resp, body = self.request("GET", "/v1/zones", "dnsapi_00000000_" + "a" * 52)
        self.assertError(resp, body, 401, "invalid_key")
        self.assertIn("Bearer", resp.getheader("WWW-Authenticate"))
        wrong_secret = self.keys["acme"][:-1] + ("a" if self.keys["acme"][-1] != "a" else "b")
        resp, body = self.request("GET", "/v1/zones", wrong_secret)
        self.assertError(resp, body, 401, "invalid_key")
        resp, body = self.request("GET", "/v1/zones", "not-a-key")
        self.assertError(resp, body, 401, "invalid_key")

    def test_expired_disabled_and_fenced_keys(self):
        resp, body = self.request("GET", "/v1/zones", "expired")
        self.assertError(resp, body, 401, "key_expired")
        resp, body = self.request("GET", "/v1/zones", "off")
        self.assertError(resp, body, 403, "tenant_disabled")
        resp, body = self.request("GET", "/v1/tenants", "fenced")
        self.assertError(resp, body, 403, "address_not_allowed")
        resp, body = self.request("GET", "/v1/tenants", "fenced", headers={"X-Forwarded-For": "203.0.113.7"})
        self.assertEqual(resp.status, 200, body)

    def test_brute_force_throttle(self):
        for _ in range(10):
            resp, body = self.request("GET", "/v1/zones", "dnsapi_00000000_" + "a" * 52)
            self.assertEqual(resp.status, 401)
        resp, body = self.request("GET", "/v1/zones", "operator")
        self.assertError(resp, body, 429, "rate_limited")
        self.assertTrue(int(resp.getheader("Retry-After")) > 0)
        # another address is not affected
        resp, body = self.request("GET", "/v1/tenants", "operator", headers={"X-Forwarded-For": "198.51.100.1"})
        self.assertEqual(resp.status, 200)

    # hardening (DESIGN.md, Security: HTTPS only, Concurrency limits, Brute force)

    def test_plain_http_is_refused(self):
        resp, body = self.request("GET", "/v1/tenants", "operator", headers={"X-Forwarded-Proto": "http"})
        self.assertError(resp, body, 403, "https_required")
        resp, body = self.request("GET", "/v1/tenants", "operator", headers={"X-Forwarded-Proto": "https"})
        self.assertEqual(resp.status, 200)
        resp, body = self.request("GET", "/v1/tenants", "operator")  # straight from the node
        self.assertEqual(resp.status, 200)
        resp, body = self.request("GET", "/v1/status", headers={"X-Forwarded-Proto": "http"})
        self.assertEqual(resp.status, 200)

    def test_per_key_concurrency(self):
        from dnsapi_server import api as apimod
        key_id = self.key_id("operator")
        self.api.in_flight[key_id] = apimod.MAX_PER_KEY
        resp, body = self.request("GET", "/v1/tenants", "operator")
        self.assertError(resp, body, 429, "too_many_concurrent")
        self.assertEqual(resp.getheader("Retry-After"), "5")
        resp, body = self.request("GET", "/v1/tenants", "operator_ro")  # another key
        self.assertEqual(resp.status, 200)
        self.api.in_flight.clear()
        resp, body = self.request("GET", "/v1/tenants", "operator")
        self.assertEqual(resp.status, 200)
        self.assertEqual(self.api.in_flight, {})  # released after each request

    def test_task_slots(self):
        from dnsapi_server import api as apimod
        saved = apimod.TASK_SLOT_WAIT
        apimod.TASK_SLOT_WAIT = 0.2
        taken = 0
        try:
            while self.api.task_slots.acquire(blocking=False):
                taken += 1
            self.assertEqual(taken, apimod.MAX_TASKS)
            resp, body = self.request("GET", "/v1/zones", "acme")
            self.assertError(resp, body, 503, "busy")
        finally:
            apimod.TASK_SLOT_WAIT = saved
            for _ in range(taken):
                self.api.task_slots.release()
        resp, body = self.request("GET", "/v1/zones", "acme")
        self.assertEqual(resp.status, 200)

    def test_connection_cap(self):
        import socket
        server = make_server("127.0.0.1", 0, self.api, max_connections=1)
        port = server.server_address[1]
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            idle = socket.create_connection(("127.0.0.1", port), timeout=5)  # holds the only slot
            time.sleep(0.2)
            conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
            conn.request("GET", "/v1/status")
            resp = conn.getresponse()
            self.assertEqual(resp.status, 503)
            self.assertEqual(json.loads(resp.read())["error"]["code"], "busy")
            conn.close()
            idle.close()
            time.sleep(0.3)
            conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
            conn.request("GET", "/v1/status")
            self.assertEqual(conn.getresponse().status, 200)
            conn.close()
        finally:
            server.shutdown()
            server.server_close()

    def test_ipv6_failures_counted_per_64(self):
        from dnsapi_server.api import throttle_key
        self.assertEqual(throttle_key("2001:db8:1:2:aaaa::1"), "2001:db8:1:2::/64")
        self.assertEqual(throttle_key("2001:db8:1:2:ffff::9"), "2001:db8:1:2::/64")
        self.assertEqual(throttle_key("::ffff:203.0.113.5"), "203.0.113.5")
        self.assertEqual(throttle_key("203.0.113.5"), "203.0.113.5")
        bad = "dnsapi_00000000_" + "a" * 52
        for i in range(10):
            self.request("GET", "/v1/zones", bad, headers={"X-Forwarded-For": f"2001:db8:1:2::{i + 1:x}"})
        resp, body = self.request("GET", "/v1/tenants", "operator", headers={"X-Forwarded-For": "2001:db8:1:2::ff"})
        self.assertError(resp, body, 429, "rate_limited")
        resp, body = self.request("GET", "/v1/tenants", "operator", headers={"X-Forwarded-For": "2001:db8:1:3::1"})
        self.assertEqual(resp.status, 200)

    def test_client_address(self):
        self.assertEqual(client_address("127.0.0.1", ["203.0.113.5"], 0), "203.0.113.5")
        self.assertEqual(client_address("127.0.0.1", ["198.51.100.9, 203.0.113.5"], 1), "198.51.100.9")
        self.assertEqual(client_address("127.0.0.1", ["1.1.1.1, 198.51.100.9, 203.0.113.5"], 1), "198.51.100.9")
        self.assertEqual(client_address("127.0.0.1", ["203.0.113.5"], 3), "203.0.113.5")
        self.assertEqual(client_address("127.0.0.1", [], 0), "127.0.0.1")
        # only a request from Traefik on loopback is trusted to carry the header
        self.assertEqual(client_address("192.0.2.50", ["203.0.113.5"], 0), "192.0.2.50")

    def test_last_used_is_recorded(self):
        self.request("GET", "/v1/tenants", "operator")
        self.api.store.flush_usage()
        used = json.load(open(os.path.join(self.usage, "last-used.json")))
        self.assertEqual(len(used), 1)

    # zones and records

    def test_operator_zones(self):
        resp, body = self.request("GET", "/v1/zones", "operator")
        self.assertEqual(resp.status, 200, body)
        zones = {z["zone"]: (z["tenant"], z["full"]) for z in body["zones"]}
        self.assertEqual(zones, {"acme.test": ("t00000001", True), "beta.test": ("t00000002", True),
                                 "free.test": (None, True), "partial.test": (None, False)})

    def test_tenant_zones(self):
        resp, body = self.request("GET", "/v1/zones", "acme_ro")
        self.assertEqual(resp.status, 200, body)
        self.assertEqual([z["zone"] for z in body["zones"]], ["acme.test"])
        self.assertNotIn("tenant", body["zones"][0])

    def test_zone_list_is_cached(self):
        self.request("GET", "/v1/zones", "acme")
        self.request("GET", "/v1/zones", "beta")
        self.assertEqual(sum(1 for c in self.backend.calls if c[1] == "list-zones"), 1)

    def test_records_with_owners(self):
        resp, body = self.request("GET", "/v1/zones/acme.test/records", "acme_ro")
        self.assertEqual(resp.status, 200, body)
        mx = [r for r in body["records"] if r["type"] == "MX"][0]
        www = [r for r in body["records"] if r["type"] == "A"][0]
        self.assertEqual(mx["owned_by"], ["mail1"])
        self.assertNotIn("owned_by", www)

    def test_records_filters_are_passed(self):
        self.request("GET", "/v1/zones/acme.test/records?name=www&type=A", "acme")
        call = [c for c in self.backend.calls if c[1] == "get-records"][0]
        self.assertEqual(call[2], {"zone": "acme.test", "name": "www", "type": "A"})

    def test_tenant_isolation_is_404(self):
        for path in ("/v1/zones/beta.test/records", "/v1/zones/free.test/records",
                     "/v1/zones/nothere.test/records", "/v1/zones/beta.test/propagation?name=www&type=A"):
            resp, body = self.request("GET", path, "acme")
            self.assertError(resp, body, 404, "zone_not_found")
        self.assertFalse([c for c in self.backend.calls if c[1] in ("get-records", "check-propagation")])

    def test_operator_reaches_only_writable_zones(self):
        for zone in ("free.test", "partial.test"):
            resp, body = self.request("GET", f"/v1/zones/{zone}/records", "operator")
            self.assertEqual(resp.status, 200)
        resp, body = self.request("GET", "/v1/zones/readonly.test/records", "operator")
        self.assertError(resp, body, 404, "zone_not_found")

    def test_propagation(self):
        resp, body = self.request("GET", "/v1/zones/acme.test/propagation?name=www&type=A", "acme_ro")
        self.assertEqual(resp.status, 200, body)
        resp, body = self.request("GET", "/v1/zones/acme.test/propagation?name=www", "acme_ro")
        self.assertError(resp, body, 400, "invalid_request")

    def test_dnshelper_missing(self):
        self.backend.fail_with = DnshelperMissing("dnshelper is not installed")
        resp, body = self.request("GET", "/v1/zones", "acme")
        self.assertError(resp, body, 503, "dnshelper_missing")

    def test_upstream_errors(self):
        self.backend.fail_with = Unavailable("down")
        resp, body = self.request("GET", "/v1/zones", "acme")
        self.assertError(resp, body, 503, "unavailable")
        self.api.zones_cache = None
        self.backend.fail_with = TaskFailed("x")
        resp, body = self.request("GET", "/v1/zones", "acme")
        self.assertError(resp, body, 502, "upstream_error")
        self.backend.fail_with = TaskRefused([{"field": "zone", "error": "not_permitted", "message": "no rule"}])
        resp, body = self.request("GET", "/v1/zones", "acme")
        self.assertError(resp, body, 403, "not_permitted")

    def test_rate_limit(self):
        write_json(self.dir, "settings.json", {"rate_limit": 3})
        os.utime(os.path.join(self.dir, "settings.json"), (2, 2))
        statuses = [self.request("GET", "/v1/zones/acme.test/records", "acme")[0].status for _ in range(2)]
        self.assertEqual(statuses, [200, 429])  # 1 list-zones + 2 per records read, then refused
        resp, body = self.request("GET", "/v1/zones", "beta")
        self.assertEqual(resp.status, 200)  # the limit is per key

    # record changes

    def key_id(self, name):
        return keyfmt.parse_key(self.keys[name])

    def writes(self):
        return [c for c in self.backend.calls if c[1] in
                ("append-records", "apply-changes", "set-records", "delete-records")]

    def test_read_key_cannot_write(self):
        for method, path in (("POST", "/v1/zones/acme.test/records"), ("POST", "/v1/zones/acme.test/changes"),
                             ("PUT", "/v1/zones/acme.test/rrsets"), ("DELETE", "/v1/zones/acme.test/records")):
            resp, body = self.request(method, path, "acme_ro", body={"bad": True})
            self.assertError(resp, body, 403, "insufficient_scope")
        self.assertFalse(self.writes())

    def test_append_by_tenant(self):
        record = {"name": "shop", "type": "A", "data": "192.0.2.9"}
        resp, body = self.request("POST", "/v1/zones/acme.test/records", "acme", body={"records": [record]})
        self.assertEqual(resp.status, 200, body)
        self.assertEqual(body["changes"]["add"][0]["name"], "shop")
        self.assertEqual(body["warnings"], [])
        agent_id, action, data = self.writes()[0]
        self.assertEqual(action, "append-records")
        self.assertEqual(data["on_behalf_of"], "t00000001:" + self.key_id("acme"))
        self.assertEqual(data["dry_run"], False)
        actions = [c[1] for c in self.backend.calls]
        self.assertLess(actions.index("list-owners"), actions.index("append-records"))

    def test_changes_go_to_the_activity_file(self):
        record = {"name": "shop", "type": "A", "data": "192.0.2.9"}
        self.request("POST", "/v1/zones/acme.test/records", "acme", body={"records": [record]})
        self.request("POST", "/v1/tenants", "operator", body={"name": "Gamma"})
        with open(os.path.join(self.usage, "activity.jsonl")) as fp:
            entries = [json.loads(line) for line in fp]
        self.assertEqual([e["action"] for e in entries], ["append-records", "add-tenant"])
        self.assertEqual(entries[0]["add"], ["shop A 192.0.2.9"])
        self.assertEqual(entries[0]["tenant"], "t00000001")
        self.assertEqual(entries[0]["result"], "ok")
        self.assertNotIn(self.keys["acme"], json.dumps(entries))

    def test_activity_names_the_acting_key(self):
        resp, body = self.request("POST", "/v1/tenants/t00000002/keys", "operator", body={"scope": "read"})
        with open(os.path.join(self.usage, "activity.jsonl")) as fp:
            entry = [json.loads(line) for line in fp][-1]
        self.assertEqual(entry["action"], "create-key")
        self.assertEqual(entry["key"], self.key_id("operator"))
        self.assertEqual(entry["target_key"], body["id"])
        self.assertNotIn(body["key"], json.dumps(entry))

    def test_write_other_tenants_zone_is_404(self):
        resp, body = self.request("POST", "/v1/zones/beta.test/records", "acme",
                                  body={"records": [{"name": "x", "type": "A", "data": "192.0.2.1"}]})
        self.assertError(resp, body, 404, "zone_not_found")
        self.assertFalse(self.writes())

    def test_edit_of_module_record_warns(self):
        mx = {"name": "@", "type": "MX", "data": "10 mail.acme.test."}
        new = {"name": "@", "type": "MX", "data": "10 mx.other.test."}
        resp, body = self.request("POST", "/v1/zones/acme.test/changes", "acme",
                                  body={"remove": [mx], "add": [new], "dry_run": True})
        self.assertEqual(resp.status, 200, body)
        self.assertTrue(body["dry_run"])
        self.assertEqual(len(body["warnings"]), 1)
        warning = body["warnings"][0]
        self.assertEqual(warning["code"], "owned_by_module")
        self.assertEqual(warning["modules"], ["mail1"])
        self.assertEqual(warning["record"]["data"], "10 mail.acme.test.")
        self.assertEqual(self.writes()[0][2]["dry_run"], True)

    def test_rrset_and_delete_warn_too(self):
        resp, body = self.request("PUT", "/v1/zones/acme.test/rrsets", "acme",
                                  body={"records": [{"name": "@", "type": "MX", "data": "20 mx.acme.test."}]})
        self.assertEqual(resp.status, 200, body)
        self.assertEqual(self.writes()[-1][2]["mode"], "rrset")
        self.assertEqual(body["warnings"][0]["modules"], ["mail1"])
        resp, body = self.request("DELETE", "/v1/zones/acme.test/records", "acme",
                                  body={"records": [{"name": "www"}]})
        self.assertEqual(resp.status, 200, body)
        self.assertEqual([r["name"] for r in body["changes"]["remove"]], ["www"])
        self.assertEqual(body["warnings"], [])

    def test_stale_remove_is_409(self):
        resp, body = self.request("POST", "/v1/zones/acme.test/changes", "acme",
                                  body={"remove": [{"name": "www", "type": "A", "data": "192.0.2.77"}]})
        self.assertError(resp, body, 409, "stale")

    def test_operator_writes_for_the_zones_tenant(self):
        record = {"name": "x", "type": "TXT", "data": "hello"}
        self.request("POST", "/v1/zones/acme.test/records", "operator", body={"records": [record]})
        self.request("POST", "/v1/zones/free.test/records", "operator", body={"records": [record]})
        behalf = [c[2]["on_behalf_of"] for c in self.writes()]
        op = self.key_id("operator")
        self.assertEqual(behalf, ["t00000001:" + op, "operator:" + op])

    def test_bad_change_bodies(self):
        cases = [
            ("POST", "/v1/zones/acme.test/records", {"records": []}, "records"),
            ("POST", "/v1/zones/acme.test/records", {"records": [{"name": "a", "type": "A"}]}, "records[0].data"),
            ("POST", "/v1/zones/acme.test/records",
             {"records": [{"name": "a", "type": "A", "data": "x", "owner": "y"}]}, "records[0]"),
            ("POST", "/v1/zones/acme.test/records",
             {"records": [{"name": "a", "type": "A", "data": "x", "ttl": True}]}, "records[0].ttl"),
            ("POST", "/v1/zones/acme.test/records",
             {"records": [{"name": "a", "type": "A-1", "data": "x"}]}, "records[0].type"),
            ("POST", "/v1/zones/acme.test/records",
             {"records": [{"name": "a", "type": "A", "data": "x"}] * 101}, "records"),
            ("POST", "/v1/zones/acme.test/changes", {"add": [], "remove": []}, None),
            ("POST", "/v1/zones/acme.test/records",
             {"records": [{"name": "a", "type": "A", "data": "x"}], "dry_run": "yes"}, "dry_run"),
            ("DELETE", "/v1/zones/acme.test/records", {"records": [{"type": "A"}]}, "records[0].name"),
        ]
        for method, path, payload, field in cases:
            resp, body = self.request(method, path, "acme", body=payload)
            self.assertError(resp, body, 400, "invalid_request")
            self.assertEqual(body["error"]["field"], field, payload)
        self.assertFalse(self.writes())

    def test_client_cannot_set_on_behalf_of(self):
        record = {"name": "x", "type": "A", "data": "192.0.2.1"}
        resp, body = self.request("POST", "/v1/zones/acme.test/records", "acme",
                                  body={"records": [record], "on_behalf_of": "someone", "zone": "beta.test"})
        self.assertEqual(resp.status, 200, body)
        data = self.writes()[0][2]
        self.assertEqual(data["zone"], "acme.test")
        self.assertTrue(data["on_behalf_of"].startswith("t00000001:"))

    # the API's own host name (DESIGN.md, The API host name in DNS)

    def reserve(self, host):
        write_json(self.dir, "settings.json", {"host": host, "rate_limit": 60})
        os.utime(os.path.join(self.dir, "settings.json"), (3, 3))

    def test_api_host_name_is_reserved(self):
        self.reserve("api.acme.test")
        rec = {"name": "api", "type": "A", "data": "198.51.100.66"}
        cases = [
            ("POST", "/v1/zones/acme.test/records", "acme", {"records": [rec]}),
            ("POST", "/v1/zones/acme.test/records", "operator", {"records": [{**rec, "name": "API."}]}),
            ("PUT", "/v1/zones/acme.test/rrsets", "acme", {"records": [rec]}),
            ("DELETE", "/v1/zones/acme.test/records", "acme", {"records": [{"name": "api"}]}),
            ("POST", "/v1/zones/acme.test/changes", "acme",
             {"remove": [{"name": "www", "type": "A", "data": "192.0.2.1"}], "add": [rec]}),
            ("POST", "/v1/zones/acme.test/records", "acme",
             {"records": [{"name": "_acme-challenge.api", "type": "TXT", "data": "x"}], "dry_run": True}),
        ]
        for method, path, key, body in cases:
            resp, out = self.request(method, path, key, body=body)
            self.assertError(resp, out, 403, "reserved_name")
        resp, out = self.request("POST", "/v1/acme/present", "acme",
                                 body={"fqdn": "_acme-challenge.api.acme.test.", "value": "v"})
        self.assertError(resp, out, 403, "reserved_name")
        self.assertFalse(self.writes())
        # other names, and reading the reserved one, are not affected
        resp, out = self.request("POST", "/v1/zones/acme.test/records", "acme",
                                 body={"records": [{"name": "api2", "type": "A", "data": "192.0.2.2"}]})
        self.assertEqual(resp.status, 200, out)
        resp, out = self.request("GET", "/v1/zones/acme.test/records?name=api", "acme")
        self.assertEqual(resp.status, 200, out)

    def test_reserved_name_only_in_its_zone(self):
        self.reserve("api.free.test")
        resp, out = self.request("POST", "/v1/zones/acme.test/records", "acme",
                                 body={"records": [{"name": "api", "type": "A", "data": "192.0.2.2"}]})
        self.assertEqual(resp.status, 200, out)

    def test_reserved_apex(self):
        self.reserve("acme.test")
        resp, out = self.request("POST", "/v1/zones/acme.test/records", "acme",
                                 body={"records": [{"name": "@", "type": "A", "data": "192.0.2.2"}]})
        self.assertError(resp, out, 403, "reserved_name")
        resp, out = self.request("POST", "/v1/acme/present", "acme",
                                 body={"fqdn": "_acme-challenge.acme.test", "value": "v"})
        self.assertError(resp, out, 403, "reserved_name")

    def test_other_tenant_gets_404_not_reserved(self):
        self.reserve("api.acme.test")
        resp, out = self.request("POST", "/v1/zones/acme.test/records", "beta",
                                 body={"records": [{"name": "api", "type": "A", "data": "192.0.2.2"}]})
        self.assertError(resp, out, 404, "zone_not_found")

    # key restrictions (DESIGN.md, ACME DNS-01 validation)

    def test_restricted_key_writes_only_inside(self):
        ok = {"name": "_acme-challenge.www", "type": "TXT", "data": "token"}
        resp, body = self.request("POST", "/v1/zones/acme.test/records", "acme_host", body={"records": [ok]})
        self.assertEqual(resp.status, 200, body)
        for bad in ({"name": "www", "type": "A", "data": "192.0.2.1"},
                    {"name": "_acme-challenge", "type": "A", "data": "192.0.2.1"},
                    {"name": "x._acme-challenge", "type": "TXT", "data": "t"}):
            resp, body = self.request("POST", "/v1/zones/acme.test/changes", "acme_host",
                                      body={"add": [ok], "remove": [bad]})
            self.assertError(resp, body, 403, "outside_restriction")
            self.assertEqual(body["error"]["field"], "remove[0]")
        # a delete without a type needs every type
        resp, body = self.request("DELETE", "/v1/zones/acme.test/records", "acme_host",
                                  body={"records": [{"name": "_acme-challenge"}]})
        self.assertError(resp, body, 403, "outside_restriction")
        self.assertEqual(len(self.writes()), 1)

    def test_restriction_any_type(self):
        resp, body = self.request("DELETE", "/v1/zones/acme.test/records", "www_any",
                                  body={"records": [{"name": "WWW."}]})
        self.assertEqual(resp.status, 200, body)

    def test_restricted_key_reads_only_inside(self):
        resp, body = self.request("GET", "/v1/zones/acme.test/records", "www_any")
        self.assertEqual([r["name"] for r in body["records"]], ["www"])
        resp, body = self.request("GET", "/v1/zones/acme.test/propagation?name=@&type=MX", "www_any")
        self.assertError(resp, body, 403, "outside_restriction")
        resp, body = self.request("GET", "/v1/zones/acme.test/propagation?name=www&type=A", "www_any")
        self.assertEqual(resp.status, 200, body)

    def test_restricted_operator_key_cannot_manage(self):
        resp, body = self.request("GET", "/v1/tenants", "op_acme")
        self.assertError(resp, body, 403, "restricted_key")
        resp, body = self.request("GET", "/v1/zones", "op_acme")
        self.assertEqual(resp.status, 200)

    def test_tenant_key_with_restrict_through_api(self):
        resp, body = self.request("POST", "/v1/tenants/t00000001/keys", "operator",
                                  body={"scope": "write", "restrict": "acme"})
        self.assertEqual(resp.status, 201, body)
        self.assertEqual(self.backend.calls[-1][2]["restrict"], "acme")

    # ACME endpoints

    def basic(self, key, user="acme"):
        import base64
        return {"Authorization": "Basic " + base64.b64encode(f"{user}:{self.keys[key]}".encode()).decode()}

    def test_acme_present_and_cleanup(self):
        msg = {"fqdn": "_acme-challenge.www.acme.test.", "value": "LHDhK3oGRvkiefQnx7OOczTY5Tic_xZ6HcMOc_gmtoM"}
        resp, body = self.request("POST", "/v1/acme/present", headers=self.basic("acme_host"), body=msg)
        self.assertEqual(resp.status, 200, body)
        # Caddy's acmeproxy module needs exactly 200, and fqdn and value echoed as sent
        self.assertEqual((body["fqdn"], body["value"], body["zone"]), (msg["fqdn"], msg["value"], "acme.test"))
        agent_id, action, data = self.writes()[-1]
        self.assertEqual(action, "append-records")
        self.assertEqual(data["records"], [{"name": "_acme-challenge.www", "type": "TXT", "ttl": 60,
                                            "data": msg["value"]}])
        self.assertFalse(data["dry_run"])
        self.assertTrue(data["on_behalf_of"].startswith("t00000001:"))
        resp, body = self.request("POST", "/v1/acme/cleanup", headers=self.basic("acme_host"), body=msg)
        self.assertEqual(resp.status, 200, body)
        self.assertIn('"%s"' % msg["value"], json.dumps(body))  # what acme.sh looks for
        agent_id, action, data = self.writes()[-1]
        self.assertEqual(action, "delete-records")
        self.assertEqual(data["records"], [{"name": "_acme-challenge.www", "type": "TXT", "data": msg["value"]}])

    def test_acme_apex_and_bearer(self):
        msg = {"fqdn": "_acme-challenge.acme.test", "value": "v"}
        resp, body = self.request("POST", "/v1/acme/present", "acme", body=msg)
        self.assertEqual(resp.status, 200, body)
        self.assertEqual(self.writes()[-1][2]["records"][0]["name"], "_acme-challenge")

    def test_acme_refusals(self):
        cases = [
            ({"fqdn": "www.acme.test.", "value": "v"}, 400, "invalid_request"),
            ({"fqdn": "_acme-challenge.www.beta.test.", "value": "v"}, 404, "zone_not_found"),
            ({"fqdn": "_acme-challenge.www.other.test.", "value": "v"}, 404, "zone_not_found"),
            ({"fqdn": "_acme-challenge.www.acme.test."}, 400, "invalid_request"),
            ({"domain": "acme.test", "token": "t", "keyAuth": "k"}, 400, "invalid_request"),  # lego RAW mode
        ]
        for msg, status, code in cases:
            resp, body = self.request("POST", "/v1/acme/present", headers=self.basic("acme_host"), body=msg)
            self.assertError(resp, body, status, code)
        resp, body = self.request("POST", "/v1/acme/present", headers=self.basic("acme_ro"),
                                  body={"fqdn": "_acme-challenge.acme.test.", "value": "v"})
        self.assertError(resp, body, 403, "insufficient_scope")
        self.assertFalse(self.writes())

    def test_acme_restriction_still_applies(self):
        resp, body = self.request("POST", "/v1/acme/present", headers=self.basic("www_any"),
                                  body={"fqdn": "_acme-challenge.acme.test.", "value": "v"})
        self.assertError(resp, body, 403, "outside_restriction")

    def test_basic_only_on_acme_endpoints(self):
        resp, body = self.request("GET", "/v1/zones", headers=self.basic("acme"))
        self.assertError(resp, body, 401, "invalid_key")
        resp, body = self.request("POST", "/v1/acme/present", headers={"Authorization": "Basic !!!"},
                                  body={"fqdn": "_acme-challenge.acme.test.", "value": "v"})
        self.assertError(resp, body, 401, "invalid_key")

    def test_acme_operator_picks_longest_zone(self):
        self.request("POST", "/v1/acme/present", headers=self.basic("op_acme"),
                     body={"fqdn": "_acme-challenge.host.free.test.", "value": "v"})
        data = self.writes()[-1][2]
        self.assertEqual((data["zone"], data["records"][0]["name"]), ("free.test", "_acme-challenge.host"))
        self.assertEqual(data["on_behalf_of"], "operator:" + self.key_id("op_acme"))

    # tenants (operator)

    def test_tenant_endpoints_hidden_from_tenants(self):
        resp, body = self.request("GET", "/v1/tenants", "acme")
        self.assertError(resp, body, 404, "not_found")

    def test_read_scope(self):
        resp, body = self.request("POST", "/v1/tenants", "operator_ro", body={"name": "X"})
        self.assertError(resp, body, 403, "insufficient_scope")
        resp, body = self.request("GET", "/v1/tenants", "operator_ro")
        self.assertEqual(resp.status, 200)

    def test_add_tenant_calls_own_action(self):
        resp, body = self.request("POST", "/v1/tenants", "operator", body={"name": "Gamma", "zones": ["x"]})
        self.assertEqual(resp.status, 201, body)
        self.assertEqual(body["id"], "t00000009")
        self.assertEqual(body["name"], "Gamma")
        call = self.backend.calls[-1]
        self.assertEqual(call, ("self", "add-tenant", {"name": "Gamma"}))

    def test_get_tenant(self):
        resp, body = self.request("GET", "/v1/tenants/t00000001", "operator")
        self.assertEqual(body["zones"], ["acme.test"])
        resp, body = self.request("GET", "/v1/tenants/t99999999", "operator")
        self.assertError(resp, body, 404, "tenant_not_found")

    def test_assign_conflict(self):
        resp, body = self.request("PUT", "/v1/tenants/t00000002/zones/acme.test", "operator")
        self.assertError(resp, body, 409, "zone_assigned")
        resp, body = self.request("PUT", "/v1/tenants/t00000002/zones/free.test", "operator")
        self.assertEqual(resp.status, 200, body)
        self.assertEqual(body["zones"], ["beta.test", "free.test"])

    def test_create_and_revoke_tenant_key(self):
        resp, body = self.request("POST", "/v1/tenants/t00000002/keys", "operator",
                                  body={"scope": "read", "label": "beta script"})
        self.assertEqual(resp.status, 201, body)
        key = body["key"]
        self.assertTrue(key.startswith("dnsapi_" + body["id"] + "_"))
        call = self.backend.calls[-1]
        self.assertEqual(call[1], "create-key")
        self.assertNotIn(key, json.dumps(call[2]))  # only the hash is sent
        self.assertEqual(call[2]["hash"], keyfmt.hash_key(key))
        resp, zones = self.request("GET", "/v1/zones", key)
        self.assertEqual([z["zone"] for z in zones["zones"]], ["beta.test"])
        resp, listed = self.request("GET", "/v1/tenants/t00000002/keys", "operator")
        self.assertIn(body["id"], [k["id"] for k in listed["keys"]])
        self.assertNotIn("hash", json.dumps(listed))
        resp, _ = self.request("DELETE", f"/v1/tenants/t00000002/keys/{body['id']}", "operator")
        self.assertEqual(resp.status, 204)
        resp, again = self.request("GET", "/v1/zones", key)
        self.assertError(resp, again, 401, "invalid_key")

    def test_revoke_other_tenants_key(self):
        acme_id = keyfmt.parse_key(self.keys["acme"])
        resp, body = self.request("DELETE", f"/v1/tenants/t00000002/keys/{acme_id}", "operator")
        self.assertError(resp, body, 404, "key_not_found")


class BrokerClientTest(unittest.TestCase):
    """The service's side of the broker protocol, against a fake broker socket."""

    def setUp(self):
        import socketserver
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, "broker.sock")
        self.answer = {}
        self.seen = []
        test = self

        class H(socketserver.StreamRequestHandler):
            def handle(self):
                test.seen.append(json.loads(self.rfile.readline()))
                self.wfile.write(json.dumps(test.answer).encode() + b"\n")

        self.server = socketserver.ThreadingUnixStreamServer(self.path, H)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.backend = Backend(self.path, timeout=5)

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        shutil.rmtree(self.dir)

    def test_answers(self):
        self.answer = {"exit_code": 0, "output": {"zones": []}, "error": ""}
        self.assertEqual(self.backend.run("dnshelper", "list-zones", {}), {"zones": []})
        self.assertEqual(self.seen[-1], {"target": "dnshelper", "action": "list-zones", "data": {}})
        self.answer = {"exit_code": 2, "output": [{"field": "zone", "error": "stale"}]}
        with self.assertRaises(TaskRefused):
            self.backend.run("dnshelper", "apply-changes", {})
        self.answer = {"exit_code": 1, "output": None, "error": "boom"}
        with self.assertRaises(TaskFailed):
            self.backend.run("dnshelper", "get-records", {})
        self.answer = {"unavailable": "dnshelper_missing"}
        with self.assertRaises(DnshelperMissing):
            self.backend.run("dnshelper", "list-zones", {})
        self.answer = {"unavailable": "api_server"}
        with self.assertRaises(Unavailable):
            self.backend.run("self", "add-tenant", {})
        self.answer = {"refused": "not allowed"}
        with self.assertRaises(TaskFailed):
            self.backend.run("self", "add-tenant", {})

    def test_no_broker(self):
        with self.assertRaises(Unavailable):
            Backend(os.path.join(self.dir, "missing.sock"), timeout=2).run("self", "add-tenant", {})


class BrokerTest(unittest.TestCase):
    """The broker's allowlist and its socket (DESIGN.md, Runtime, The broker)."""

    def setUp(self):
        from dnsapi_server import broker
        self.broker = broker
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, "broker.sock")
        self.calls = []
        self.dnshelper = "module/dnshelper4"
        test = self

        class Client:
            def run(self, agent_id, action, data):
                test.calls.append((agent_id, action))
                return {"exit_code": 0, "output": {"done": action}, "error": ""}

        self.server = broker.Server(self.path, broker.Broker(lambda: self.dnshelper, lambda: "module/dnsapi3", Client()))
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.client = Backend(self.path, timeout=5)

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        shutil.rmtree(self.dir)

    def test_socket_mode(self):
        self.assertEqual(os.stat(self.path).st_mode & 0o777, 0o600)

    def test_allowlist(self):
        allowed = [
            ("dnshelper", "list-zones", {}),
            ("dnshelper", "get-records", {"zone": "x"}),
            ("dnshelper", "apply-changes", {"zone": "x", "on_behalf_of": "t1:k"}),
            ("self", "add-tenant", {"name": "x"}),
            ("self", "create-key", {"owner": "t00000001"}),
            ("self", "revoke-key", {"id": "abcdef12"}),
        ]
        refused = [
            ("dnshelper", "append-records", {"zone": "x"}),  # no on_behalf_of
            ("dnshelper", "set-policy", {"rules": []}),
            ("dnshelper", "add-zone", {}),
            ("dnshelper", "has-zone", {"name": "x"}),
            ("self", "configure-module", {}),
            ("self", "create-key", {"owner": "operator"}),
            ("traefik", "set-route", {}),
            ("node", "get-fqdn", {}),
        ]
        for target, action, data in allowed:
            self.assertEqual(self.client.run(target, action, data), {"done": action})
        for target, action, data in refused:
            with self.assertRaises(TaskFailed, msg=(target, action)):
                self.client.run(target, action, data)
        self.assertEqual([c[1] for c in self.calls], [a[1] for a in allowed])
        self.assertEqual(self.calls[0][0], "module/dnshelper4")
        self.assertEqual(self.calls[3][0], "module/dnsapi3")

    def test_dnshelper_missing(self):
        self.dnshelper = None
        with self.assertRaises(DnshelperMissing):
            self.client.run("dnshelper", "list-zones", {})

    def test_garbage(self):
        import socket
        with socket.socket(socket.AF_UNIX) as sock:
            sock.connect(self.path)
            sock.sendall(b"not json\n")
            self.assertIn("refused", json.loads(sock.makefile().readline()))


class ApiClientTest(unittest.TestCase):
    def test_reads_only_the_credentials(self):
        from dnsapi_server.apiclient import ApiClient
        directory = tempfile.mkdtemp()
        try:
            path = os.path.join(directory, "agent.env")
            with open(path, "w") as fp:
                fp.write("PATH=/bad\nREDIS_USER=module/dnsapi7\nREDIS_PASSWORD=p=w\nPYTHONPATH=/bad\n")
            self.assertEqual(ApiClient(path).credentials(), ("module/dnsapi7", "p=w"))
        finally:
            shutil.rmtree(directory)


class KeyTest(unittest.TestCase):
    def test_format(self):
        key_id, key, key_hash = keyfmt.new_key()
        self.assertEqual(keyfmt.parse_key(key), key_id)
        self.assertEqual(len(key), len("dnsapi_") + 8 + 1 + 52)
        self.assertTrue(keyfmt.hash_matches(key, key_hash))
        self.assertFalse(keyfmt.hash_matches(key, "0" * 64))
        self.assertIsNone(keyfmt.parse_key("dnsapi_ABCDEF12_" + "a" * 52))


if __name__ == "__main__":
    unittest.main()
