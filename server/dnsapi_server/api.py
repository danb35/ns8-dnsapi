#
# Copyright (C) 2026 Dan Brown
# SPDX-License-Identifier: GPL-3.0-or-later
#
# The v1 endpoints (DESIGN.md, API (v1)). Reads come from the state files
# and from dnshelper; changes to tenants, zone assignments and keys go
# through this module's own actions (its selfadm role), so the actions stay
# the only writers of the state.

import base64
import binascii
import concurrent.futures
import fnmatch
import ipaddress
import json
import logging
import re
import secrets
import threading
import time
from http import HTTPStatus

from . import keys as keyfmt
from .backend import DnshelperMissing, NotGranted, TaskFailed, TaskRefused, TaskTimeout, Unavailable
from .store import isoformat, parse_time

log = logging.getLogger("dnsapi")

TENANT_ID_RE = re.compile(r"^t[0-9a-f]{8}$")
KEY_ID_RE = re.compile(r"^[0-9a-f]{8}$")
# What PATCH may change on a key; the update-key action checks the values.
EDITABLE_KEY_FIELDS = ("label", "allowlist", "expires")
# A zone name as dnshelper accepts it (lowercase, at least one dot).
ZONE_RE = re.compile(r"^(?=.{3,253}$)([a-z0-9_]([a-z0-9_-]{0,61}[a-z0-9_])?\.)+[a-z0-9-]{2,63}$")
RECORD_TYPE_RE = re.compile(r"^[A-Za-z0-9]{1,10}$")
ZONES_CACHE_SECONDS = 30.0
# dnshelper's provider list is its built-in registry: it changes only when dnshelper is updated.
PROVIDERS_CACHE_SECONDS = 600.0
PROVIDER_KEYS = ("name", "label", "notes", "types", "fields")
PROVIDER_FIELD_KEYS = ("name", "label", "secret", "required", "default")
MAX_RECORDS = 100  # dnshelper's limit per change
MAX_CREDENTIAL_FIELD = 4096  # dnshelper's limit per credential field
RECORD_FIELDS = {"name", "type", "ttl", "data"}

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
    "zone_already_configured": HTTPStatus.CONFLICT,
    "zone_overlaps": HTTPStatus.CONFLICT,
    "auth_failed": HTTPStatus.BAD_GATEWAY,
}

# Concurrency limits (DESIGN.md, Security, Concurrency limits)
MAX_TASKS = 16           # NS8 tasks in progress at once, for the whole service
TASK_SLOT_WAIT = 10.0    # seconds a request waits for a task slot before 503 busy
MAX_PER_KEY = 4          # requests of one key in progress at once

ACME_LABEL = "_acme-challenge"
ACME_TTL = 60  # a provider with a higher minimum raises it
MAX_ACME_VALUE = 255


def restrict_covers(restrict, name, rtype):
    """Does a key's restrict allow the record (name, rtype)? rtype None means
    any type. The same matching as dnshelper's rules (dnshelper_lib._covers)."""
    if not restrict:
        return True
    n = name.strip().lower().rstrip(".") or "@"
    if not any(fnmatch.fnmatchcase(n, p) for p in restrict.get("names") or ["*"]):
        return False
    types = restrict.get("types") or ["*"]
    if "*" in types:
        return True
    return rtype is not None and rtype.upper() in types


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
        self.restrict = record.get("restrict")  # None: every record of its zones
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


def throttle_key(address):
    """What failed authentications are counted by: an IPv4 address, or an IPv6 /64, since
    one IPv6 host usually has a whole /64 to rotate through (DESIGN.md, Security)."""
    try:
        ip = ipaddress.ip_address(address)
    except ValueError:
        return address
    if ip.version == 6:
        if ip.ipv4_mapped:
            return str(ip.ipv4_mapped)
        return str(ipaddress.ip_network(f"{ip}/64", strict=False))
    return str(ip)


def key_from_authorization(authorization, path):
    """The key an Authorization header carries, or "": Bearer anywhere, and Basic on
    /v1/acme/, where lego's httpreq, acme.sh's acmeproxy and Caddy's acmeproxy send the
    key as the password (the user name is not used)."""
    scheme, _, value = (authorization or "").partition(" ")
    scheme = scheme.lower()
    value = value.strip()
    if scheme == "bearer":
        return value
    if scheme == "basic" and path.startswith("/v1/acme/"):
        try:
            return base64.b64decode(value, validate=True).decode().partition(":")[2]
        except (binascii.Error, UnicodeDecodeError):
            return ""
    return ""


