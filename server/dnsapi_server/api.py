#
# Copyright (C) 2026 Dan Brown
# SPDX-License-Identifier: GPL-3.0-or-later
#
# The v1 endpoints (DESIGN.md, API (v1)). Reads come from the state files
# and from dnshelper; changes to tenants, zone assignments and keys go
# through this module's own actions (its selfadm role), so the actions stay
# the only writers of the state.

import concurrent.futures
import ipaddress
import logging
import re
import threading
import time
from http import HTTPStatus

from . import keys as keyfmt
from .backend import TaskFailed, TaskRefused, TaskTimeout, Unavailable
from .store import isoformat, parse_time

log = logging.getLogger("dnsapi")

TENANT_ID_RE = re.compile(r"^t[0-9a-f]{8}$")
KEY_ID_RE = re.compile(r"^[0-9a-f]{8}$")
# A zone name as dnshelper accepts it (lowercase, at least one dot).
ZONE_RE = re.compile(r"^(?=.{3,253}$)([a-z0-9_]([a-z0-9_-]{0,61}[a-z0-9_])?\.)+[a-z0-9-]{2,63}$")
RECORD_TYPE_RE = re.compile(r"^[A-Za-z0-9]{1,10}$")
ZONES_CACHE_SECONDS = 30.0

# dnshelper and dnsapi error codes -> HTTP status (DESIGN.md: 400 validation,
# 403 permission, 404 unknown zone, 409 stale or conflict, 502 provider failure)
ERROR_STATUS = {
    "not_permitted": HTTPStatus.FORBIDDEN,
    "forbidden": HTTPStatus.FORBIDDEN,
    "zone_not_found": HTTPStatus.NOT_FOUND,
    "tenant_not_found": HTTPStatus.NOT_FOUND,
    "key_not_found": HTTPStatus.NOT_FOUND,
    "zone_not_assigned": HTTPStatus.NOT_FOUND,
    "conflict": HTTPStatus.CONFLICT,
    "stale": HTTPStatus.CONFLICT,
    "cnameconflict": HTTPStatus.CONFLICT,
    "zone_assigned": HTTPStatus.CONFLICT,
    "zone_not_assignable": HTTPStatus.CONFLICT,
    "auth_failed": HTTPStatus.BAD_GATEWAY,
}


class ApiError(Exception):
    """An error answered as {"error": {"code", "message", "field"}}."""

    def __init__(self, status, code, message, field=None, headers=None):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.field = field
        self.headers = headers or {}


class Principal:
    """The key a request was authenticated with."""

    def __init__(self, key_id, record, tenant):
        self.key_id = key_id
        self.owner = record["owner"]
        self.scope = record["scope"]
        self.tenant = tenant  # the tenant's record, or None for an operator key

    @property
    def is_operator(self):
        return self.owner == "operator"

    @property
    def label(self):
        """Who acts, for dnshelper's on_behalf_of and the audit lines."""
        return f"{self.owner}:{self.key_id}"


class Request:
    def __init__(self, method, path, query, body, client_ip):
        self.method = method
        self.path = path
        self.query = query
        self.body = body
        self.client_ip = client_ip
        self.principal = None
        self.params = {}


def client_address(peer, forwarded_for, proxies_depth):
    """The client's address as Traefik saw it (verified on a node, 2026-11-21).

    Traefik drops an X-Forwarded-For header that does not come from one of its
    trusted proxies and appends the address it was connected from, so the last
    entry is the peer of Traefik. With trusted proxies (ns8-traefik's
    set-trusted-proxies, PROXIES_DEPTH), the client is that many entries to
    the left. The header is used only on requests from Traefik on loopback.
    """
    try:
        if not ipaddress.ip_address(peer).is_loopback:
            return peer
    except ValueError:
        return peer
    chain = [part.strip() for value in forwarded_for for part in value.split(",") if part.strip()]
    if not chain:
        return peer
    index = max(0, len(chain) - 1 - max(0, proxies_depth))
    return chain[index]


