#!/usr/bin/env python3
#
# Copyright (C) 2026 Dan Brown
# SPDX-License-Identifier: GPL-3.0-or-later
#
"""Local harness for the dnsapi UI: a mock NS8 API serving the built UI
(ui/dist) inside a fake shell (harness.html). Adapted from ns8-automx's and
ns8-dnshelper's ui/dev.

    python3 ui/dev/server.py [port]        then open http://127.0.0.1:8099/

dnsapi's actions need a node (dnshelper, Traefik, the API service), so they
are faked here, in memory: dnshelper1 lets dnsapi write in four zones (three
in full, one with the ACME preset only), two tenants, five keys and some
activity. Tenant and key views come from the module's real dnsapi.state
code; output shapes follow each action's validate-output.json, so check
them again when an output schema changes.

Environment: CORE_CSS=<the NS8 core UI's stylesheet> gives the shell's
styling (see README.md).
"""
import datetime
import json
import os
import sys
import threading
import time
import traceback
import types
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "imageroot", "pypkg"))
sys.modules["agent"] = types.ModuleType("agent")  # dnsapi.state imports it only to fail an action
from dnsapi import state  # noqa: E402

DIST = os.path.join(HERE, "..", "dist")
CORE_CSS = os.environ.get("CORE_CSS", "")
EVENTS, LOCK = [], threading.Lock()

MODULE_ID = "dnsapi1"
HOST = "dnsapi.example.com"
NODE_FQDN = "node1.example.com"
INSTALLED = {
    "ghcr.io/danb35/dnsapi": [{"id": MODULE_ID, "node": "1", "module": "dnsapi", "ui_name": "",
                               "version": "0.1.0", "source": "ghcr.io/danb35/dnsapi"}],
}

# What dnshelper lets dnsapi write: zone -> (provider, full)
ZONES = {
    "acme-shop.com": ("cloudflare", True),
    "bakery.example": ("powerdns", True),
    "example.com": ("cloudflare", True),
    "internal.example.net": ("hetzner", False),
}
SETTINGS = {"host": HOST, "lets_encrypt": True, "ip_allowlist": [],
            "rate_limit": 60, "publish_host_record": True, "revoke_cleartext_keys": True}
# EXPOSED=1 shows the Status page's notice about a key revoked for being sent over plain HTTP
EXPOSED = [{"time": "2026-11-22T09:30:00Z", "key": "7d41e9b2", "owner": "t81c0d4e7",
            "tenant_name": "Corner Bakery", "address": "198.51.100.23"}] if os.environ.get("EXPOSED") else []
HOST_RECORD = {"host": HOST, "target": NODE_FQDN, "zone": "example.com", "status": "created",
               "existing": [], "message": "", "checked": "2026-11-22T09:12:00Z"}
TENANTS, KEYS, LAST_USED, ACTIVITY = {}, {}, {}, []


