#
# Copyright (C) 2026 Dan Brown
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Domains added through the API (DESIGN.md, Phase 2): POST and DELETE /v1/zones,
# POST /v1/zones/provision and the one-shot clean-up.

import json
import os
import unittest

from dnsapi_server.backend import TaskRefused, Unavailable

from test_app import ZONES, ApiTest, FakeBackend

TOKEN = "customer-token-not-real-0123"
CREDS = {"api_token": TOKEN}


def refused(code, field="zone", message=""):
    return TaskRefused([{"field": field, "error": code, "value": "", "message": message or code}])


class DelegateBackend(FakeBackend):
    """FakeBackend plus what dnshelper 0.8.0 lets a delegate do."""

    def __init__(self, store):
        super().__init__(store)
        self.creds = {}   # id -> provider
        self.zones = {}   # zone -> credential id (dnsapi's own)
        self.refuse = {}  # action -> TaskRefused to raise
        self.next = 0

    def run(self, agent_id, action, data):
        if self.fail_with:
            return super().run(agent_id, action, data)
        if agent_id == "dnshelper" and action in self.refuse:
            self.calls.append((agent_id, action, data))
            raise self.refuse[action]
        if agent_id == "dnshelper" and action == "list-zones":
            self.calls.append((agent_id, action, data))
            own = [{"zone": z, "credential": c, "provider": self.creds.get(c), "delegated": True,
                    "access": "write", "full": True} for z, c in sorted(self.zones.items())]
            return {"zones": [dict(z, delegated=False) for z in ZONES] + own}
        if agent_id == "dnshelper" and action == "validate-zone":
            self.calls.append((agent_id, action, data))
            if "bad" in json.dumps(data.get("fields", {})):
                raise refused("auth_failed", "credentials", "the DNS host refused the credential")
            return {"valid": True, "validation": {"method": "list"}, "capabilities": {}}
        if agent_id == "dnshelper" and action == "add-credential":
            self.calls.append((agent_id, action, data))
            self.next += 1
            cid = f"c{self.next:08x}"
            self.creds[cid] = data["provider"]
            return {"id": cid}
        if agent_id == "dnshelper" and action == "add-zone":
            self.calls.append((agent_id, action, data))
            if data["zone"] in self.zones or data["zone"] in {z["zone"] for z in ZONES}:
                raise refused("zone_already_configured")
            self.zones[data["zone"]] = data["credential"]
            return {}
        if agent_id == "dnshelper" and action == "update-zone":
            self.calls.append((agent_id, action, data))
            if data["zone"] not in self.zones or data["credential"] not in self.creds:
                raise refused("not_permitted")
            self.zones[data["zone"]] = data["credential"]
            return {}
        if agent_id == "dnshelper" and action == "remove-zone":
            self.calls.append((agent_id, action, data))
            if data["zone"] not in self.zones:
                raise refused("not_permitted")
            del self.zones[data["zone"]]
            return {}
        if agent_id == "dnshelper" and action == "remove-credential":
            self.calls.append((agent_id, action, data))
            if data["id"] not in self.creds:
                raise refused("credential_not_found", "id")
            if data["id"] in self.zones.values():
                raise refused("credential_in_use", "id")
            del self.creds[data["id"]]
            return {}
        if agent_id == "self" and action == "unassign-zone":
            self.calls.append((agent_id, action, data))
            state = self.store.state_dir
            tenants = json.load(open(os.path.join(state, "tenants.json")))
            tenants["tenants"][data["tenant"]]["zones"].remove(data["zone"])
            with open(os.path.join(state, "tenants.json"), "w") as fp:
                json.dump(tenants, fp)
            return {}
        return super().run(agent_id, action, data)