def address_allowed(address, allowlist):
    if not allowlist:
        return True
    try:
        ip = ipaddress.ip_address(address)
    except ValueError:
        return False
    for entry in allowlist:
        try:
            if ip in ipaddress.ip_network(entry, strict=False):
                return True
        except ValueError:
            continue
    return False


class Api:
    def __init__(self, store, backend, limiter, failures, clock=time.monotonic,
                 max_failures=10, workers=8):
        self.store = store
        self.backend = backend
        self.limiter = limiter  # per key, dnshelper calls
        self.failures = failures  # per source address, failed authentications
        self.max_failures = max_failures
        self.clock = clock
        self.zones_cache = None  # (time, [zones])
        self.zones_lock = threading.Lock()
        self.pool = concurrent.futures.ThreadPoolExecutor(max_workers=workers)

    # authentication

    def authenticate(self, req, authorization):
        wait = self.failures.retry_after(req.client_ip, self.max_failures)
        if wait:
            raise ApiError(HTTPStatus.TOO_MANY_REQUESTS, "rate_limited",
                           "Too many failed authentications", headers={"Retry-After": str(wait)})
        if not authorization:
            raise self._unauthorized("missing_key", "An API key is required")
        scheme, _, key = authorization.partition(" ")
        key = key.strip()
        key_id = keyfmt.parse_key(key) if scheme.lower() == "bearer" else None
        record = self.store.keys().get(key_id) if key_id else None
        if record is None or not keyfmt.hash_matches(key, record.get("hash")):
            self.failures.hit(req.client_ip, 0)
            log.warning("authentication failed from %s (key id %s)", req.client_ip, key_id or "-")
            raise self._unauthorized("invalid_key", "The API key is not valid")
        expires = parse_time(record.get("expires"))
        if expires and expires <= self.store.clock():
            raise self._unauthorized("key_expired", "The API key has expired")
        tenant = None
        if record["owner"] != "operator":
            tenant = self.store.tenant(record["owner"])
            if tenant is None or not tenant.get("enabled", True):
                raise ApiError(HTTPStatus.FORBIDDEN, "tenant_disabled", "The key's tenant is disabled")
        if not address_allowed(req.client_ip, record.get("allowlist") or []):
            log.warning("key %s refused from %s: not in its allowlist", key_id, req.client_ip)
            raise ApiError(HTTPStatus.FORBIDDEN, "address_not_allowed",
                           "This key may not be used from this address")
        self.store.touch_key(key_id)
        req.principal = Principal(key_id, record, tenant)

    @staticmethod
    def _unauthorized(code, message):
        return ApiError(HTTPStatus.UNAUTHORIZED, code, message,
                        headers={"WWW-Authenticate": 'Bearer realm="dnsapi"'})

    # helpers

    def require_operator(self, req):
        if not req.principal.is_operator:
            # A tenant key does not learn that the operator endpoints exist.
            raise ApiError(HTTPStatus.NOT_FOUND, "not_found", "No such endpoint")

    def require_write(self, req):
        if req.principal.scope != "write":
            raise ApiError(HTTPStatus.FORBIDDEN, "insufficient_scope", "This key is read-only")

    def charge(self, req, calls=1):
        """Count dnshelper calls against the key's rate limit."""
        limit = int(self.store.settings().get("rate_limit", 60))
        for _ in range(calls):
            wait = self.limiter.hit(req.principal.key_id, limit)
            if wait:
                raise ApiError(HTTPStatus.TOO_MANY_REQUESTS, "rate_limited",
                               f"At most {limit} DNS requests per minute for this key",
                               headers={"Retry-After": str(wait)})

    def run_task(self, agent_id, action, data):
        try:
            return self.backend.run(agent_id, action, data)
        except TaskRefused as exc:
            first = exc.errors[0] if exc.errors else {}
            code = first.get("error") or "invalid_request"
            if not re.match(r"^[a-z_]{1,40}$", str(code)):
                code = "invalid_request"  # an NS8 schema message, not a code
            status = ERROR_STATUS.get(code, HTTPStatus.BAD_REQUEST)
            message = first.get("message") or str(first.get("error") or "The request was refused")
            raise ApiError(status, code, message, field=first.get("field") or None)
        except TaskTimeout as exc:
            log.error("%s", exc)
            raise ApiError(HTTPStatus.GATEWAY_TIMEOUT, "upstream_timeout",
                           "The DNS host did not answer in time")
        except TaskFailed:
            raise ApiError(HTTPStatus.BAD_GATEWAY, "upstream_error",
                           "The DNS host could not complete the request")
        except Unavailable as exc:
            log.error("%s", exc)
            raise ApiError(HTTPStatus.SERVICE_UNAVAILABLE, "unavailable",
                           "The DNS service is not available", headers={"Retry-After": "30"})

    def dnshelper(self, req, action, data):
        try:
            agent_id = self.backend.dnshelper_id()
        except Unavailable:
            raise ApiError(HTTPStatus.SERVICE_UNAVAILABLE, "dnshelper_missing",
                           "dnshelper is not installed", headers={"Retry-After": "300"})
        return self.run_task(agent_id, action, data)

    def own_action(self, action, data):
        output = self.run_task(self.backend.agent_id(), action, data)
        self.store.invalidate()
        return output

    def assignable_zones(self, req):
        """dnshelper's zones that dnsapi may write in full, cached for a short time."""
        with self.zones_lock:
            cached = self.zones_cache
            if cached and self.clock() - cached[0] < ZONES_CACHE_SECONDS:
                return cached[1]
        self.charge(req)
        output = self.dnshelper(req, "list-zones", {})
        zones = [z for z in output.get("zones", []) if z.get("full")]
        with self.zones_lock:
            self.zones_cache = (self.clock(), zones)
        return zones

    def zone_param(self, req):
        zone = req.params["zone"].lower().rstrip(".")
        if not ZONE_RE.match(zone):
            raise ApiError(HTTPStatus.NOT_FOUND, "zone_not_found", "No such zone")
        return zone

    def reachable_zone(self, req):
        """The zone in the path, if this key may use it; 404 otherwise (DESIGN.md: a
        tenant key must not learn which other zones are managed)."""
        zone = self.zone_param(req)
        principal = req.principal
        if not principal.is_operator and zone not in principal.tenant.get("zones", []):
            raise ApiError(HTTPStatus.NOT_FOUND, "zone_not_found", "No such zone")
        if zone not in {z["zone"] for z in self.assignable_zones(req)}:
            raise ApiError(HTTPStatus.NOT_FOUND, "zone_not_found", "No such zone")
        return zone

    # zones and records

    def list_zones(self, req):
        assigned = {}
        for tenant_id, tenant in self.store.tenants().items():
            for zone in tenant.get("zones", []):
                assigned[zone] = tenant_id
        result = []
        for z in self.assignable_zones(req):
            zone = z["zone"]
            if req.principal.is_operator:
                result.append({"zone": zone, "provider": z.get("provider"), "tenant": assigned.get(zone)})
            elif assigned.get(zone) == req.principal.owner:
                result.append({"zone": zone, "provider": z.get("provider")})
        return HTTPStatus.OK, {"zones": result}

    def get_records(self, req):
        zone = self.reachable_zone(req)
        data = {"zone": zone}
        for name in ("name", "type"):
            value = req.query.get(name)
            if value:
                data[name] = value
        if "type" in data and not RECORD_TYPE_RE.match(data["type"]):
            raise ApiError(HTTPStatus.BAD_REQUEST, "invalid_request", "Not a record type", field="type")
        self.charge(req, 2)
        records_f = self.pool.submit(self.dnshelper, req, "get-records", data)
        owners_f = self.pool.submit(self.dnshelper, req, "list-owners", {"zone": zone})
        records = records_f.result().get("records", [])
        try:
            owners = owners_f.result().get("owners", [])
        except ApiError as exc:
            # The records are what was asked for; the owners only add a warning.
            log.warning("list-owners for %s failed: %s", zone, exc.code)
            owners = []
        owned = {}
        for owner in owners:
            callers = [c.split("/", 1)[-1] for c in owner.get("callers", [])]
            if callers:
                owned[(owner["name"].lower(), owner["type"].upper(), owner["data"])] = callers
        for record in records:
            callers = owned.get((record["name"].lower(), record["type"].upper(), record["data"]))
            if callers:
                record["owned_by"] = callers
        return HTTPStatus.OK, {"zone": zone, "records": records}

    def get_propagation(self, req):
        zone = self.reachable_zone(req)
        name, rtype = req.query.get("name"), req.query.get("type")
        if not name:
            raise ApiError(HTTPStatus.BAD_REQUEST, "invalid_request", "name is required", field="name")
        if not rtype or not RECORD_TYPE_RE.match(rtype):
            raise ApiError(HTTPStatus.BAD_REQUEST, "invalid_request", "type is required", field="type")
        self.charge(req)
        output = self.dnshelper(req, "check-propagation", {"zone": zone, "name": name, "type": rtype})
        return HTTPStatus.OK, output

    # tenants (operator keys)

    def tenant_param(self, req):
        tenant_id = req.params["tenant"]
        if not TENANT_ID_RE.match(tenant_id) or self.store.tenant(tenant_id) is None:
            raise ApiError(HTTPStatus.NOT_FOUND, "tenant_not_found", "No such tenant")
        return tenant_id

    def tenant_view(self, tenant_id):
        tenant = self.store.tenant(tenant_id) or {}
        return {
            "id": tenant_id,
            "name": tenant.get("name", ""),
            "enabled": tenant.get("enabled", True),
            "zones": sorted(tenant.get("zones", [])),
            "created": tenant.get("created"),
        }

    def key_view(self, key_id, record):
        return {
            "id": key_id,
            "owner": record["owner"],
            "scope": record["scope"],
            "label": record.get("label", ""),
            "allowlist": record.get("allowlist") or [],
            "expires": record.get("expires"),
            "created": record.get("created"),
            "last_used": self.store.last_used.get(key_id),
        }

    def body_object(self, req):
        if not isinstance(req.body, dict):
            raise ApiError(HTTPStatus.BAD_REQUEST, "invalid_request", "A JSON object is required")
        return req.body

    def list_tenants(self, req):
        self.require_operator(req)
        return HTTPStatus.OK, {"tenants": [self.tenant_view(t) for t in sorted(self.store.tenants())]}

    def get_tenant(self, req):
        self.require_operator(req)
        return HTTPStatus.OK, self.tenant_view(self.tenant_param(req))

    def add_tenant(self, req):
        self.require_operator(req)
        self.require_write(req)
        body = self.body_object(req)
        data = {k: body[k] for k in ("name", "enabled") if k in body}
        output = self.own_action("add-tenant", data)
        self.audit(req, "add-tenant", tenant=output["id"])
        return HTTPStatus.CREATED, self.tenant_view(output["id"])

    def update_tenant(self, req):
        self.require_operator(req)
        self.require_write(req)
        tenant_id = self.tenant_param(req)
        body = self.body_object(req)
        data = {k: body[k] for k in ("name", "enabled") if k in body}
        self.own_action("update-tenant", {"id": tenant_id, **data})
        self.audit(req, "update-tenant", tenant=tenant_id)
        return HTTPStatus.OK, self.tenant_view(tenant_id)

    def remove_tenant(self, req):
        self.require_operator(req)
        self.require_write(req)
        tenant_id = self.tenant_param(req)
        self.own_action("remove-tenant", {"id": tenant_id})
        self.audit(req, "remove-tenant", tenant=tenant_id)
        return HTTPStatus.NO_CONTENT, None

    def assign_zone(self, req):
        self.require_operator(req)
        self.require_write(req)
        tenant_id = self.tenant_param(req)
        zone = self.zone_param(req)
        self.charge(req)
        self.own_action("assign-zone", {"tenant": tenant_id, "zone": zone})
        with self.zones_lock:
            self.zones_cache = None
        self.audit(req, "assign-zone", tenant=tenant_id, zone=zone)
        return HTTPStatus.OK, self.tenant_view(tenant_id)

    def unassign_zone(self, req):
        self.require_operator(req)
        self.require_write(req)
        tenant_id = self.tenant_param(req)
        zone = self.zone_param(req)
        self.own_action("unassign-zone", {"tenant": tenant_id, "zone": zone})
        self.audit(req, "unassign-zone", tenant=tenant_id, zone=zone)
        return HTTPStatus.NO_CONTENT, None

    def list_tenant_keys(self, req):
        self.require_operator(req)
        tenant_id = self.tenant_param(req)
        found = [self.key_view(k, r) for k, r in sorted(self.store.keys().items()) if r["owner"] == tenant_id]
        return HTTPStatus.OK, {"keys": found}

    def create_tenant_key(self, req):
        self.require_operator(req)
        self.require_write(req)
        tenant_id = self.tenant_param(req)
        body = self.body_object(req)
        # The secret is made here and never leaves this process except in the
        # response: the action gets its hash only.
        key_id, key, key_hash = keyfmt.new_key()
        data = {"id": key_id, "hash": key_hash, "owner": tenant_id}
        for name in ("scope", "label", "allowlist", "expires"):
            if name in body:
                data[name] = body[name]
        self.own_action("create-key", data)
        self.audit(req, "create-key", tenant=tenant_id, key=key_id)
        record = self.store.keys().get(key_id)
        view = self.key_view(key_id, record) if record else {"id": key_id}
        return HTTPStatus.CREATED, {**view, "key": key}

    def revoke_tenant_key(self, req):
        self.require_operator(req)
        self.require_write(req)
        tenant_id = self.tenant_param(req)
        key_id = req.params["key"]
        record = self.store.keys().get(key_id) if KEY_ID_RE.match(key_id) else None
        if record is None or record["owner"] != tenant_id:
            raise ApiError(HTTPStatus.NOT_FOUND, "key_not_found", "No such key")
        self.own_action("revoke-key", {"id": key_id})
        self.audit(req, "revoke-key", tenant=tenant_id, key=key_id)
        return HTTPStatus.NO_CONTENT, None

    def audit(self, req, action, **fields):
        details = " ".join(f'{k}="{v}"' for k, v in fields.items())
        log.info('dnsapi audit: key="%s" owner="%s" address="%s" action="%s" %s result="ok"',
                 req.principal.key_id, req.principal.owner, req.client_ip, action, details)