def stamp(minutes_ago):
    t = datetime.datetime(2026, 11, 22, 10, 0, tzinfo=datetime.timezone.utc) - datetime.timedelta(minutes=minutes_ago)
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def seed():
    TENANTS.update({
        "t3f9a21c0": {"name": "Acme Shop", "enabled": True, "zones": ["acme-shop.com"], "created": stamp(4000)},
        "t81c0d4e7": {"name": "Corner Bakery", "enabled": True, "zones": ["bakery.example"], "created": stamp(3000)},
        "t5be20a93": {"name": "Internal hosts", "enabled": True, "zones": ["internal.example.net"],
                      "created": stamp(2000)},
    })
    keys = [
        ("4c1e9a07", "operator", "write", "Billing portal", ["203.0.113.10"], None, None, 3),
        ("9d2f6b18", "t3f9a21c0", "write", "Acme's deploy script", [], None, None, 600),
        ("b7a35e42", "t81c0d4e7", "read", "Bakery monitoring", [], "2027-06-30T00:00:00Z", None, 45),
        ("e06c8d51", "t5be20a93", "write", "host1 certificates", ["10.0.0.5"], None, "acme", 1500),
        ("f41b7c29", "t5be20a93", "write", "nas certificates", ["10.0.0.9"], None, "acme", None),
        ("2a6d03f5", "t3f9a21c0", "read", "Acme's old monitor", [], "2026-10-01T00:00:00Z", None, 75000),
        ("6e8b14c3", "operator", "write", "Old billing portal", [], None, None, 9000),
    ]
    for kid, owner, scope, label, allow, expires, restrict, used in keys:
        KEYS[kid] = {"owner": owner, "scope": scope, "label": label, "allowlist": allow, "expires": expires,
                     "restrict": state.parse_restrict(restrict), "created": stamp(2500), "hash": "0" * 64}
        if used is not None:
            LAST_USED[kid] = stamp(used)
    KEYS["6e8b14c3"].update(revoked=stamp(8000), revoked_reason="revoked")
    api = {"source": "api", "address": "203.0.113.10", "result": "ok"}
    ACTIVITY.extend([
        {**api, "time": stamp(3), "key": "4c1e9a07", "owner": "operator", "tenant": "t3f9a21c0",
         "action": "apply-changes", "zone": "acme-shop.com", "add": ["www A 192.0.2.20"],
         "remove": ["www A 192.0.2.10"]},
        {**api, "time": stamp(9), "key": "4c1e9a07", "owner": "operator", "tenant": "t81c0d4e7",
         "action": "append-records", "zone": "bakery.example",
         "add": ["@ TXT v=spf1 include:_spf.mail.example.com ~all"], "remove": [], "result": "dry-run"},
        {**api, "time": stamp(25), "key": "e06c8d51", "owner": "t5be20a93", "tenant": "t5be20a93",
         "address": "10.0.0.5", "action": "delete-records", "zone": "internal.example.net", "add": [],
         "remove": ["_acme-challenge.host1 TXT 9ihDbjYfTExAYeDs4DBUeuTo18KBzwvTEjUnSwd32-c"]},
        {**api, "time": stamp(26), "key": "e06c8d51", "owner": "t5be20a93", "tenant": "t5be20a93",
         "address": "10.0.0.5", "action": "append-records", "zone": "internal.example.net",
         "add": ["_acme-challenge.host1 TXT 9ihDbjYfTExAYeDs4DBUeuTo18KBzwvTEjUnSwd32-c"], "remove": []},
        {**api, "time": stamp(40), "key": "9d2f6b18", "owner": "t3f9a21c0", "tenant": "t3f9a21c0",
         "address": "198.51.100.23", "action": "apply-changes", "zone": "acme-shop.com",
         "add": ["shop CNAME acme-shop.myshopify.com."], "remove": [], "result": "rejected:conflict"},
        {"source": "admin", "time": stamp(2000), "caller": "admin", "action": "add-tenant", "result": "ok",
         "tenant": "t5be20a93", "name": "Internal hosts"},
    ])


class Refused(Exception):
    def __init__(self, field, error, value, message=""):
        self.errors = [{"field": field, "parameter": field, "value": value, "error": error, "message": message}]


def tenant_out(tid):
    view = state.tenant_view(tid, TENANTS[tid])
    view["keys"] = sum(1 for k in state.active_keys(KEYS).values() if k["owner"] == tid)
    return view


def tenant_of(zone):
    return next((tid for tid, t in TENANTS.items() if zone in t["zones"]), None)


def get_overview(data):
    return {
        "host": HOST, "url": f"https://{HOST}/v1/", "dnshelper": "dnshelper1", "dnshelper_error": None,
        "zones_writable": len(ZONES), "zones_full": sum(1 for _, full in ZONES.values() if full),
        "zones_assigned": sum(len(t["zones"]) for t in TENANTS.values()),
        "tenants": len(TENANTS), "tenants_disabled": sum(1 for t in TENANTS.values() if not t["enabled"]),
        "keys_operator": sum(1 for k in state.active_keys(KEYS).values() if k["owner"] == "operator"),
        "keys_tenant": sum(1 for k in state.active_keys(KEYS).values() if k["owner"] != "operator"),
        "host_record": HOST_RECORD,
        "exposed_keys": EXPOSED,
    }


