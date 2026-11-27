#
# Copyright (C) 2026 Dan Brown
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Read-only view of the module state that the actions write (DESIGN.md,
# Runtime). state/api/ is mounted read-only, without the rest of state/ and
# so without the module's NS8 credentials, which only the broker holds; files are replaced
# atomically, so a changed modification time means a complete new file.
# The only thing the service writes is the last-used time of each key, in
# a separate writable directory.
#
#   settings.json  configure-module: host, rate_limit, ...
#   tenants.json   {"tenants": {"t1a2b3c4d": {"name", "enabled", "zones", "created"}}}
#   keys.json      {"keys": {"a1b2c3d4": {"owner", "scope", "hash", "label",
#                                         "allowlist", "expires", "created",
#                                         "revoked", "revoked_reason"}}}
#   runtime.json   bin/discover-runtime: {"dnshelper": "module/dnshelper1" | null,
#                                         "proxies_depth": 0}

import datetime
import json
import logging
import os
import tempfile
import threading

log = logging.getLogger("dnsapi")

DEFAULT_SETTINGS = {"rate_limit": 60}
ACTIVITY_MAX_BYTES = 1024 * 1024
ACTIVITY_KEEP = 2000
FILES = {
    "settings": ("settings.json", {}),
    "tenants": ("tenants.json", {"tenants": {}}),
    "keys": ("keys.json", {"keys": {}}),
    "runtime": ("runtime.json", {"dnshelper": None, "proxies_depth": 0}),
}


def utcnow():
    return datetime.datetime.now(datetime.timezone.utc)


def isoformat(when):
    return when.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_time(value):
    if not value:
        return None
    try:
        when = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=datetime.timezone.utc)
    return when


class Store:
    def __init__(self, state_dir, usage_dir=None, clock=utcnow):
        self.state_dir = state_dir
        self.usage_dir = usage_dir
        self.clock = clock
        self.lock = threading.Lock()
        self.cache = {}  # name -> (mtime_ns, data)
        self.last_used = {}
        self.usage_dirty = False
        if usage_dir:
            try:
                with open(os.path.join(usage_dir, "last-used.json")) as fp:
                    self.last_used = json.load(fp)
            except (OSError, ValueError):
                self.last_used = {}

    def _load(self, name):
        filename, default = FILES[name]
        path = os.path.join(self.state_dir, filename)
        with self.lock:
            try:
                mtime = os.stat(path).st_mtime_ns
            except FileNotFoundError:
                self.cache[name] = (None, default)
                return default
            cached = self.cache.get(name)
            if cached and cached[0] == mtime:
                return cached[1]
            try:
                with open(path) as fp:
                    data = json.load(fp)
            except (OSError, ValueError) as exc:
                # Keep serving what was read last rather than nothing.
                log.error("cannot read %s: %s", filename, exc)
                return cached[1] if cached else default
            self.cache[name] = (mtime, data)
            return data

    def invalidate(self):
        with self.lock:
            self.cache.clear()

    def settings(self):
        return {**DEFAULT_SETTINGS, **self._load("settings")}

    def tenants(self):
        return self._load("tenants").get("tenants", {})

    def keys(self):
        return self._load("keys").get("keys", {})

    def runtime(self):
        return self._load("runtime")

    def tenant(self, tenant_id):
        return self.tenants().get(tenant_id)

    def zone_tenant(self, zone):
        """The id of the tenant the zone is assigned to, or None."""
        for tenant_id, tenant in self.tenants().items():
            if zone in tenant.get("zones", []):
                return tenant_id
        return None

    # activity (DESIGN.md, Admin UI): the journal is not readable by the module's
    # user, so the changes are also kept in usage/activity.jsonl for the Activity
    # page, trimmed to the most recent entries. The service is its only writer.

    def append_activity(self, entry):
        if not self.usage_dir:
            return
        path = os.path.join(self.usage_dir, "activity.jsonl")
        line = json.dumps({"time": isoformat(self.clock()), **entry}, separators=(",", ":")) + "\n"
        with self.lock:
            try:
                with open(path, "a") as fp:
                    fp.write(line)
                if os.path.getsize(path) > ACTIVITY_MAX_BYTES:
                    with open(path) as fp:
                        keep = fp.readlines()[-ACTIVITY_KEEP:]
                    fd, tmp = tempfile.mkstemp(dir=self.usage_dir, prefix=".activity.")
                    with os.fdopen(fd, "w") as fp:
                        fp.writelines(keep)
                    os.replace(tmp, path)
            except OSError as exc:
                log.error("cannot write activity.jsonl: %s", exc)

    # one-shot journal (DESIGN.md, Phase 2, One-shot): {entry id: {"zone", "credential",
    # "started"}} for each credential a one-shot request may have left in dnshelper.

    def _provisioning_path(self):
        return os.path.join(self.usage_dir, "provisioning.json") if self.usage_dir else None

    def provisioning(self):
        path = self._provisioning_path()
        if not path:
            return {}
        with self.lock:
            try:
                with open(path) as fp:
                    data = json.load(fp)
            except (OSError, ValueError):
                return {}
        return data if isinstance(data, dict) else {}

    def _write_provisioning(self, update):
        path = self._provisioning_path()
        if not path:
            return
        with self.lock:
            try:
                with open(path) as fp:
                    data = json.load(fp)
            except (OSError, ValueError):
                data = {}
            if not isinstance(data, dict):
                data = {}
            update(data)
            fd, tmp = tempfile.mkstemp(dir=self.usage_dir, prefix=".provisioning.")
            with os.fdopen(fd, "w") as fp:
                json.dump(data, fp)
            os.replace(tmp, path)

    def provisioning_set(self, entry_id, entry):
        def update(data):
            data[entry_id] = {**data.get(entry_id, {"started": isoformat(self.clock())}), **entry}
        self._write_provisioning(update)

    def provisioning_drop(self, entry_id):
        self._write_provisioning(lambda data: data.pop(entry_id, None))

    # last-used times

    def touch_key(self, key_id):
        stamp = isoformat(self.clock())
        with self.lock:
            # Minute resolution is enough, and it keeps writes rare.
            if self.last_used.get(key_id, "")[:16] != stamp[:16]:
                self.last_used[key_id] = stamp
                self.usage_dirty = True

    def flush_usage(self):
        if not self.usage_dir:
            return
        with self.lock:
            if not self.usage_dirty:
                return
            known = self.keys_unlocked()
            data = {k: v for k, v in self.last_used.items() if k in known}
            self.usage_dirty = False
        try:
            fd, tmp = tempfile.mkstemp(dir=self.usage_dir, prefix=".last-used.")
            with os.fdopen(fd, "w") as fp:
                json.dump(data, fp)
            os.replace(tmp, os.path.join(self.usage_dir, "last-used.json"))
        except OSError as exc:
            log.error("cannot write last-used.json: %s", exc)

    def keys_unlocked(self):
        cached = self.cache.get("keys")
        if cached is None:
            return set(self.last_used)  # not loaded yet: keep everything
        return set(cached[1].get("keys", {}))