class DomainTest(ApiTest):
    def setUp(self):
        super().setUp()
        self.backend = DelegateBackend(self.api.store)
        self.api.backend = self.backend

    def actions(self):
        return [c[1] for c in self.backend.calls if c[0] == "dnshelper" and c[1] != "list-providers"]

    def journal(self):
        path = os.path.join(self.usage, "provisioning.json")
        return json.load(open(path)) if os.path.exists(path) else {}

    def assertNoSecret(self):
        for name in os.listdir(self.usage):
            with open(os.path.join(self.usage, name)) as fp:
                self.assertNotIn(TOKEN, fp.read(), name)

    # hosting

    def test_add_a_hosted_zone_for_a_tenant(self):
        resp, body = self.request("POST", "/v1/zones", "operator", {
            "zone": "Customer.Example.", "provider": "cloudflare", "credentials": CREDS, "tenant": "t00000001"})
        self.assertEqual(resp.status, 201, body)
        self.assertEqual(body, {"zone": "customer.example", "provider": "cloudflare", "tenant": "t00000001",
                                "full": True, "hosted": True, "dry_run": False})
        self.assertEqual(self.actions(), ["validate-zone", "add-credential", "add-zone"])
        validate = next(c[2] for c in self.backend.calls if c[1] == "validate-zone")
        self.assertEqual(validate, {"zone": "customer.example", "provider": "cloudflare", "fields": CREDS})
        add = next(c[2] for c in self.backend.calls if c[1] == "add-credential")
        self.assertEqual(add["name"], "dnsapi: customer.example")
        self.assertIn(("self", "assign-zone", {"tenant": "t00000001", "zone": "customer.example"}),
                      self.backend.calls)
        # the tenant reaches it like any of its zones; the operator sees it as hosted
        resp, body = self.request("GET", "/v1/zones", "acme")
        self.assertIn("customer.example", [z["zone"] for z in body["zones"]])
        resp, body = self.request("GET", "/v1/zones", "operator")
        hosted = {z["zone"]: z["hosted"] for z in body["zones"]}
        self.assertTrue(hosted["customer.example"])
        self.assertFalse(hosted["acme.test"])
        resp, body = self.request("GET", "/v1/zones/customer.example/records", "acme")
        self.assertEqual(resp.status, 200, body)
        activity = [json.loads(line) for line in open(os.path.join(self.usage, "activity.jsonl"))]
        self.assertEqual(activity[-1]["action"], "add-zone")
        self.assertEqual(activity[-1]["provider"], "cloudflare")
        self.assertNoSecret()

    def test_dry_run_stores_nothing(self):
        resp, body = self.request("POST", "/v1/zones", "operator", {
            "zone": "customer.example", "provider": "cloudflare", "credentials": CREDS, "dry_run": True})
        self.assertEqual(resp.status, 200, body)
        self.assertEqual((body["dry_run"], body["valid"]), (True, True))
        self.assertEqual(self.actions(), ["validate-zone"])
        self.assertEqual(self.backend.creds, {})

    def test_bad_credentials_store_nothing(self):
        resp, body = self.request("POST", "/v1/zones", "operator", {
            "zone": "customer.example", "provider": "cloudflare", "credentials": {"api_token": "bad"}})
        self.assertError(resp, body, 502, "auth_failed")
        self.assertEqual(self.actions(), ["validate-zone"])
        self.assertEqual(self.backend.creds, {})

    def test_a_managed_zone_is_409_and_the_credential_is_removed(self):
        resp, body = self.request("POST", "/v1/zones", "operator", {
            "zone": "acme.test", "provider": "cloudflare", "credentials": CREDS})
        self.assertError(resp, body, 409, "zone_already_configured")
        self.assertEqual(self.actions(), ["validate-zone", "add-credential", "add-zone", "remove-credential"])
        self.assertEqual(self.backend.creds, {})
        self.backend.refuse["add-zone"] = refused("zone_overlaps")
        resp, body = self.request("POST", "/v1/zones", "operator", {
            "zone": "shop.acme.test", "provider": "cloudflare", "credentials": CREDS})
        self.assertError(resp, body, 409, "zone_overlaps")
        self.assertEqual(self.backend.creds, {})

    def test_a_failed_assignment_undoes_the_zone(self):
        tenants = json.load(open(os.path.join(self.dir, "tenants.json")))
        tenants["tenants"]["t00000002"]["zones"].append("customer.example")
        with open(os.path.join(self.dir, "tenants.json"), "w") as fp:
            json.dump(tenants, fp)
        resp, body = self.request("POST", "/v1/zones", "operator", {
            "zone": "customer.example", "provider": "cloudflare", "credentials": CREDS, "tenant": "t00000001"})
        self.assertError(resp, body, 409, "zone_assigned")
        self.assertEqual((self.backend.zones, self.backend.creds), ({}, {}))

    def test_not_a_delegate(self):
        self.backend.refuse["validate-zone"] = refused(
            "not_permitted", "zone", "this module may not add or change zones and credentials: it is not "
            "one of the delegates in dnshelper's settings")
        resp, body = self.request("POST", "/v1/zones", "operator", {
            "zone": "customer.example", "provider": "cloudflare", "credentials": CREDS})
        self.assertError(resp, body, 403, "not_permitted")
        self.assertIn("delegates", body["error"]["message"])

    def test_bad_requests(self):
        base = {"zone": "customer.example", "provider": "cloudflare", "credentials": CREDS}
        for change, code, field in [
                ({"zone": "nodot"}, "invalid_zone", "zone"),
                ({"zone": 5}, "invalid_zone", "zone"),
                ({"provider": "nosuch"}, "unknown_provider", "provider"),
                ({"provider": None}, "invalid_request", "provider"),
                ({"credentials": "x"}, "invalid_request", "credentials"),
                ({"credentials": {"api_token": TOKEN, "extra": "x"}}, "unknown_field", "credentials.extra"),
                ({"credentials": {"api_token": 5}}, "invalid_request", "credentials.api_token"),
                ({"credentials": {"api_token": "x" * 5000}}, "invalid_request", "credentials.api_token"),
                ({"credentials": {}}, "required", "credentials.api_token"),
                ({"dry_run": "yes"}, "invalid_request", "dry_run")]:
            resp, body = self.request("POST", "/v1/zones", "operator", {**base, **change})
            self.assertError(resp, body, 400, code)
            self.assertEqual(body["error"]["field"], field, change)
        resp, body = self.request("POST", "/v1/zones", "operator", {**base, "tenant": "t99999999"})
        self.assertError(resp, body, 404, "tenant_not_found")
        # a default fills a required field (rfc2136's key_alg is not required; server is)
        resp, body = self.request("POST", "/v1/zones", "operator", {
            "zone": "customer.example", "provider": "rfc2136", "credentials": {}, "dry_run": True})
        self.assertError(resp, body, 400, "required")
        self.assertEqual(body["error"]["field"], "credentials.server")
        self.assertEqual(self.backend.creds, {})
        self.assertNoSecret()

    def test_who_may_add(self):
        data = {"zone": "customer.example", "provider": "cloudflare", "credentials": CREDS}
        resp, body = self.request("POST", "/v1/zones", "acme", data)
        self.assertError(resp, body, 404, "not_found")
        resp, body = self.request("POST", "/v1/zones", "op_acme", data)
        self.assertError(resp, body, 403, "restricted_key")
        resp, body = self.request("POST", "/v1/zones", "operator_ro", data)
        self.assertError(resp, body, 403, "insufficient_scope")
        for path in ("/v1/zones/acme.test", "/v1/zones/provision"):
            method = "DELETE" if path.endswith("acme.test") else "POST"
            resp, body = self.request(method, path, "acme", {**data, "records": []})
            self.assertError(resp, body, 404, "not_found")
        self.assertEqual(self.backend.creds, {})

    def test_remove_a_hosted_zone(self):
        self.request("POST", "/v1/zones", "operator", {
            "zone": "customer.example", "provider": "cloudflare", "credentials": CREDS, "tenant": "t00000001"})
        self.backend.calls.clear()
        resp, body = self.request("DELETE", "/v1/zones/customer.example", "operator")
        self.assertEqual(resp.status, 204, body)
        self.assertEqual((self.backend.zones, self.backend.creds), ({}, {}))
        self.assertIn(("self", "unassign-zone", {"tenant": "t00000001", "zone": "customer.example"}),
                      self.backend.calls)
        self.assertNotIn("customer.example", self.api.store.tenant("t00000001")["zones"])
        resp, body = self.request("GET", "/v1/zones/customer.example/records", "acme")
        self.assertError(resp, body, 404, "zone_not_found")

    def test_only_zones_added_through_the_api_can_be_removed(self):
        for zone in ("acme.test", "nosuch.test", "x"):
            resp, body = self.request("DELETE", f"/v1/zones/{zone}", "operator")
            self.assertError(resp, body, 404, "zone_not_found")
        self.assertNotIn("remove-zone", self.actions())

    # new credentials for a hosted zone

    def hosted(self):
        resp, body = self.request("POST", "/v1/zones", "operator", {
            "zone": "customer.example", "provider": "cloudflare", "credentials": CREDS, "tenant": "t00000001"})
        self.assertEqual(resp.status, 201, body)
        self.backend.calls.clear()
        return self.backend.zones["customer.example"]

    def test_new_credentials_replace_the_old(self):
        old = self.hosted()
        resp, body = self.request("PATCH", "/v1/zones/customer.example", "operator",
                                  {"credentials": {"api_token": "rotated-token-0123"}})
        self.assertEqual(resp.status, 200, body)
        self.assertEqual((body["provider"], body["tenant"], body["dry_run"]), ("cloudflare", "t00000001", False))
        self.assertEqual(self.actions(), ["list-zones", "validate-zone", "list-zones", "add-credential",
                                          "update-zone", "remove-credential"])
        new = self.backend.zones["customer.example"]
        self.assertNotEqual(new, old)
        self.assertEqual(list(self.backend.creds), [new])
        self.assertEqual(self.journal(), {})
        self.assertIn("customer.example", self.api.store.tenant("t00000001")["zones"])
        entry = self.activity()[-1]
        self.assertEqual((entry["action"], entry["result"], entry["provider"]), ("update-zone", "ok", "cloudflare"))
        self.assertNotIn("rotated-token", json.dumps(self.activity()))
        # the tenant's key still reaches the zone
        resp, body = self.request("GET", "/v1/zones/customer.example/records", "acme")
        self.assertEqual(resp.status, 200, body)

    def test_another_dns_host(self):
        self.hosted()
        resp, body = self.request("PATCH", "/v1/zones/customer.example", "operator",
                                  {"provider": "rfc2136", "credentials": {"server": "ns.example"}})
        self.assertEqual(resp.status, 200, body)
        self.assertEqual(body["provider"], "rfc2136")
        self.assertEqual(list(self.backend.creds.values()), ["rfc2136"])

    def test_dry_run_and_bad_credentials_change_nothing(self):
        old = self.hosted()
        resp, body = self.request("PATCH", "/v1/zones/customer.example", "operator",
                                  {"credentials": {"api_token": "rotated"}, "dry_run": True})
        self.assertEqual((resp.status, body["valid"], body["dry_run"]), (200, True, True))
        resp, body = self.request("PATCH", "/v1/zones/customer.example", "operator",
                                  {"credentials": {"api_token": "bad"}})
        self.assertError(resp, body, 502, "auth_failed")
        self.assertEqual((self.backend.zones["customer.example"], list(self.backend.creds)), (old, [old]))
        self.assertNotIn("add-credential", self.actions())
        self.assertEqual([e["result"] for e in self.activity()[-2:]], ["dry-run", "failed:auth_failed"])

    def test_a_failed_switch_keeps_the_old_credential(self):
        old = self.hosted()
        self.backend.refuse["update-zone"] = refused("not_permitted")
        resp, body = self.request("PATCH", "/v1/zones/customer.example", "operator",
                                  {"credentials": {"api_token": "rotated"}})
        self.assertError(resp, body, 403, "not_permitted")
        self.assertEqual((self.backend.zones["customer.example"], list(self.backend.creds)), (old, [old]))
        self.assertEqual(self.journal(), {})

    def test_patch_refusals(self):
        self.hosted()
        for path, key, data, status, code in [
                ("/v1/zones/acme.test", "operator", {"credentials": CREDS}, 404, "zone_not_found"),
                ("/v1/zones/customer.example", "acme", {"credentials": CREDS}, 404, "not_found"),
                ("/v1/zones/customer.example", "op_acme", {"credentials": CREDS}, 403, "restricted_key"),
                ("/v1/zones/customer.example", "operator", {"tenant": "t00000002"}, 400, "not_editable"),
                ("/v1/zones/customer.example", "operator", {}, 400, "invalid_request"),
                ("/v1/zones/customer.example", "operator", {"credentials": {"nope": "x"}}, 400, "unknown_field")]:
            resp, body = self.request("PATCH", path, key, data)
            self.assertError(resp, body, status, code)
        self.assertNotIn("add-credential", self.actions())

    def test_a_concurrent_change_is_409(self):
        self.hosted()
        lock = self.api.zone_change_locks.setdefault("customer.example", __import__("threading").Lock())
        lock.acquire()
        try:
            resp, body = self.request("PATCH", "/v1/zones/customer.example", "operator", {"credentials": CREDS})
            self.assertError(resp, body, 409, "change_in_progress")
        finally:
            lock.release()

    def test_clean_up_after_a_stop_during_a_credential_change(self):
        """Whichever of the two credentials the zone does not use is removed; never a zone."""
        old = self.hosted()
        self.backend.creds["c000000ee"] = "cloudflare"
        # stopped before update-zone: the zone still uses the old one
        self.api.store.provisioning_set("before", {"zone": "customer.example", "kind": "credentials",
                                                   "credentials": ["c000000ee", old]})
        self.api.cleanup_provisioning()
        self.assertEqual((self.backend.zones, list(self.backend.creds), self.journal()),
                         ({"customer.example": old}, [old], {}))
        # stopped after update-zone: the zone uses the new one
        self.backend.creds["c000000ff"] = "cloudflare"
        self.backend.zones["customer.example"] = "c000000ff"
        self.api.store.provisioning_set("after", {"zone": "customer.example", "kind": "credentials",
                                                  "credentials": ["c000000ff", old]})
        self.api.cleanup_provisioning()
        self.assertEqual((self.backend.zones, list(self.backend.creds), self.journal()),
                         ({"customer.example": "c000000ff"}, ["c000000ff"], {}))

    # one-shot

    def provision(self, key="operator", **extra):
        data = {"zone": "mail-customer.example", "provider": "cloudflare", "credentials": CREDS,
                "records": [{"name": "@", "type": "TXT", "data": "v=spf1 include:mail.op.test -all"}], **extra}
        return self.request("POST", "/v1/zones/provision", key, data)

    def test_provision_writes_and_leaves_nothing(self):
        resp, body = self.provision()
        self.assertEqual(resp.status, 200, body)
        self.assertEqual(body["dry_run"], False)
        self.assertEqual(body["changes"]["add"][0]["data"], "v=spf1 include:mail.op.test -all")
        self.assertEqual(self.actions(), ["validate-zone", "add-credential", "add-zone", "list-owners",
                                          "append-records", "list-zones", "remove-zone", "remove-credential"])
        write = next(c[2] for c in self.backend.calls if c[1] == "append-records")
        self.assertEqual(write["on_behalf_of"], "operator:" + self.key_id("operator"))
        self.assertEqual((self.backend.zones, self.backend.creds, self.journal()), ({}, {}, {}))
        self.assertNoSecret()
        actions = [json.loads(line)["action"] for line in open(os.path.join(self.usage, "activity.jsonl"))]
        self.assertEqual(actions[-2:], ["append-records", "provision"])

    def test_provision_dry_run(self):
        resp, body = self.provision(dry_run=True)
        self.assertEqual(resp.status, 200, body)
        self.assertTrue(body["dry_run"])
        write = next(c[2] for c in self.backend.calls if c[1] == "append-records")
        self.assertTrue(write["dry_run"])
        self.assertEqual((self.backend.zones, self.backend.creds), ({}, {}))

    def test_provision_cleans_up_after_a_failed_write(self):
        self.backend.refuse["append-records"] = refused("conflict", "records", "a CNAME is there")
        resp, body = self.provision()
        self.assertError(resp, body, 409, "conflict")
        self.assertEqual((self.backend.zones, self.backend.creds, self.journal()), ({}, {}, {}))

    def test_provision_into_a_managed_zone_removes_only_its_own(self):
        resp, body = self.provision(zone="acme.test")
        self.assertError(resp, body, 409, "zone_already_configured")
        self.assertNotIn("remove-zone", self.actions())
        self.assertEqual((self.backend.creds, self.journal()), ({}, {}))

    def test_provision_checks_before_anything_is_stored(self):
        for extra, code in [({"records": []}, "invalid_request"),
                            ({"records": [{"name": "@", "type": "TXT"}]}, "invalid_request"),
                            ({"credentials": {"api_token": "bad"}}, "auth_failed")]:
            resp, body = self.provision(**extra)
            self.assertEqual(body["error"]["code"], code, extra)
        self.assertEqual(self.backend.creds, {})
        # the API's own host name is reserved here too
        resp, body = self.provision(zone="api.test", records=[{"name": "@", "type": "A", "data": "192.0.2.9"}])
        self.assertError(resp, body, 403, "reserved_name")
        self.assertEqual(self.backend.creds, {})

    def test_failed_clean_up_is_reported_and_retried(self):
        self.backend.refuse["remove-zone"] = TaskRefused([])
        resp, body = self.provision()
        self.assertError(resp, body, 502, "cleanup_failed")
        self.assertIn("records were written", body["error"]["message"])
        self.assertEqual(list(self.backend.zones), ["mail-customer.example"])
        entries = list(self.journal().values())
        self.assertEqual(entries[0]["zone"], "mail-customer.example")
        self.assertTrue(entries[0]["credential"])
        self.assertNotIn(TOKEN, json.dumps(entries))
        # the next clean-up removes what was left
        del self.backend.refuse["remove-zone"]
        self.api.cleanup_provisioning()
        self.assertEqual((self.backend.zones, self.backend.creds, self.journal()), ({}, {}, {}))

    def test_clean_up_after_a_crash(self):
        """A process that stopped after add-credential, with or without the zone."""
        self.backend.creds = {"c000000aa": "cloudflare", "c000000bb": "cloudflare", "c000000cc": "cloudflare"}
        self.backend.zones = {"crashed.example": "c000000aa", "kept.example": "c000000dd"}
        self.api.store.provisioning_set("e1", {"zone": "crashed.example", "credential": "c000000aa"})
        self.api.store.provisioning_set("e2", {"zone": "nozone.example", "credential": "c000000bb"})
        self.api.store.provisioning_set("e3", {"zone": "kept.example", "credential": None})
        self.api.store.provisioning_set("busy", {"zone": "busy.example", "credential": "c000000cc"})
        self.api.provisioning.add("busy")
        self.api.cleanup_provisioning()
        self.assertEqual(self.backend.zones, {"kept.example": "c000000dd"})
        self.assertEqual(self.backend.creds, {"c000000cc": "cloudflare"})
        self.assertEqual(list(self.journal()), ["busy"])

    def test_clean_up_waits_while_dnshelper_is_away(self):
        self.api.store.provisioning_set("e1", {"zone": "crashed.example", "credential": "c000000aa"})
        self.backend.fail_with = Unavailable("broker down")
        self.api.cleanup_provisioning()
        self.assertEqual(list(self.journal()), ["e1"])


def load_tests(loader, tests, pattern):
    """Only this file's tests: DomainTest inherits ApiTest's, which test_app.py runs."""
    return unittest.TestSuite(DomainTest(name) for name in sorted(vars(DomainTest)) if name.startswith("test_"))