def get_configuration(data):
    return {**SETTINGS, "host_record": HOST_RECORD}


def configure_module(data):
    data = data or {}
    time.sleep(1)  # set-route takes a while
    # A host name starting with "norule." in example.com acts as one dnshelper has no rule for:
    # the host record is saved as not_permitted, then the certificate fails and nothing else is
    if data.get("host", "").startswith("norule.") and data.get("publish_host_record"):
        HOST_RECORD.clear()
        HOST_RECORD.update({"host": data["host"], "target": NODE_FQDN, "zone": "example.com",
                            "status": "not_permitted", "existing": [], "message": "",
                            "checked": "2026-11-22T10:00:00Z"})
        if data.get("lets_encrypt"):
            raise Refused("host", "newcert_acme_error", data["host"])
    SETTINGS.update({k: v for k, v in data.items() if k in SETTINGS})
    return None


def list_assignable_zones(data):
    return {"dnshelper": "dnshelper1", "error": None,
            "zones": [{"zone": z, "provider": p, "tenant": tenant_of(z), "full": full}
                      for z, (p, full) in sorted(ZONES.items())]}


def add_tenant(data):
    tid = "t%08x" % (0x1a2b3c4d + len(TENANTS))
    TENANTS[tid] = {"name": data["name"], "enabled": data.get("enabled", True), "zones": [], "created": stamp(0)}
    return tenant_out(tid)


def update_tenant(data):
    tenant = TENANTS[data["id"]]
    tenant.update({k: data[k] for k in ("name", "enabled") if k in data})
    return tenant_out(data["id"])


def remove_tenant(data):
    TENANTS.pop(data["id"])
    for kid in [k for k, r in KEYS.items() if r["owner"] == data["id"]]:
        del KEYS[kid]
    return {}


def assign_zone(data):
    owner = tenant_of(data["zone"])
    if owner and owner != data["tenant"]:
        raise Refused("zone", "zone_assigned", data["zone"], "the zone belongs to another tenant")
    if data["zone"] not in TENANTS[data["tenant"]]["zones"]:
        TENANTS[data["tenant"]]["zones"].append(data["zone"])
    return tenant_out(data["tenant"])


def unassign_zone(data):
    zones = TENANTS[data["tenant"]]["zones"]
    if data["zone"] in zones:
        zones.remove(data["zone"])
    return tenant_out(data["tenant"])


def list_keys(data):
    owner = (data or {}).get("owner")
    return {"keys": [state.key_view(k, r, LAST_USED) for k, r in sorted(KEYS.items())
                     if owner in (None, r["owner"])]}


def create_key(data):
    KEYS[data["id"]] = {"owner": data["owner"], "scope": data["scope"], "label": data.get("label", ""),
                        "allowlist": data.get("allowlist") or [], "expires": data.get("expires"),
                        "restrict": state.parse_restrict(data.get("restrict")), "created": stamp(0),
                        "hash": data["hash"]}
    return state.key_view(data["id"], KEYS[data["id"]], LAST_USED)


def revoke_key(data):
    if KEYS[data["id"]].get("revoked"):
        raise Refused("id", "key_revoked", data["id"], "the key is already revoked")
    KEYS[data["id"]].update(revoked=state.now(), revoked_reason="revoked")
    return {}


def list_activity(data):
    return {"entries": ACTIVITY[: (data or {}).get("limit", 200)]}