def key_status(record, now):
    """"revoked", "expired" or "active"."""
    if record.get("revoked"):
        return "revoked"
    expires = parse_time(record.get("expires"))
    if expires and expires <= now:
        return "expired"
    return "active"


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
        self.providers_cache = None  # (time, [providers])
        self.task_slots = threading.BoundedSemaphore(MAX_TASKS)
        self.in_flight = {}  # key id -> requests in progress
        self.in_flight_lock = threading.Lock()
        self.zones_lock = threading.Lock()
        self.pool = concurrent.futures.ThreadPoolExecutor(max_workers=workers)
        self.provisioning = set()  # ids of one-shot entries a request of this process is working on
        self.provisioning_lock = threading.Lock()
        self.zone_change_locks = {}  # zone -> lock: one credential change of a zone at a time

    # authentication

    def authenticate(self, req, authorization):
        source = throttle_key(req.client_ip)
        wait = self.failures.retry_after(source, self.max_failures)
        if wait:
            raise ApiError(HTTPStatus.TOO_MANY_REQUESTS, "rate_limited",
                           "Too many failed authentications", headers={"Retry-After": str(wait)})
        if not authorization:
            raise self._unauthorized("missing_key", "An API key is required")
        key = key_from_authorization(authorization, req.path)
        key_id = keyfmt.parse_key(key) if key else None
        record = self.store.keys().get(key_id) if key_id else None
        if record is None or not keyfmt.hash_matches(key, record.get("hash")):
            self.failures.hit(source, 0)
            log.warning("authentication failed from %s (key id %s)", req.client_ip, key_id or "-")
            raise self._unauthorized("invalid_key", "The API key is not valid")
        if record.get("revoked"):
            # The whole key matched, so only its holder learns that it was revoked.
            log.warning("revoked key %s refused from %s", key_id, req.client_ip)
            raise self._unauthorized("key_revoked", "The API key has been revoked")
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

    def cleartext_key(self, authorization, path, address):
        """A request came over plain HTTP (refused by the caller with https_required). If it
        carried a valid key, that key crossed the network in the clear: revoke it when
        revoke_cleartext_keys is on (the default), else log it. A key-shaped string that does
        not match its stored hash is only logged, so that nobody can get a key revoked by
        knowing its id, which is not secret (DESIGN.md, Security, HTTPS only). Never raises:
        the answer is the same 403 whatever happens here."""
        key = key_from_authorization(authorization, path)
        key_id = keyfmt.parse_key(key) if key else None
        if not key_id:
            return
        record = self.store.keys().get(key_id)
        if record is None or not keyfmt.hash_matches(key, record.get("hash")):
            log.warning("a key-shaped string with id %s that is not a valid key was sent over plain HTTP from %s",
                        key_id, address)
            return
        if record.get("revoked"):
            log.warning("revoked key %s was sent over plain HTTP from %s", key_id, address)
            return
        if not self.store.settings().get("revoke_cleartext_keys", True):
            log.warning("key %s was sent over plain HTTP from %s: revoke it if the network may be watched",
                        key_id, address)
            return
        try:
            self.own_action("revoke-exposed-key", {"id": key_id, "address": address})
            result = "ok"
        except ApiError as exc:
            log.error("key %s was sent over plain HTTP from %s and could not be revoked: %s",
                      key_id, address, exc.message)
            result = f"failed:{exc.code}"
        except Exception:
            log.exception("key %s was sent over plain HTTP from %s and could not be revoked", key_id, address)
            result = "failed"
        owner = record.get("owner", "")
        tenant = owner if owner != "operator" else ""
        log.info('dnsapi audit: key="%s" owner="%s" address="%s" action="revoke-exposed-key" '
                 'reason="plain_http" result="%s"', key_id, owner, address, result)
        self.store.append_activity({
            "source": "api", "key": key_id, "owner": owner, "tenant": tenant, "address": address,
            "action": "revoke-exposed-key", "target_key": key_id, "reason": "plain_http",
            "result": result,
        })

    def enter(self, req):
        """Count a request of the key in progress; refuse beyond MAX_PER_KEY."""
        key_id = req.principal.key_id
        with self.in_flight_lock:
            if self.in_flight.get(key_id, 0) >= MAX_PER_KEY:
                raise ApiError(HTTPStatus.TOO_MANY_REQUESTS, "too_many_concurrent",
                               f"At most {MAX_PER_KEY} requests of this key at once",
                               headers={"Retry-After": "5"})
            self.in_flight[key_id] = self.in_flight.get(key_id, 0) + 1

    def leave(self, req):
        if req.principal is None:
            return
        key_id = req.principal.key_id
        with self.in_flight_lock:
            count = self.in_flight.get(key_id, 0) - 1
            if count > 0:
                self.in_flight[key_id] = count
            else:
                self.in_flight.pop(key_id, None)

    @staticmethod
    def _unauthorized(code, message):
        return ApiError(HTTPStatus.UNAUTHORIZED, code, message,
                        headers={"WWW-Authenticate": 'Bearer realm="dnsapi"'})

    # helpers

    def require_operator(self, req):
        if not req.principal.is_operator:
            # A tenant key does not learn that the operator endpoints exist.
            raise ApiError(HTTPStatus.NOT_FOUND, "not_found", "No such endpoint")
        if req.principal.restrict:
            raise ApiError(HTTPStatus.FORBIDDEN, "restricted_key",
                           "A key limited to some records cannot manage tenants and keys")

    def reserved_names(self, zone):
        """Names in `zone`, relative to it, that no key may change: the API's own host name
        and its _acme-challenge (DESIGN.md, The API host name in DNS). Otherwise a key of a
        tenant holding that zone could point the API elsewhere, or get a certificate for it."""
        host = (self.store.settings().get("host") or "").lower().rstrip(".")
        if not host or not (host == zone or host.endswith("." + zone)):
            return set()
        name = "@" if host == zone else host[: -len(zone) - 1]
        acme = ACME_LABEL if name == "@" else f"{ACME_LABEL}.{name}"
        return {name, acme}

    def require_not_reserved(self, zone, records, field):
        reserved = self.reserved_names(zone)
        if not reserved:
            return
        for index, record in enumerate(records):
            name = record["name"].strip().lower().rstrip(".") or "@"
            if name in reserved:
                raise ApiError(HTTPStatus.FORBIDDEN, "reserved_name",
                               f"{record['name']} belongs to the API's own host name and cannot be changed through the API",
                               field=f"{field}[{index}]")

    def require_covered(self, req, records, field):
        """Refuse a request with any record outside the key's restrict."""
        restrict = req.principal.restrict
        for index, record in enumerate(records):
            if not restrict_covers(restrict, record["name"], record.get("type")):
                what = f"{record['name']} {record.get('type') or '(any type)'}"
                raise ApiError(HTTPStatus.FORBIDDEN, "outside_restriction",
                               f"This key may not change {what}", field=f"{field}[{index}]")

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

    def run_task(self, target, action, data):
        if not self.task_slots.acquire(timeout=TASK_SLOT_WAIT):
            raise ApiError(HTTPStatus.SERVICE_UNAVAILABLE, "busy", "The service is busy; try again",
                           headers={"Retry-After": "10"})
        try:
            return self.backend.run(target, action, data)
        except DnshelperMissing:
            raise ApiError(HTTPStatus.SERVICE_UNAVAILABLE, "dnshelper_missing",
                           "dnshelper is not installed", headers={"Retry-After": "300"})
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
        except NotGranted as exc:
            log.error("%s", exc)
            raise ApiError(HTTPStatus.SERVICE_UNAVAILABLE, "not_granted",
                           f"dnshelper does not let this module run {action}; dnshelper may need updating",
                           headers={"Retry-After": "300"})
        except Unavailable as exc:
            log.error("%s", exc)
            raise ApiError(HTTPStatus.SERVICE_UNAVAILABLE, "unavailable",
                           "The DNS service is not available", headers={"Retry-After": "30"})
        finally:
            self.task_slots.release()

    def dnshelper(self, req, action, data):
        return self.run_task("dnshelper", action, data)

    def own_action(self, action, data):
        output = self.run_task("self", action, data)
        self.store.invalidate()
        return output

    def assignable_zones(self, req):
        """dnshelper's zones that dnsapi may write in, cached for a short time: in full
        (a hosting customer's zone) or only some records (DESIGN.md, ACME DNS-01
        validation). dnshelper's rule stays the outer limit for each."""
        with self.zones_lock:
            cached = self.zones_cache
            if cached and self.clock() - cached[0] < ZONES_CACHE_SECONDS:
                return cached[1]
        self.charge(req)
        output = self.dnshelper(req, "list-zones", {})
        zones = [z for z in output.get("zones", []) if z.get("access") == "write"]
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
                result.append({"zone": zone, "provider": z.get("provider"), "full": bool(z.get("full")),
                               "tenant": assigned.get(zone), "hosted": bool(z.get("delegated"))})
            elif assigned.get(zone) == req.principal.owner:
                result.append({"zone": zone, "provider": z.get("provider"), "full": bool(z.get("full"))})
        return HTTPStatus.OK, {"zones": result}

    def list_providers(self, req):
        """The DNS hosts dnshelper supports and the credential fields each one takes
        (DESIGN.md, Providers). The same for every caller and nothing about the
        administrator's credentials, but only operator keys need it."""
        if not req.principal.is_operator:
            raise ApiError(HTTPStatus.NOT_FOUND, "not_found", "No such endpoint")
        return HTTPStatus.OK, {"providers": self.providers(req)}

    def providers(self, req):
        with self.zones_lock:
            cached = self.providers_cache
            if cached and self.clock() - cached[0] < PROVIDERS_CACHE_SECONDS:
                return cached[1]
        self.charge(req)
        output = self.dnshelper(req, "list-providers", {})
        providers = []
        for p in output.get("providers", []):
            # Only the fields documented in openapi.json: a later dnshelper may add more.
            item = {k: p[k] for k in PROVIDER_KEYS if k in p and k != "fields"}
            item["fields"] = [{k: f[k] for k in PROVIDER_FIELD_KEYS if k in f} for f in p.get("fields", [])]
            providers.append(item)
        with self.zones_lock:
            self.providers_cache = (self.clock(), providers)
        return providers

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
        records = [r for r in records_f.result().get("records", [])
                   if restrict_covers(req.principal.restrict, r["name"], r["type"])]
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
        if not restrict_covers(req.principal.restrict, name, rtype):
            raise ApiError(HTTPStatus.FORBIDDEN, "outside_restriction", f"This key may not read {name} {rtype}")
        self.charge(req)
        output = self.dnshelper(req, "check-propagation", {"zone": zone, "name": name, "type": rtype})
        return HTTPStatus.OK, output

    # record changes (write keys)

    def records_param(self, body, field, required_keys, max_items=MAX_RECORDS, allow_empty=False):
        """A list of records from the request body, with only the fields dnshelper takes."""
        records = body.get(field, [] if allow_empty else None)
        if not isinstance(records, list) or (not records and not allow_empty):
            raise ApiError(HTTPStatus.BAD_REQUEST, "invalid_request",
                           f"{field} must be a non-empty list of records", field=field)
        if len(records) > max_items:
            raise ApiError(HTTPStatus.BAD_REQUEST, "invalid_request",
                           f"At most {max_items} records per request", field=field)
        clean = []
        for index, record in enumerate(records):
            where = f"{field}[{index}]"
            if not isinstance(record, dict):
                raise ApiError(HTTPStatus.BAD_REQUEST, "invalid_request", "A record is an object", field=where)
            unknown = set(record) - RECORD_FIELDS
            if unknown:
                raise ApiError(HTTPStatus.BAD_REQUEST, "invalid_request",
                               f"Unknown field {sorted(unknown)[0]}", field=where)
            for key in required_keys:
                if key not in record:
                    raise ApiError(HTTPStatus.BAD_REQUEST, "invalid_request", f"{key} is required",
                                   field=f"{where}.{key}")
            for key in ("name", "type", "data"):
                if key in record and not isinstance(record[key], str):
                    raise ApiError(HTTPStatus.BAD_REQUEST, "invalid_request", f"{key} is a string",
                                   field=f"{where}.{key}")
            if "name" in record and not record["name"]:
                raise ApiError(HTTPStatus.BAD_REQUEST, "invalid_request", "name is empty", field=f"{where}.name")
            if "type" in record and not RECORD_TYPE_RE.match(record["type"]):
                raise ApiError(HTTPStatus.BAD_REQUEST, "invalid_request", "Not a record type", field=f"{where}.type")
            if "ttl" in record and (not isinstance(record["ttl"], int) or isinstance(record["ttl"], bool)
                                    or record["ttl"] < 0):
                raise ApiError(HTTPStatus.BAD_REQUEST, "invalid_request", "ttl is a whole number of seconds",
                               field=f"{where}.ttl")
            clean.append({k: record[k] for k in ("name", "type", "ttl", "data") if k in record})
        return clean

    def change(self, req, action, data, zone=None, dry_run=None):
        """Run a dnshelper write and answer with its changes, plus a warning for each
        record it removes that another module wrote (DESIGN.md, Security, Records
        written by other modules)."""
        self.require_write(req)
        for field in ("add", "remove", "records"):
            self.require_covered(req, data.get(field, []), field)
        zone = zone or self.reachable_zone(req)
        for field in ("add", "remove", "records"):
            self.require_not_reserved(zone, data.get(field, []), field)
        if dry_run is None:
            dry_run = req.body.get("dry_run", False)
        if not isinstance(dry_run, bool):
            raise ApiError(HTTPStatus.BAD_REQUEST, "invalid_request", "dry_run is true or false", field="dry_run")
        tenant = req.principal.owner if not req.principal.is_operator else self.store.zone_tenant(zone)
        data = {"zone": zone, **data, "dry_run": dry_run,
                # dnshelper records it in its audit line and the zone's history,
                # and records no owner for what a tenant writes.
                "on_behalf_of": f"{tenant or 'operator'}:{req.principal.key_id}"}
        self.charge(req, 2)
        # Before the write: dnshelper forgets a record's owner when it is removed.
        try:
            owners = self.dnshelper(req, "list-owners", {"zone": zone}).get("owners", [])
        except ApiError as exc:
            log.warning("list-owners for %s failed: %s", zone, exc.code)
            owners = []
        outcome = "failed"
        output = {}
        try:
            output = self.dnshelper(req, action, data)
            outcome = "dry-run" if dry_run else "ok"
        except ApiError as exc:
            outcome = "rejected" if exc.status < 500 else "failed"
            self.change_audit(req, action, zone, tenant, data, None, f"{outcome}:{exc.code}")
            raise
        changes = output.get("changes") or {"add": [], "remove": []}
        self.change_audit(req, action, zone, tenant, data, changes, outcome)
        owned = {}
        for owner in owners:
            callers = [c.split("/", 1)[-1] for c in owner.get("callers", [])]
            if callers:
                owned[(owner["name"].lower(), owner["type"].upper(), owner["data"])] = callers
        warnings = []
        for record in changes.get("remove", []):
            modules = owned.get((record["name"].lower(), record["type"].upper(), record["data"]))
            if modules:
                warnings.append({
                    "code": "owned_by_module",
                    "record": record,
                    "modules": modules,
                    "message": f"{', '.join(modules)} wrote this record and may write it again",
                })
        return HTTPStatus.OK, {
            "zone": zone,
            "dry_run": output.get("dry_run", dry_run),
            "changes": changes,
            "warnings": warnings,
            "records": output.get("records", []),
        }

    def change_audit(self, req, action, zone, tenant, data, changes, outcome):
        def show(records):
            return json.dumps([f"{r['name']} {r.get('type', '*')} {r.get('data', '*')}" for r in records])

        if changes is None:
            added, removed = data.get("add", data.get("records", [])), data.get("remove", [])
            if action == "delete-records":
                added, removed = [], data.get("records", [])
        else:
            added, removed = changes.get("add", []), changes.get("remove", [])
        log.info('dnsapi audit: key="%s" tenant="%s" address="%s" action="%s" zone="%s" add=%s remove=%s '
                 'result="%s"', req.principal.key_id, tenant or "", req.client_ip, action, zone,
                 show(added), show(removed), outcome)
        self.store.append_activity({
            "source": "api", "key": req.principal.key_id, "owner": req.principal.owner,
            "tenant": tenant, "address": req.client_ip, "action": action, "zone": zone,
            "add": json.loads(show(added)), "remove": json.loads(show(removed)), "result": outcome,
        })

    def apply_changes(self, req):
        self.require_write(req)
        body = self.body_object(req)
        add = self.records_param(body, "add", ("name", "type", "data"), allow_empty=True)
        remove = self.records_param(body, "remove", ("name", "type", "data"), allow_empty=True)
        if not add and not remove:
            raise ApiError(HTTPStatus.BAD_REQUEST, "invalid_request", "Nothing to add or remove")
        if len(add) + len(remove) > MAX_RECORDS:
            raise ApiError(HTTPStatus.BAD_REQUEST, "invalid_request", f"At most {MAX_RECORDS} records per change")
        data = {}
        if add:
            data["add"] = add
        if remove:
            data["remove"] = remove
        return self.change(req, "apply-changes", data)

    def append_records(self, req):
        self.require_write(req)
        body = self.body_object(req)
        return self.change(req, "append-records",
                           {"records": self.records_param(body, "records", ("name", "type", "data"))})

    def set_rrsets(self, req):
        self.require_write(req)
        body = self.body_object(req)
        return self.change(req, "set-records",
                           {"records": self.records_param(body, "records", ("name", "type", "data")),
                            "mode": "rrset"})

    def delete_records(self, req):
        self.require_write(req)
        body = self.body_object(req)
        return self.change(req, "delete-records", {"records": self.records_param(body, "records", ("name",))})

    # ACME DNS-01 (lego's httpreq provider, acme.sh's acmeproxy)

    def acme_request(self, req):
        """The zone and the name relative to it for {"fqdn", "value"}."""
        self.require_write(req)
        body = self.body_object(req)
        fqdn, value = body.get("fqdn"), body.get("value")
        if not isinstance(fqdn, str) or not fqdn.strip():
            raise ApiError(HTTPStatus.BAD_REQUEST, "invalid_request", "fqdn is required", field="fqdn")
        if not isinstance(value, str) or not value or len(value) > MAX_ACME_VALUE:
            raise ApiError(HTTPStatus.BAD_REQUEST, "invalid_request", "value is required", field="value")
        host = fqdn.strip().lower().rstrip(".")
        if host.split(".", 1)[0] != ACME_LABEL or "." not in host:
            raise ApiError(HTTPStatus.BAD_REQUEST, "invalid_request",
                           f"fqdn must start with {ACME_LABEL}.", field="fqdn")
        principal = req.principal
        candidates = [z["zone"] for z in self.assignable_zones(req)]
        if not principal.is_operator:
            candidates = [z for z in candidates if z in principal.tenant.get("zones", [])]
        matching = [z for z in candidates if host == z or host.endswith("." + z)]
        if not matching:
            raise ApiError(HTTPStatus.NOT_FOUND, "zone_not_found", "No zone of this key contains fqdn",
                           field="fqdn")
        zone = max(matching, key=len)
        name = host[: -len(zone) - 1] if host != zone else "@"
        return fqdn, value, zone, name

    def acme_present(self, req):
        fqdn, value, zone, name = self.acme_request(req)
        record = {"name": name, "type": "TXT", "ttl": ACME_TTL, "data": value}
        status, result = self.change(req, "append-records", {"records": [record]}, zone=zone, dry_run=False)
        # acme.sh's acmeproxy counts the call as done when the reply contains the value.
        return status, {"fqdn": fqdn, "value": value, "zone": zone, "changes": result["changes"]}

    def acme_cleanup(self, req):
        fqdn, value, zone, name = self.acme_request(req)
        record = {"name": name, "type": "TXT", "data": value}
        status, result = self.change(req, "delete-records", {"records": [record]}, zone=zone, dry_run=False)
        return status, {"fqdn": fqdn, "value": value, "zone": zone, "changes": result["changes"]}

    # domains added through the API (DESIGN.md, Phase 2): dnsapi is one of dnshelper's
    # delegates, and adds the zone and its credential itself

    def forget_zones(self):
        with self.zones_lock:
            self.zones_cache = None

    def zone_body(self, body):
        zone = body.get("zone")
        if not isinstance(zone, str) or not ZONE_RE.match(zone.strip().lower().rstrip(".")):
            raise ApiError(HTTPStatus.BAD_REQUEST, "invalid_zone", "zone is a domain name like example.com",
                           field="zone")
        return zone.strip().lower().rstrip(".")

    def credentials_param(self, req, body, default_provider=None):
        """The DNS host and the credential fields for it, checked against dnshelper's
        provider list: known names only, and the required ones present (dnshelper
        checks them again). The values are passed on, never kept or logged."""
        provider = body.get("provider", default_provider)
        if not isinstance(provider, str) or not provider:
            raise ApiError(HTTPStatus.BAD_REQUEST, "invalid_request", "provider is required", field="provider")
        info = next((p for p in self.providers(req) if p.get("name") == provider), None)
        if info is None:
            raise ApiError(HTTPStatus.BAD_REQUEST, "unknown_provider",
                           "Not a DNS host dnshelper supports: see GET /v1/providers", field="provider")
        fields = body.get("credentials")
        if not isinstance(fields, dict):
            raise ApiError(HTTPStatus.BAD_REQUEST, "invalid_request", "credentials is an object",
                           field="credentials")
        known = {f["name"]: f for f in info.get("fields", [])}
        for name, value in fields.items():
            if name not in known:
                raise ApiError(HTTPStatus.BAD_REQUEST, "unknown_field", f"{provider} takes no field {name}",
                               field=f"credentials.{name}")
            if not isinstance(value, str) or len(value) > MAX_CREDENTIAL_FIELD:
                raise ApiError(HTTPStatus.BAD_REQUEST, "invalid_request",
                               f"{name} is a string of at most {MAX_CREDENTIAL_FIELD} characters",
                               field=f"credentials.{name}")
        for name, f in known.items():
            if f.get("required") and not fields.get(name) and not f.get("default"):
                raise ApiError(HTTPStatus.BAD_REQUEST, "required", f"{name} is required",
                               field=f"credentials.{name}")
        return provider, {k: v for k, v in fields.items() if v != ""}

    def dry_run_param(self, body):
        dry_run = body.get("dry_run", False)
        if not isinstance(dry_run, bool):
            raise ApiError(HTTPStatus.BAD_REQUEST, "invalid_request", "dry_run is true or false", field="dry_run")
        return dry_run

    def validate_credentials(self, req, zone, provider, fields):
        """That the credential reaches the zone at the DNS host, before anything is stored."""
        self.charge(req)
        self.dnshelper(req, "validate-zone", {"zone": zone, "provider": provider, "fields": fields})

    def add_delegated(self, req, zone, provider, fields, name):
        """Add a credential of dnsapi's own and the zone with it. Returns the credential
        id. If the zone cannot be added, the credential is removed again."""
        self.charge(req, 2)
        cred = self.dnshelper(req, "add-credential", {"name": name, "provider": provider, "fields": fields})["id"]
        try:
            self.dnshelper(req, "add-zone", {"zone": zone, "credential": cred})
        except ApiError:
            self.quietly("remove-credential", {"id": cred})
            raise
        finally:
            self.forget_zones()
        return cred

    def quietly(self, action, data):
        """A clean-up step: True if it worked, logged if not."""
        try:
            self.run_task("dnshelper", action, data)
            return True
        except ApiError as exc:
            log.error("%s %s failed: %s", action, json.dumps(data), exc.code)
            return False

    def hosted_entry(self, req, zone):
        """dnshelper's entry for a zone dnsapi added, read afresh, or None."""
        self.charge(req)
        zones = self.dnshelper(req, "list-zones", {}).get("zones", [])
        return next((z for z in zones if z.get("zone") == zone and z.get("delegated")), None)

    def add_hosted_zone(self, req):
        """POST /v1/zones: a customer's domain with its DNS host and credentials, kept
        so that its records can be managed through the API (DESIGN.md, Phase 2, Hosting)."""
        self.require_operator(req)
        self.require_write(req)
        body = self.body_object(req)
        zone = self.zone_body(body)
        provider, fields = self.credentials_param(req, body)
        tenant_id = body.get("tenant")
        if tenant_id is not None and (not isinstance(tenant_id, str) or not TENANT_ID_RE.match(tenant_id)
                                      or self.store.tenant(tenant_id) is None):
            raise ApiError(HTTPStatus.NOT_FOUND, "tenant_not_found", "No such tenant", field="tenant")
        dry_run = self.dry_run_param(body)
        audit = {"zone": zone, "provider": provider, "tenant": tenant_id or ""}
        try:
            self.validate_credentials(req, zone, provider, fields)
            if dry_run:
                self.audit(req, "add-zone", dry_run=True, **audit)
                return HTTPStatus.OK, {"zone": zone, "provider": provider, "tenant": tenant_id,
                                       "dry_run": True, "valid": True}
            cred = self.add_delegated(req, zone, provider, fields, f"dnsapi: {zone}")
            if tenant_id:
                try:
                    self.charge(req)
                    self.own_action("assign-zone", {"tenant": tenant_id, "zone": zone})
                except ApiError:
                    self.quietly("remove-zone", {"zone": zone})
                    self.quietly("remove-credential", {"id": cred})
                    self.forget_zones()
                    raise
        except ApiError as exc:
            self.audit(req, "add-zone", result=f"rejected:{exc.code}" if exc.status < 500 else f"failed:{exc.code}",
                       **audit)
            raise
        self.audit(req, "add-zone", **audit)
        return HTTPStatus.CREATED, {"zone": zone, "provider": provider, "tenant": tenant_id, "full": True,
                                    "hosted": True, "dry_run": False}

    def remove_hosted_zone(self, req):
        """DELETE /v1/zones/{zone}: a zone dnsapi added. dnshelper forgets it and its
        credential; the records stay at the DNS host."""
        self.require_operator(req)
        self.require_write(req)
        zone = self.zone_param(req)
        entry = self.hosted_entry(req, zone)
        if entry is None:
            # Not added through the API, or taken over by the administrator since.
            raise ApiError(HTTPStatus.NOT_FOUND, "zone_not_found", "No zone added through the API by that name")
        tenant_id = self.store.zone_tenant(zone)
        if tenant_id:
            self.own_action("unassign-zone", {"tenant": tenant_id, "zone": zone})
        self.charge(req, 2)
        try:
            self.dnshelper(req, "remove-zone", {"zone": zone})
        finally:
            self.forget_zones()
        if not self.quietly("remove-credential", {"id": entry["credential"]}):
            log.warning("the credential %s of %s was left in dnshelper", entry["credential"], zone)
        self.audit(req, "remove-zone", zone=zone, provider=entry.get("provider") or "", tenant=tenant_id or "")
        return HTTPStatus.NO_CONTENT, None

    def update_hosted_zone(self, req):
        """PATCH /v1/zones/{zone}: new credentials for a zone dnsapi added, for example when
        the customer's token expires or is rotated, or the domain moves to another DNS host
        (DESIGN.md, Phase 2, Changing a hosted domain's credentials). The whole set of
        fields is given: dnsapi cannot read the stored secrets to merge them. The new
        credentials are checked at the DNS host first, added as a new credential, the zone
        is pointed at it (dnshelper's update-zone), and the old one is removed."""
        self.require_operator(req)
        self.require_write(req)
        zone = self.zone_param(req)
        body = self.body_object(req)
        unknown = set(body) - {"provider", "credentials", "dry_run"}
        if unknown:
            name = sorted(unknown)[0]
            raise ApiError(HTTPStatus.BAD_REQUEST, "not_editable", f"{name} cannot be changed here", field=name)
        if "credentials" not in body:
            raise ApiError(HTTPStatus.BAD_REQUEST, "invalid_request", "credentials is required", field="credentials")
        entry = self.hosted_entry(req, zone)
        if entry is None:
            raise ApiError(HTTPStatus.NOT_FOUND, "zone_not_found", "No zone added through the API by that name")
        provider, fields = self.credentials_param(req, body, entry.get("provider"))
        dry_run = self.dry_run_param(body)
        tenant_id = self.store.zone_tenant(zone)
        audit = {"zone": zone, "provider": provider, "tenant": tenant_id or ""}
        try:
            self.validate_credentials(req, zone, provider, fields)
        except ApiError as exc:
            self.audit(req, "update-zone", result=f"{'rejected' if exc.status < 500 else 'failed'}:{exc.code}",
                       **audit)
            raise
        if dry_run:
            self.audit(req, "update-zone", result="dry-run", **audit)
            return HTTPStatus.OK, {"zone": zone, "provider": provider, "tenant": tenant_id, "dry_run": True,
                                   "valid": True}
        with self.provisioning_lock:
            lock = self.zone_change_locks.setdefault(zone, threading.Lock())
        if not lock.acquire(blocking=False):
            raise ApiError(HTTPStatus.CONFLICT, "change_in_progress",
                           "The credentials of this zone are being changed by another request")
        try:
            return self.replace_credentials(req, zone, provider, fields, tenant_id, audit)
        finally:
            lock.release()

    def replace_credentials(self, req, zone, provider, fields, tenant_id, audit):
        # read again under the lock: another request may have replaced it meanwhile
        entry = self.hosted_entry(req, zone)
        if entry is None:
            raise ApiError(HTTPStatus.NOT_FOUND, "zone_not_found", "No zone added through the API by that name")
        old = entry["credential"]
        # Both credentials are journalled: whichever the zone does not use after a stop is
        # removed by the clean-up, and dnshelper refuses to remove the one it uses.
        entry_id = secrets.token_hex(8)
        with self.provisioning_lock:
            self.provisioning.add(entry_id)
        journal = {"zone": zone, "kind": "credentials", "credentials": [old]}
        self.store.provisioning_set(entry_id, journal)
        new, switched = None, False
        try:
            self.charge(req, 2)
            new = self.dnshelper(req, "add-credential",
                                 {"name": f"dnsapi: {zone}", "provider": provider, "fields": fields})["id"]
            journal["credentials"] = [new, old]
            self.store.provisioning_set(entry_id, journal)
            try:
                self.dnshelper(req, "update-zone", {"zone": zone, "credential": new})
                switched = True
            except ApiError as exc:
                self.audit(req, "update-zone",
                           result=f"{'rejected' if exc.status < 500 else 'failed'}:{exc.code}", **audit)
                raise
            finally:
                self.forget_zones()
        finally:
            # the unused one goes: the old after the switch, the new if it failed (the journal
            # keeps both only for a clean-up after a stop, which cannot know which)
            unused = [old] if switched else ([new] if new else [])
            if not self.cleanup_credentials(entry_id, {"credentials": unused}):
                log.warning("credential %s of %s was left in dnshelper; a later clean-up removes it",
                            unused[0], zone)
            with self.provisioning_lock:
                self.provisioning.discard(entry_id)
        self.audit(req, "update-zone", **audit)
        return HTTPStatus.OK, {"zone": zone, "provider": provider, "tenant": tenant_id, "full": True,
                               "hosted": True, "dry_run": False}

    def provision(self, req):
        """POST /v1/zones/provision: write records into a customer's domain with
        credentials that are not kept (DESIGN.md, Phase 2, One-shot). The credential
        and the zone exist in dnshelper only while the request runs; a journal entry
        lets cleanup_provisioning() remove them if this process stops before it does."""
        self.require_operator(req)
        self.require_write(req)
        body = self.body_object(req)
        zone = self.zone_body(body)
        provider, fields = self.credentials_param(req, body)
        records = self.records_param(body, "records", ("name", "type", "data"))
        self.require_covered(req, records, "records")
        self.require_not_reserved(zone, records, "records")
        dry_run = self.dry_run_param(body)
        self.validate_credentials(req, zone, provider, fields)
        entry_id = secrets.token_hex(8)
        with self.provisioning_lock:
            self.provisioning.add(entry_id)
        self.store.provisioning_set(entry_id, {"zone": zone, "credential": None})
        failure = None
        result = None
        cred = None
        try:
            self.charge(req)
            cred = self.dnshelper(req, "add-credential",
                                  {"name": f"dnsapi provision {zone}", "provider": provider, "fields": fields})["id"]
            self.store.provisioning_set(entry_id, {"zone": zone, "credential": cred})
            self.charge(req)
            self.dnshelper(req, "add-zone", {"zone": zone, "credential": cred})
            _, result = self.change(req, "append-records", {"records": records}, zone=zone, dry_run=dry_run)
        except ApiError as exc:
            failure = exc
        finally:
            cleaned = self.cleanup_entry(entry_id, {"zone": zone, "credential": cred})
            with self.provisioning_lock:
                self.provisioning.discard(entry_id)
        outcome = "dry-run" if dry_run else "ok"
        if failure is not None:
            outcome = f"{'rejected' if failure.status < 500 else 'failed'}:{failure.code}"
        if not cleaned:
            outcome += ",cleanup_failed"
        self.audit(req, "provision", zone=zone, provider=provider, result=outcome)
        if not cleaned:
            what = (f"{failure.code}: {failure.message}; " if failure is not None else
                    ("the records were written; " if not dry_run else ""))
            raise ApiError(HTTPStatus.BAD_GATEWAY, "cleanup_failed",
                           f"{what}the credential could not be removed from dnshelper yet, and will be "
                           "removed by a later clean-up")
        if failure is not None:
            raise failure
        return HTTPStatus.OK, {"zone": zone, "dry_run": result["dry_run"], "changes": result["changes"],
                               "records": result["records"]}

    def cleanup_entry(self, entry_id, entry):
        """Remove a one-shot zone and credential from dnshelper, then the journal entry.
        The zone is removed only if dnshelper has it with this entry's credential: a zone
        that was there already (zone_already_configured) is not this request's."""
        if entry.get("kind") == "credentials":
            return self.cleanup_credentials(entry_id, entry)
        cred = entry.get("credential")
        ok = True
        if cred:
            try:
                zones = self.run_task("dnshelper", "list-zones", {}).get("zones", [])
            except ApiError as exc:
                log.error("one-shot clean-up of %s: list-zones failed: %s", entry.get("zone"), exc.code)
                return False
            mine = [z["zone"] for z in zones if z.get("credential") == cred]
            for zone in mine:
                ok = self.quietly("remove-zone", {"zone": zone}) and ok
            if ok:
                try:
                    self.run_task("dnshelper", "remove-credential", {"id": cred})
                except ApiError as exc:
                    if exc.code != "credential_not_found":
                        log.error("one-shot clean-up: remove-credential %s failed: %s", cred, exc.code)
                        ok = False
            self.forget_zones()
        if ok:
            self.store.provisioning_drop(entry_id)
        return ok

    def cleanup_credentials(self, entry_id, entry):
        """Remove the credentials of an entry that no zone uses: dnshelper refuses one that a
        zone still uses (credential_in_use), which is then kept. No zone is touched."""
        ok = True
        for cred in entry.get("credentials") or []:
            try:
                self.run_task("dnshelper", "remove-credential", {"id": cred})
            except ApiError as exc:
                if exc.code not in ("credential_not_found", "credential_in_use"):
                    log.error("credential clean-up: remove-credential %s failed: %s", cred, exc.code)
                    ok = False
        if ok:
            self.store.provisioning_drop(entry_id)
        return ok

    def cleanup_provisioning(self):
        """Remove what one-shot requests left in dnshelper when this process, or the
        broker, stopped before their own clean-up (at start and every few minutes).
        Entries a request of this process is still working on are left alone."""
        with self.provisioning_lock:
            active = set(self.provisioning)
        for entry_id, entry in self.store.provisioning().items():
            if entry_id in active:
                continue
            if self.cleanup_entry(entry_id, entry):
                log.info("one-shot clean-up: removed what a stopped request left for %s", entry.get("zone"))

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
            "restrict": record.get("restrict"),
            "created": record.get("created"),
            "modified": record.get("modified"),
            "last_used": self.store.last_used.get(key_id),
            "status": key_status(record, self.store.clock()),
            "revoked": record.get("revoked"),
            "revoked_reason": record.get("revoked_reason"),
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
        self.audit(req, "add-tenant", tenant=output["id"], name=data.get("name", ""))
        return HTTPStatus.CREATED, self.tenant_view(output["id"])

    def update_tenant(self, req):
        self.require_operator(req)
        self.require_write(req)
        tenant_id = self.tenant_param(req)
        body = self.body_object(req)
        data = {k: body[k] for k in ("name", "enabled") if k in body}
        self.own_action("update-tenant", {"id": tenant_id, **data})
        self.audit(req, "update-tenant", tenant=tenant_id, name=self.store.tenant(tenant_id).get("name", ""))
        return HTTPStatus.OK, self.tenant_view(tenant_id)

    def remove_tenant(self, req):
        self.require_operator(req)
        self.require_write(req)
        tenant_id = self.tenant_param(req)
        name = self.store.tenant(tenant_id).get("name", "")
        self.own_action("remove-tenant", {"id": tenant_id})
        self.audit(req, "remove-tenant", tenant=tenant_id, name=name)
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
        # Revoked keys are kept as records (DESIGN.md, Concepts), but listed only on request.
        revoked = req.query.get("revoked", "").lower() in ("1", "true", "yes")
        found = [self.key_view(k, r) for k, r in sorted(self.store.keys().items())
                 if r["owner"] == tenant_id and (revoked or not r.get("revoked"))]
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
        for name in ("scope", "label", "allowlist", "expires", "restrict"):
            if name in body:
                data[name] = body[name]
        self.own_action("create-key", data)
        self.audit(req, "create-key", tenant=tenant_id, key=key_id)
        record = self.store.keys().get(key_id)
        view = self.key_view(key_id, record) if record else {"id": key_id}
        return HTTPStatus.CREATED, {**view, "key": key}

    def tenant_key_param(self, req, tenant_id):
        key_id = req.params["key"]
        record = self.store.keys().get(key_id) if KEY_ID_RE.match(key_id) else None
        if record is None or record["owner"] != tenant_id or record.get("revoked"):
            raise ApiError(HTTPStatus.NOT_FOUND, "key_not_found", "No such key")
        return key_id, record

    def update_tenant_key(self, req):
        """Change a key's label, allowed addresses or expiry (DESIGN.md, Concepts).
        What the key can reach (scope, restrict) is fixed: that is a new key."""
        self.require_operator(req)
        self.require_write(req)
        tenant_id = self.tenant_param(req)
        key_id, before = self.tenant_key_param(req, tenant_id)
        body = self.body_object(req)
        for name in body:
            if name not in EDITABLE_KEY_FIELDS:
                raise ApiError(HTTPStatus.BAD_REQUEST, "not_editable",
                               f"{name} cannot be changed: revoke the key and make another", field=name)
        if not body:
            raise ApiError(HTTPStatus.BAD_REQUEST, "invalid_request",
                           f"Nothing to change: give {', '.join(EDITABLE_KEY_FIELDS)}")
        self.own_action("update-key", {"id": key_id, **body})
        after = self.store.keys().get(key_id) or before
        changes = {n: [before.get(n), after.get(n)] for n in EDITABLE_KEY_FIELDS
                   if before.get(n) != after.get(n)}
        if changes:
            self.audit(req, "update-key", tenant=tenant_id, key=key_id, changes=changes)
        return HTTPStatus.OK, self.key_view(key_id, after)

    def revoke_tenant_key(self, req):
        self.require_operator(req)
        self.require_write(req)
        tenant_id = self.tenant_param(req)
        key_id, _ = self.tenant_key_param(req, tenant_id)
        self.own_action("revoke-key", {"id": key_id})
        self.audit(req, "revoke-key", tenant=tenant_id, key=key_id)
        return HTTPStatus.NO_CONTENT, None

    def audit(self, req, action, **fields):
        # "key" is who acted; a key the operator made, changed or revoked is
        # "target_key", in the journal line as on the Activity page.
        result = fields.pop("result", "ok")
        extra = {("target_key" if k == "key" else k): v for k, v in fields.items()}
        details = " ".join(f'{k}="{v}"' if isinstance(v, str) else f"{k}={json.dumps(v)}"
                           for k, v in extra.items())
        log.info('dnsapi audit: key="%s" owner="%s" address="%s" action="%s" %s result="%s"',
                 req.principal.key_id, req.principal.owner, req.client_ip, action, details, result)
        self.store.append_activity({
            "source": "api", "key": req.principal.key_id, "owner": req.principal.owner,
            "address": req.client_ip, "action": action, "result": result, **extra,
        })


