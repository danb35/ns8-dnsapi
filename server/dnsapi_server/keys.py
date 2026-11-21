#
# Copyright (C) 2026 Dan Brown
# SPDX-License-Identifier: GPL-3.0-or-later
#
# API key format (DESIGN.md, Concepts): dnsapi_<id>_<secret>. The id (8 hex)
# finds the record; the secret is 32 random bytes in lowercase base32
# without padding (52 characters). Only the SHA-256 of the whole key string
# is stored, so a key cannot be read back. imageroot/pypkg/dnsapi/state.py
# uses the same format.

import base64
import hashlib
import hmac
import re
import secrets

KEY_RE = re.compile(r"^dnsapi_([0-9a-f]{8})_([a-z2-7]{52})$")


def new_key():
    """Return (key id, full key, hash) for a new random key."""
    key_id = secrets.token_hex(4)
    secret = base64.b32encode(secrets.token_bytes(32)).decode().rstrip("=").lower()
    key = f"dnsapi_{key_id}_{secret}"
    return key_id, key, hash_key(key)


def hash_key(key):
    return hashlib.sha256(key.encode()).hexdigest()


def parse_key(key):
    """Return the key id, or None when the string is not a dnsapi key."""
    match = KEY_RE.match(key)
    return match.group(1) if match else None


def hash_matches(key, stored_hash):
    return hmac.compare_digest(hash_key(key), stored_hash or "")