def get_status(data):
    return {
        "instance": MODULE_ID, "ui_name": "", "node": "1", "node_ui_name": "",
        "services": [{"name": "dnsapi", "active": True, "enabled": True, "failed": False},
                     {"name": "dnsapi-broker", "active": True, "enabled": True, "failed": False}],
        "images": [{"name": "ghcr.io/danb35/dnsapi-server:0.1.0", "size": "131 MB",
                    "created": "2026-11-22 08:00:00 +0000 UTC"}],
        "volumes": [],
    }


MODULE_ACTIONS = {
    "get-overview": get_overview, "get-configuration": get_configuration, "configure-module": configure_module,
    "list-assignable-zones": list_assignable_zones, "list-tenants":
        lambda data: {"tenants": [tenant_out(t) for t in sorted(TENANTS, key=lambda t: TENANTS[t]["name"])]},
    "add-tenant": add_tenant, "update-tenant": update_tenant, "remove-tenant": remove_tenant,
    "assign-zone": assign_zone, "unassign-zone": unassign_zone, "list-keys": list_keys,
    "create-key": create_key, "revoke-key": revoke_key, "list-activity": list_activity, "get-status": get_status,
}
CLUSTER_ACTIONS = {
    "list-installed-modules": lambda data: INSTALLED,
    "list-backup-repositories": lambda data: {"repositories": []},
    "list-backups": lambda data: {"backups": []},
}


def run(kind, module_id, body):
    action, data, event = body["action"], body.get("data"), body["extra"]["eventId"]
    time.sleep(0.15)  # a task takes a moment
    ev = {"action": action, "eventId": event, "type": "completed", "output": None}
    try:
        handlers = CLUSTER_ACTIONS if kind == "cluster" else MODULE_ACTIONS
        ev["output"] = handlers[action](data)
    except Refused as e:
        ev.update(type="validation-failed", errors=e.errors, output=None)
    except Exception as e:  # unknown action, bug: show it as a failed task
        print("harness error", kind, repr(module_id), action, file=sys.stderr)
        traceback.print_exc()
        ev.update(type="aborted", output={"error": repr(e)})
    with LOCK:
        # kept, not handed out once: a dropped response or a second viewer must not lose results
        ev["seq"] = len(EVENTS) + 1
        EVENTS.append(ev)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def send(self, code, body, ctype="application/json"):
        raw = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/api/events":
            after = int((parse_qs(urlparse(self.path).query).get("after") or ["0"])[0])
            with LOCK:
                out = [e for e in EVENTS if e["seq"] > after]
            return self.send(200, out)
        if path == "/":
            return self.send(200, open(os.path.join(HERE, "harness.html"), "rb").read(), "text/html")
        if path == "/cluster-admin/css/core.css" and os.path.isfile(CORE_CSS):
            return self.send(200, open(CORE_CSS, "rb").read(), "text/css")
        if path.startswith("/app/"):
            rel = path[len("/app/"):] or "index.html"
            full = os.path.normpath(os.path.join(DIST, rel))
            if full.startswith(os.path.normpath(DIST)) and os.path.isfile(full):
                ctype = {".js": "text/javascript", ".css": "text/css", ".html": "text/html",
                         ".json": "application/json", ".png": "image/png", ".svg": "image/svg+xml"
                         }.get(os.path.splitext(full)[1], "application/octet-stream")
                return self.send(200, open(full, "rb").read(), ctype)
        self.send(404, {"error": "not found"})

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        parts = self.path.strip("/").split("/")  # api/module/<id>/tasks | api/cluster/tasks
        if parts[:2] == ["api", "module"] and parts[-1] == "tasks":
            kind, module_id = "module", parts[2]
        elif parts[:2] == ["api", "cluster"] and parts[-1] == "tasks":
            kind, module_id = "cluster", ""
        else:
            return self.send(404, {"error": "unknown api"})
        threading.Thread(target=run, args=(kind, module_id, body), daemon=True).start()
        self.send(200, {"result": "ok"})


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8099
    seed()
    print(f"open http://127.0.0.1:{port}/", flush=True)
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