ZONE = r"(?P<zone>[^/]+)"
TENANT = r"(?P<tenant>[^/]+)"

# (pattern, {method: Api method name}); /v1/status is answered in app.py.
ROUTES = [
    (r"/v1/zones", {"GET": "list_zones", "POST": "add_hosted_zone"}),
    (r"/v1/zones/provision", {"POST": "provision"}),
    (rf"/v1/zones/{ZONE}", {"PATCH": "update_hosted_zone", "DELETE": "remove_hosted_zone"}),
    (rf"/v1/zones/{ZONE}/records", {"GET": "get_records", "POST": "append_records", "DELETE": "delete_records"}),
    (rf"/v1/zones/{ZONE}/changes", {"POST": "apply_changes"}),
    (rf"/v1/zones/{ZONE}/rrsets", {"PUT": "set_rrsets"}),
    (rf"/v1/zones/{ZONE}/propagation", {"GET": "get_propagation"}),
    (r"/v1/providers", {"GET": "list_providers"}),
    (r"/v1/acme/present", {"POST": "acme_present"}),
    (r"/v1/acme/cleanup", {"POST": "acme_cleanup"}),
    (r"/v1/tenants", {"GET": "list_tenants", "POST": "add_tenant"}),
    (rf"/v1/tenants/{TENANT}", {"GET": "get_tenant", "PATCH": "update_tenant", "DELETE": "remove_tenant"}),
    (rf"/v1/tenants/{TENANT}/zones/{ZONE}", {"PUT": "assign_zone", "DELETE": "unassign_zone"}),
    (rf"/v1/tenants/{TENANT}/keys", {"GET": "list_tenant_keys", "POST": "create_tenant_key"}),
    (rf"/v1/tenants/{TENANT}/keys/(?P<key>[^/]+)", {"PATCH": "update_tenant_key", "DELETE": "revoke_tenant_key"}),
]
COMPILED = [(re.compile("^" + pattern + "$"), methods) for pattern, methods in ROUTES]


def match_route(path):
    for regex, methods in COMPILED:
        match = regex.match(path)
        if match:
            return methods, match.groupdict()
    return None, {}


__all__ = ["Api", "ApiError", "Request", "match_route", "client_address", "isoformat"]
