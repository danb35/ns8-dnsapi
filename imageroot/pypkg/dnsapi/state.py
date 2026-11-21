#
# Copyright (C) 2026 Dan Brown
# SPDX-License-Identifier: GPL-3.0-or-later
#
# The module state, as the actions read and write it (DESIGN.md, Module
# plumbing). The API service (server/dnsapi_server/store.py) reads the same
# files from a read-only mount; only the actions write them.
#
#   settings.json  {"host", "lets_encrypt", "http2https", "ip_allowlist", "rate_limit"}
#   tenants.json   {"tenants": {"t1a2b3c4d": {"name", "enabled", "zones", "created"}}}
#   keys.json      {"keys": {"a1b2c3d4": {"owner", "scope", "hash", "label",
#                                         "allowlist", "expires", "created"}}}
#   runtime.json   {"dnshelper": "module/dnshelper1" | null, "proxies_depth": 0}
#                  (bin/discover-runtime; not backed up: it is recomputed)
#   usage/last-used.json   written by the service
#
# Every file is replaced atomically with mode 0600: the service runs with the
# module's own uid, so it can read them.

import contextlib
import datetime
import fcntl
import ipaddress
import json
import os
import secrets
import sys
import tempfile

SETTINGS_DEFAULTS = {
    "host": None,
    "lets_encrypt": False,
    "http2https": True,
    "ip_allowlist": [],
    "rate_limit": 60,
}


def state_dir():
    return os.environ.get("AGENT_STATE_DIR") or os.getcwd()


def path(name):
    return os.path.join(state_dir(), name)


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@contextlib.contextmanager
def locked():
    """Serialize the actions that change state: NS8 runs tasks in parallel."""
    with open(path(".dnsapi.lock"), "a") as fp:
        fcntl.flock(fp, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fp, fcntl.LOCK_UN)


def load(name, default):
    try:
        with open(path(name)) as fp:
            return json.load(fp)
    except FileNotFoundError:
        return default


def save(name, data):
    fd, tmp = tempfile.mkstemp(dir=state_dir(), prefix="." + name + ".")
    try:
        with os.fdopen(fd, "w") as fp:
            json.dump(data, fp, indent=2, sort_keys=True)
            fp.write("\n")
        os.chmod(tmp, 0o600)
        os.replace(tmp, path(name))
    except BaseException:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(tmp)
        raise


def load_settings():
    return {**SETTINGS_DEFAULTS, **load("settings.json", {})}


def tenants():
    return load("tenants.json", {}).get("tenants", {})


def save_tenants(data):
    save("tenants.json", {"tenants": data})


def keys():
    return load("keys.json", {}).get("keys", {})


def save_keys(data):
    save("keys.json", {"keys": data})


def last_used():
    return load(os.path.join("usage", "last-used.json"), {})


def new_tenant_id(existing):
    while True:
        candidate = "t" + secrets.token_hex(4)
        if candidate not in existing:
            return candidate


def zone_owner(all_tenants, zone):
    for tenant_id, tenant in all_tenants.items():
        if zone in tenant.get("zones", []):
            return tenant_id
    return None


def bad_networks(values):
    """The entries of an allowlist that are not an IP address or network."""
    bad = []
    for value in values:
        try:
            ipaddress.ip_network(value, strict=False)
        except ValueError:
            bad.append(value)
    return bad


def fail(field, error, value="", message=""):
    """Report a problem the caller can fix as an NS8 validation failure and exit."""
    import agent

    entry = {"field": field, "parameter": field, "value": value, "error": error}
    if message:
        entry["message"] = message
    agent.set_status("validation-failed")
    json.dump([entry], fp=sys.stdout)
    sys.exit(2)


def caller():
    """Who runs the task: "module/dnsapi1" when the API service calls its own
    action, otherwise the NS8 user (a cluster administrator)."""
    return os.environ.get("AGENT_TASK_USER") or "shell"


def audit(action, **fields):
    details = " ".join(f'{k}="{v}"' for k, v in fields.items())
    print(f'dnsapi audit: caller="{caller()}" action="{action}" {details}', file=sys.stderr)


def tenant_view(tenant_id, tenant):
    return {
        "id": tenant_id,
        "name": tenant.get("name", ""),
        "enabled": tenant.get("enabled", True),
        "zones": sorted(tenant.get("zones", [])),
        "created": tenant.get("created"),
    }


def key_view(key_id, record, used=None):
    return {
        "id": key_id,
        "owner": record["owner"],
        "scope": record["scope"],
        "label": record.get("label", ""),
        "allowlist": record.get("allowlist") or [],
        "expires": record.get("expires"),
        "created": record.get("created"),
        "last_used": (used or {}).get(key_id),
    }


KEY_ID_PATTERN = "^[0-9a-f]{8}$"
HASH_PATTERN = "^[0-9a-f]{64}$"


def parse_expiry(value):
    """An ISO 8601 date-time in the future, normalized to UTC, or None."""
    if value in (None, ""):
        return None
    try:
        when = datetime.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("not an ISO 8601 date-time")
    if when.tzinfo is None:
        when = when.replace(tzinfo=datetime.timezone.utc)
    if when <= datetime.datetime.now(datetime.timezone.utc):
        raise ValueError("in the past")
    return when.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def add_key(key_id, key_hash, owner, scope, label="", allowlist=None, expires=None):
    """Store a new key record (the caller holds locked()). Return an error
    (field, code, value, message) or None."""
    import re

    if not re.match(KEY_ID_PATTERN, key_id or "") or not re.match(HASH_PATTERN, key_hash or ""):
        return ("id", "invalid_key", key_id or "", "id must be 8 hex digits and hash 64")
    if scope not in ("read", "write"):
        return ("scope", "invalid_scope", scope or "", "scope is read or write")
    all_tenants = tenants()
    if owner != "operator" and owner not in all_tenants:
        return ("owner", "tenant_not_found", owner, "no such tenant")
    allowlist = list(dict.fromkeys(allowlist or []))
    bad = bad_networks(allowlist)
    if bad:
        return ("allowlist", "bad_ip_address", bad[0], "not an IP address or network")
    try:
        expires = parse_expiry(expires)
    except ValueError as exc:
        return ("expires", "invalid_expiry", str(expires), str(exc))
    all_keys = keys()
    if key_id in all_keys:
        return ("id", "key_exists", key_id, "a key with this id exists")
    all_keys[key_id] = {
        "owner": owner,
        "scope": scope,
        "hash": key_hash,
        "label": label or "",
        "allowlist": allowlist,
        "expires": expires,
        "created": now(),
    }
    save_keys(all_keys)
    return None