ZONE = r"(?P<zone>[^/]+)"
TENANT = r"(?P<tenant>[^/]+)"

# (pattern, {method: Api method name}); /v1/status is answered in app.py.
ROUTES = [
    (r"/v1/zones", {"GET": "list_zones"}),
    (rf"/v1/zones/{ZONE}/records", {"GET": "get_records"}),
    (rf"/v1/zones/{ZONE}/propagation", {"GET": "get_propagation"}),
    (r"/v1/tenants", {"GET": "list_tenants", "POST": "add_tenant"}),
    (rf"/v1/tenants/{TENANT}", {"GET": "get_tenant", "PATCH": "update_tenant", "DELETE": "remove_tenant"}),
    (rf"/v1/tenants/{TENANT}/zones/{ZONE}", {"PUT": "assign_zone", "DELETE": "unassign_zone"}),
    (rf"/v1/tenants/{TENANT}/keys", {"GET": "list_tenant_keys", "POST": "create_tenant_key"}),
    (rf"/v1/tenants/{TENANT}/keys/(?P<key>[^/]+)", {"DELETE": "revoke_tenant_key"}),
]
COMPILED = [(re.compile("^" + pattern + "$"), methods) for pattern, methods in ROUTES]


def match_route(path):
    for regex, methods in COMPILED:
        match = regex.match(path)
        if match:
            return methods, match.groupdict()
    return None, {}


__all__ = ["Api", "ApiError", "Request", "match_route", "client_address", "isoformat"]
