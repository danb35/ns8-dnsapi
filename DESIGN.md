# ns8-dnsapi: design brief (draft)

A separate NS8 module that puts an HTTPS API in front of dnshelper, so that software outside the
cluster (a billing or client portal such as Blesta or WHMCS, or the operator's own scripts) can
manage DNS records for the operator's customers. It is a dnshelper consumer like any other module:
it holds no DNS provider code and talks to DNS hosts only through dnshelper's actions.

The dnshelper side is in
[dnshelper's DESIGN.md](https://github.com/danb35/ns8-dnshelper/blob/master/DESIGN.md#delegated-access-for-an-api-module-draft),
"Delegated access for an API module". Items marked **VERIFY** were not confirmed from the sources
or on a node.

Status: build order steps 1 to 8 are done (the service and its route; tenants, keys,
authentication, rate limits and the read endpoints; the write endpoints; ACME DNS-01; the admin
UI and the OpenAPI document; the full node test; the API host name in DNS; the hardening from the
security review); steps 9 to 11 (editable keys, the provider list, CI with dnshelper) are done,
and released as 0.1.0. dnshelper's side, phase 1, is released in dnshelper 0.7.0 (2026-11-21),
which this module needs at least; `GET /v1/providers` needs dnshelper 0.7.1.

Origin: forum request, community.nethserver.org topic 28774, posts 32-37 (2026-11-18/20). The
ACME DNS-01 use was added by the operator on 2026-11-21.

## Scope

- **In:** a REST API with API keys; tenants (the operator's customers), each limited to their own
  zones; record reads and changes through dnshelper; an NS8 admin UI to manage tenants, zones and
  keys.
- **In:** ACME DNS-01 validation for other systems, including ones the internet cannot reach: they
  create and remove their `_acme-challenge` TXT records through dnsapi, with keys limited to those
  records (see [ACME DNS-01 validation](#acme-dns-01-validation)).
- **Later (phase 2):** the operator's tool adds domains and their DNS provider credentials through
  the API, kept for hosting or removed once the records are written (see
  [Phase 2](#phase-2-domains-added-through-the-api-design-not-built)). Needs the dnshelper
  changes in its DESIGN.md, phase 2 (not built).
- **Later (phase 3):** creating zones on ns8-powerdns ("DNS hosting by the operator"). Needs an
  ns8-powerdns change too.
- **Deferred:** a control panel the operator's customers log into (OIDC, TOTP). It would sit on
  top of this API, in this module or another one.
- **Out:** DNS provider code, zone-level settings (DNSSEC, SOA), registrar operations (domain
  registration, name server changes at the registrar).

## Why a separate module

dnshelper is reachable only through the NS8 api-server: cluster administrators and modules that
were granted a role. That is why it can have no authentication of its own. This module is the
opposite: it is exposed to the internet and does its own authentication. Keeping the two apart
means:

- a fault in the public-facing code is limited to what dnshelper's policy lets this module do;
- dnshelper stays a set of on-demand actions with no long-running service;
- administrators who don't need the API never install the code that faces the internet.

## Concepts

- **Tenant:** one of the operator's customers. Id (`t<8 hex>`), name, enabled flag, zones.
- **Zone assignment:** a zone managed by dnshelper, given to at most one tenant. A tenant sees and
  changes only its own zones. The zones dnsapi may assign are the ones dnshelper's policy lets it
  write: `list-zones` and `has-zone` report `access` and `full` (dnshelper 0.7.0). `full: true`
  means one write rule allows every name and type, as the "API module (all records)" preset on
  dnshelper's Access page grants; that is what a hosting customer needs. A zone with a narrower
  write rule (`access: "write"`, `full: false`), such as dnshelper's ACME preset, can be assigned
  too, for ACME use (decision 2026-11-21, see [ACME DNS-01 validation](#acme-dns-01-validation)).
  The NS8 administrator sets those rules, and dnsapi cannot widen them.
- **API key:** belongs to either the operator or one tenant.
  - Operator key: manages tenants and assignments, and acts on any tenant's zones. This is the key
    a billing portal uses: it acts for whichever customer is logged into it.
  - Tenant key: reaches only that tenant's zones. For customers who script their own DNS.
  - Every key has: a scope (`read` or `write`), an optional IP allowlist (CIDR), an optional
    expiry, a label, and created and last-used times.
  - A key can also be restricted to some names and types (`restrict`, see
    [ACME DNS-01 validation](#acme-dns-01-validation)); by default it reaches every record of its
    zones.
  - Revoked keys are kept (decision 2026-11-23, from the operator), so the Keys page can list
    them. `revoke-key` and `revoke-exposed-key` mark the record with `revoked` (the time) and
    `revoked_reason` (`revoked`, or `plain_http` for a key the API received over plain HTTP)
    instead of deleting it; the hash stays, so a revoked key is refused with 401 `key_revoked`
    after its hash matches, and its id can never be made again. `list-keys` returns every key
    with a `status` (`active`, `expired`, `revoked`); the Keys page lists the expired and revoked
    ones after the others, dimmed and struck through, behind a "Show revoked and expired keys"
    check box (on by default, remembered in the browser). `GET /v1/tenants/{id}/keys` leaves
    revoked keys out unless `?revoked=true`, so existing portals see no change. The tenant and
    Status page counts are of active keys only. `remove-tenant` still deletes its keys: they
    would have no owner to list them under. Kept without limit: a record is a few hundred bytes.
  - A key's label, allowlist and expiry can be changed (decision 2026-11-25, from the operator;
    the earlier position was that nothing could be). Its owner, scope and `restrict` stay fixed:
    they decide what the key can reach, and a key handed to a less-trusted host (an ACME client
    on an internal box, a customer's script) must not gain reach after it was given out. A key
    that should reach more is a new key. The secret does not change either, so a key that may
    have leaked is still revoked, not edited.
    - `update-key` (`id`, and any of `label`, `allowlist`, `expires`; a field left out keeps its
      value) records `modified` (the time) on the key and an audit line and Activity entry with
      each changed field's old and new value. A revoked key cannot be changed (`key_revoked`);
      revocation stays final.
    - An expired key given a later expiry works again: it is the same as making a new key with
      the same settings, without redeploying it. The new expiry must be in the future, as at
      creation.
    - Through the API: `PATCH /v1/tenants/{id}/keys/{key id}` for tenant keys; any other field
      is 400 `not_editable`, and a revoked key is 404 as for `DELETE`. Like `create-key` and
      `revoke-key`, the action refuses operator keys when the module itself calls it, so the
      service cannot change an operator key's allowlist or expiry. For tenant keys it gives a
      compromised service nothing new: it can already make tenant keys with any settings.
    - Changes apply on the next request: the service reloads `keys.json` when it changes. Rate
      and concurrency counts are kept by key id, so they carry over.
- **Key format:** `dnsapi_<id>_<secret>`. The id (8 hex) finds the record. The secret (32 random
  bytes, base32) is stored only as its SHA-256 hash, which is enough for a random secret of that
  length. The full key is shown once, at creation; there is no way to read it back. The prefix
  lets secret scanners recognise leaked keys.

## API (v1)

JSON over HTTPS. Authentication: `Authorization: Bearer <key>`. Errors are `{"error": {"code",
"message", "field"}}`. dnshelper's error codes (`not_permitted`, `stale`, `cnameconflict`, ...)
are passed through, and the HTTP status follows the error class (400 validation, 403 permission,
404 unknown zone, 409 stale or conflict, 429 rate limit, 502 provider failure). An OpenAPI document
is served at `/v1/openapi.json`.

Records use dnshelper's own shape (`name` relative to the zone, `type`, `ttl`, `data`), so its
semantics carry over as they are: TXT as one unquoted string, exact matching for deletes, apex NS
and SOA read-only.

| Method and path | Key | dnshelper action |
|---|---|---|
| `GET /v1/zones` | any | the caller's zones (operator: every assignable zone, with its tenant) |
| `GET /v1/zones/{zone}/records` | any | `get-records` |
| `POST /v1/zones/{zone}/changes` `{remove, add, dry_run}` | write | `apply-changes` (strict removes; an edit is one remove plus one add) |
| `POST /v1/zones/{zone}/records` `{records, dry_run}` | write | `append-records` |
| `PUT /v1/zones/{zone}/rrsets` `{records, dry_run}` | write | `set-records` mode `rrset` |
| `DELETE /v1/zones/{zone}/records` `{records, dry_run}` | write | `delete-records` |
| `GET /v1/zones/{zone}/propagation?name=&type=` | any | `check-propagation` (in dnshelper's `dnsreader` role since 0.7.0) |
| `GET /v1/providers` | operator | `list-providers` (in dnshelper's `dnsreader` role after 0.7.0; see [Providers](#providers)) |
| `GET/POST/PATCH/DELETE /v1/tenants[/{id}]` | operator | none (dnsapi's own state) |
| `PUT/DELETE /v1/tenants/{id}/zones/{zone}` | operator | `list-zones` checks that dnsapi may write in it (`access: "write"`; `full` or not) |
| `POST/PATCH/DELETE /v1/tenants/{id}/keys[/{key id}]` | operator | none (`PATCH` changes only `label`, `allowlist`, `expires`) |
| `POST /v1/acme/present`, `POST /v1/acme/cleanup` `{fqdn, value}` | write | `append-records`, `delete-records` of one `_acme-challenge` TXT record (see [ACME DNS-01 validation](#acme-dns-01-validation)) |
| `GET /v1/status` | none | none (liveness only, says nothing about zones) |

A tenant key that names a zone it doesn't own gets 404, not 403, so that a key cannot be used to
find out which zones are managed.

Phase 2 adds `POST /v1/zones` (add a domain with a provider and credentials), `DELETE
/v1/zones/{zone}` and `POST /v1/zones/provision` (one-shot), using dnshelper's delegated-zone
actions; see [Phase 2](#phase-2-domains-added-through-the-api-design-not-built).

## Providers

Request (2026-11-25, forum topic 29504, post 7, the operator): the portal should be able to list
the DNS hosts it can offer from dnsapi itself, so that a host added to dnshelper appears without
anyone keeping a list by hand. It is the first piece of phase 2 (adding domains and their
credentials through the API), which the same post asks for; only the list is built.

- `GET /v1/providers` returns dnshelper's `list-providers`: each DNS host's `name` (as in a
  zone's `provider`), `label`, `notes`, the record `types` it supports, and the credential
  `fields` it takes (`name`, `label`, `secret`, `required`, `default`). dnsapi passes on only
  those keys, so what a later dnshelper adds is not exposed until it is documented here.
- Operator keys only, restricted ones included: the list is dnshelper's built-in registry, the
  same for every caller, and says nothing about the administrator's credentials or zones. A tenant
  key gets 404, as for the other operator endpoints. Configured credentials are not listed: they
  are the administrator's, and phase 2 lets a delegate use only the ones it made.
- Cached for 10 minutes (the list changes only when dnshelper is updated); a miss counts once
  against the key's rate limit.
- dnshelper needed a change: `list-providers` was admin only until 0.7.0, and is now in
  `dnsreader` (so `dnswriter`), with no policy rule needed (dnshelper's DESIGN.md, Delegated
  access, phase 1). With dnshelper 0.7.0 the api-server refuses the task with 403. The broker
  now reports an api-server 403 as `not_granted` instead of `api_server`, and the API answers 503
  `not_granted`, saying that dnshelper may need updating. dnsapi's minimum dnshelper stays 0.7.0:
  only this endpoint needs the newer one. The 403 is from the sources (2026-11-25): ns8-core's
  api-server (`core/api-server/middleware/middleware.go`) has an `Authorizer` that returns false
  for an action outside the caller's roles, and gin-jwt (v3) answers that with 403; its
  `Unauthorized` handler keeps the code. Seen on the test node (2026-11-25): "api-server answered
  403 for module/dnshelper4/list-providers".

## Phase 2: domains added through the API (design, not built)

Request (2026-11-25, forum topic 29504, post 7, the operator): the operator's portal adds a
customer's domain with the customer's DNS host and credentials, and dnsapi writes the records the
operator's service needs (for example for hosted mail). Asked in post 8 and answered in post 10
(2026-11-26):

- dnsapi reaching only the zones it added, and nothing else, is acceptable.
- Only the operator's portal (operator keys) adds domains, for now. Customers entering their own
  credentials may come later.
- The one-hour expiry was only an idea; any short time would do.
- The customers' DNS hosts are not known in advance: each customer brings the one they already
  use. The portal offers what `GET /v1/providers` returns (see [Providers](#providers)), and the
  set grows as dnshelper adds providers.
- Two uses, both needed:
  - **One-shot**, for example transactional mail: the records are written while the domain is
    validated, and the credentials are not needed afterwards.
  - **Hosting**: the customer keeps managing the domain's records through the operator's
    interface, so the zone and its credentials stay. Hosting the zone on the operator's own
    PowerDNS is phase 3.

Decision (2026-11-26): both uses are in phase 2. They use the same dnshelper actions; one-shot
adds one dnsapi endpoint and a clean-up, and nothing in dnshelper.

### What dnshelper provides

dnshelper's DESIGN.md, Delegated access, phase 2 (not built): a `dnszoneadmin` role
(`dnswriter` plus `list-provider-zones`, `validate-zone`, the credential actions and the zone
actions), allowed only for modules listed in its `delegates` setting. A credential a delegate
creates is marked `delegated_to: "module/<id>"`; a zone is delegated when its credential is. A
delegate may add zones only with its own credentials, change or remove only its own credentials
and zones, and write every record of its own zones without a policy rule. The administrator sees
them tagged, can remove them or take them over, but cannot edit them in place.

For dnsapi that means:

- The grant becomes `dnshelper@any:dnszoneadmin` (it includes `dnswriter`), and the
  administrator adds dnsapi to dnshelper's `delegates` to turn the feature on. Without it,
  dnshelper refuses with `not_permitted`, and the API answers 403 with a message that says so.
- The broker's allowlist gains `add-credential`, `remove-credential`, `add-zone`, `remove-zone`,
  `validate-zone` and `list-provider-zones`. `update-credential` and `update-zone` are left out
  until a use for them appears.
- A delegated zone is assignable like any other (`list-zones` reports it with `access: "write"`
  and `full: true`). **VERIFY** once dnshelper's side is built.

### Hosting

- `POST /v1/zones` `{zone, provider, credentials, tenant, dry_run}`, operator keys only
  (unrestricted ones: a restricted operator key reaches no tenant endpoint either).
  1. Check `provider` against `list-providers` and `credentials` against its `fields`: only
     those names, and the required ones present. dnshelper checks them again.
  2. `add-credential` with one new credential per zone, so that removing a zone can remove its
     credential without checking what else uses it.
  3. `add-zone`, then `validate-zone`: the credential reaches the zone at the DNS host. If either
     fails, the credential is removed again and the error is returned (400 or 502, as for other
     dnshelper errors).
  4. Assign the zone to `tenant` in the same request, so the portal does not need a second call.
  - `dry_run` runs steps 1 and 3's check without keeping anything: the credential and zone are
    added, validated and removed. **VERIFY** whether dnshelper can validate credentials without
    adding them (`list-provider-zones` with credentials not yet stored).
  - A zone dnshelper already manages (the administrator's, or another delegate's) is refused with
    409: dnshelper's `add-zone` raises `zone_already_configured` (checked 2026-11-26 in
    `dnshelper_lib.py`), which dnsapi maps to 409 like `zone_assigned`.
- After that, the tenant's keys and the operator's keys manage the zone's records through the
  existing endpoints, as for any assigned zone.
- `DELETE /v1/zones/{zone}`, operator keys only, for a zone dnsapi added: unassign it,
  `remove-zone`, then `remove-credential`. The records stay at the DNS host: dnshelper's
  `remove-zone` drops the zone from its list with its snapshots and owner index, and does not
  contact the DNS host (checked 2026-11-26 in `dnshelper_lib.py`). A zone
  dnsapi did not add is 404, as is one the administrator took over.
- The credential fields are passed on as they are and never stored or logged by dnsapi; the audit
  line and Activity entry name the zone, provider and tenant only. NS8 masks secret fields in its
  task records and audit log by name, and every secret field in dnshelper's provider list has a
  name that NS8 masks (checked 2026-11-25 against `core/agent/htask.go` and the api-server's
  `tasks.go`).

### One-shot

- `POST /v1/zones/provision` `{zone, provider, credentials, records, dry_run}`, operator keys
  only: add the credential and the zone, write `records` (as `POST .../records` does, at most
  100), then remove the zone and the credential. The answer lists what was written. The records
  stay at the DNS host; nothing stays in dnshelper or dnsapi. No tenant is involved.
- The zone and credential are removed whatever happened in between, a failed write included. If
  the removal itself fails, the answer says so (502 with `cleanup_failed`) and the clean-up below
  retries it.
- **Clean-up after a crash.** If the service or the broker stops between adding and removing, a
  customer's credentials would stay in dnshelper. So before `add-credential`, dnsapi records the
  zone and credential id in `state/usage/provisioning.json`, and drops the entry once both are
  removed. At start, and every few minutes, entries older than the request timeout are removed
  from dnshelper and then from the file. A credential then lives for one request, or until the
  next clean-up after a crash.
- A zone dnshelper already manages is refused, as for hosting: one-shot does not write into an
  existing zone with other credentials.
- `restrict` and the reserved name apply to `records` as to any write. **Open:** whether one-shot
  needs `on_behalf_of` (there is no tenant; `operator:<key id>` is the likely choice).

Alternative considered: a dnshelper action that writes records with credentials given in the
request, without storing them, so that nothing could be left behind. Not needed with the clean-up
above, and it would bypass dnshelper's zone list, owner index and snapshots.

### Security

The concern raised in post 8 stays, and is the reason the feature is off until the administrator
lists dnsapi in dnshelper's `delegates`:

- dnshelper holds customers' credentials, briefly for one-shot and for as long as the domain is
  hosted. With many DNS hosts a credential reaches the customer's whole account, not one zone. A
  compromised dnsapi service could use every hosted credential, through the records it can write.
- dnsapi gains a role that adds zones. dnshelper's rules keep it to zones it added with
  credentials it supplied, never the administrator's, but a compromised service can do more than
  in phase 1.
- The user guide tells operators to ask customers for credentials limited to the zone, and with
  an expiry, where the DNS host offers them (Cloudflare tokens can have both, and an IP filter).
  That limit holds even if dnsapi does not. Whether a provider offers such tokens could become a
  field of `list-providers` (a dnshelper change), so the portal can say so.

### Not decided

- Which use comes first, if they are not built together.
- Customers adding their own domains with a tenant key (post 10: later).
- What happens to hosted zones when their tenant is removed: removed with it (records left at the
  DNS host), or refused while the tenant has hosted zones.
- How the portal handles a DNS host dnshelper does not support: it shows the records for the
  customer to add by hand and checks them itself (`propagation` works only for zones dnsapi
  manages).

## ACME DNS-01 validation

Decision (2026-11-21): dnsapi also serves systems that get certificates from Let's Encrypt (or
another ACME CA) with the DNS-01 challenge, above all ones the internet cannot reach, so that
HTTP-01 is impossible for them. Such a system creates a TXT record at
`_acme-challenge.<host name>`, waits for the CA to see it, and removes it. It needs nothing else
in the zone, so it should be able to do nothing else.

The REST API already does the job: `POST .../records` to add the TXT record (adding never
removes, so a wildcard and its base name can both have a value at the same name), `GET
.../propagation` to wait, `DELETE .../records` with the exact value to remove it, and dnshelper's
helper locks each zone, so two systems validating at once do not lose a value. Three additions
make it safe and easy:

1. **Keys limited to some records.** A key may carry `restrict: {"names": [...], "types": [...]}`:
   name patterns relative to the zone (with `*` and `?`, as in dnshelper's rules) and record types.
   The `acme` preset is `{"names": ["_acme-challenge", "_acme-challenge.*"], "types": ["TXT"]}`.
   - dnsapi checks it before calling dnshelper. A change is refused as a whole (403
     `outside_restriction`) if any record to add or remove is outside it; a delete without a
     `type` needs `types` to allow every type.
   - Reads return only the records inside it; `propagation` is refused outside it.
   - A restricted operator key reaches the zones but not the tenant and key endpoints.
   - It is set when the key is made and cannot be changed: revoke the key and make another
     (still so after keys became editable on 2026-11-25: only label, allowlist and expiry are).
   - Without this, a leaked key on an internal host could rewrite every record of the zone.
2. **Zones with partial access.** A zone whose dnshelper rule for dnsapi is narrower than full
   (dnshelper's ACME preset: `_acme-challenge` and `_acme-challenge.*`, TXT) can be assigned, so
   the administrator does not have to grant dnsapi the whole zone for ACME use.
   - dnshelper's rule stays the outer limit: a change outside it is refused by dnshelper (403
     `not_permitted`), and reads return only what it covers. dnsapi cannot see the rule's names and
     types (`list-zones` does not report them), so it cannot refuse earlier.
   - `GET /v1/zones`, `list-assignable-zones` and the admin UI show `full` for each zone, so an
     operator does not hand a hosting customer a zone they can only partly change.
3. **Endpoints for existing ACME clients.** `POST /v1/acme/present` and `POST /v1/acme/cleanup`
   with `{"fqdn": "_acme-challenge.www.example.com.", "value": "<token>"}`, which is what lego's
   `httpreq` provider (lego is also inside Traefik), acme.sh's `acmeproxy` and Caddy's `acmeproxy`
   DNS module send. The
   client is configured with `https://<dnsapi host>/v1/acme` as its endpoint and the key as its
   password.
   - The fully qualified name must start with the label `_acme-challenge`. The zone is the
     longest of the key's zones that contains it; the name sent to dnshelper is relative to it.
   - `present` adds the TXT record (TTL 60, which a provider with a higher minimum raises);
     `cleanup` deletes that exact name, type and value. Both carry `on_behalf_of`, need a write
     key, count against the rate limit and log an audit line, as any change does.
   - They are limited to `_acme-challenge` TXT records whatever the key's `restrict`, and the
     key's `restrict` applies too.
   - These clients send HTTP Basic authentication. dnsapi accepts Basic, with the key as the
     password and any user name, on these two endpoints only; Bearer works there too.
   - Verified against the sources (2026-11-21; lego v5.6.0 `providers/dns/httpreq/httpreq.go`,
     acme.sh `dnsapi/dns_acmeproxy.sh`): both `POST <endpoint>/present` and `/cleanup` with
     `{"fqdn", "value"}` and `Content-Type: application/json`, and send Basic authentication only
     when both user name and password are set.
     - lego sends its `EffectiveFQDN` with the trailing dot, which follows a CNAME on
       `_acme-challenge`; such a target outside `_acme-challenge` names is refused. It accepts any
       2xx and ignores the body. Its HTTP timeout is 30 s by default (`HTTPREQ_HTTP_TIMEOUT`).
       Its `RAW` mode (`{"domain", "token", "keyAuth"}`) is not supported.
     - acme.sh appends the trailing dot itself and counts the call as done only when the reply
       contains the value in quotes, so both endpoints answer with `{"fqdn", "value", "zone",
       "changes"}`.
     - Caddy (checked 2026-11-22 against `caddy-dns/acmeproxy` v1.1.1 and the
       `libdns/acmeproxy` it uses; run 2026-11-23, see below): Caddy does not use lego; its DNS modules are libdns
       providers, and the `acmeproxy` one, which standard Caddy builds do not include, sends the
       same requests, with `fqdn` built by `libdns.AbsoluteName` (trailing dot), and Basic
       authentication when a user name or password is set. It accepts only 200, and only a JSON
       reply whose `fqdn` and `value` equal what it sent, so both endpoints echo them as received.
       Tested by the operator (2026-11-23): Caddy 2.11.9 with `caddy-dns/acmeproxy` and an
       ACME-restricted tenant key, against `dnsapi1` on the test node (`dnsapi:latest`, master at
       `a0b668d`), obtained a production Let's Encrypt certificate; the key's last-used time
       showed on the Keys page.
   - certbot has no such plugin: the user guide shows a `--manual-auth-hook` and
     `--manual-cleanup-hook` script that calls `/v1/acme/present` and `/cleanup` with curl.
     Tested 2026-11-23: certbot 4.0.0 on Debian 13, the guide's script unchanged, the same
     ACME-restricted key as the Caddy test, Let's Encrypt's staging CA, one certificate for
     `caddy-test.2v6.in` and `*.caddy-test.2v6.in`. Both values were at the same name at once,
     each was removed on its own, and no record was left; two add and two delete audit lines, in
     dnsapi's log and in dnshelper's (with `on_behalf_of`). It took 2 minutes, mostly the
     script's 30-second wait after each value.

A typical setup for internal hosts:
- on dnshelper's Access page, the ACME preset for `module/dnsapi1` on the zones concerned;
- a tenant, for example "Internal hosts", with those zones;
- one key per host: write scope, `restrict` preset `acme`, the host's address in its allowlist,
  optionally an expiry.

The CA validates against the zone's public name servers, so the zones must be public, even when
the hosts are not. NS8's own Let's Encrypt certificates (Traefik) are unrelated to this.

## The API host name in DNS

Decision (2026-11-21, from the operator): the API's host name is usually in a zone dnshelper
manages. `configure-module` then publishes it itself, so that the Let's Encrypt certificate that
`set-route` requests can be issued without the administrator adding the record by hand.

- **The record** is a CNAME from the host name to the node's own host name, which the node's
  `get-fqdn` action returns (as ns8-automx does; it needs the `node:reader` role). A CNAME follows
  the node if its address changes, and dnsapi cannot reliably know the node's public address
  (it may be behind NAT), so no A or AAAA record is made. A host name at a zone's apex cannot have
  a CNAME, so it is left to the administrator.
- **Before `set-route`**, in `configure-module`, when `publish_host_record` is on (default on):
  1. `has-zone` with the record (`{"name": <host>, "type": "CNAME"}`): whether dnshelper manages
     a zone containing the host name and whether its rules let dnsapi write that CNAME, decided
     from the rules without contacting the DNS host. Not managed, not permitted, or the apex:
     nothing is written, and the Status and Settings pages say why.
  2. `get-records` for the name: a CNAME to the node already there, nothing to do; nothing
     there, the CNAME is added (`append-records`, without `on_behalf_of`, so dnshelper records
     dnsapi as its owner and the Records page shows whose it is); anything else, such as another
     CNAME or an A record, is never overwritten: it is reported as a conflict and the route is
     set up as before. A record dnshelper's rules do not let dnsapi read can be invisible here;
     adding the CNAME beside it is refused by dnshelper (`conflict`), and reported the same way.
  3. After adding the record, when a Let's Encrypt certificate is requested, wait (at most 90 s)
     until `check-propagation` reports that the zone's name servers answer with it. A name that
     was looked up before it existed can be cached as absent, and `lets_encrypt_check` makes
     `set-route` fail the action if the certificate is not issued at once. If the wait runs out,
     `set-route` is tried anyway.
- **Nothing here fails `configure-module`**: dnshelper missing or not answering, a missing rule
  or a conflict only change what the pages report. The result is kept in `state/host-record.json`
  (`status`: `ok`, `created`, `conflict`, `not_managed`, `not_permitted`, `apex`, `disabled`,
  `error`), and `get-configuration` and `get-overview` return it.
- **The rule it needs**: a dnshelper rule for `module/dnsapi1`, write, names `<host label>`,
  types `CNAME`. The "API module (all records)" preset on the zone covers it too.
- **Reserved name.** A zone that holds the API host name may also be assigned to a tenant, in full
  or in part. A key of that tenant could otherwise point the API's name elsewhere, or get a
  certificate for it through `_acme-challenge.<host>`, and so collect the keys sent to the API.
  The service refuses any change through the API to records at the host name or at
  `_acme-challenge.<host>` (403 `reserved_name`), for every key, the operator's included; reads
  are not restricted.
- **When the host name changes**, the old name's record is left as it is: deleting a live record
  automatically could break something else that uses it. The administrator removes it on
  dnshelper's Records page, where it is listed as dnsapi's.
- **After a restore to another node**, the existing CNAME points to the old node; it is reported
  as a conflict, not changed.

## Security

- **Transport:** a Traefik route on a dedicated host name (`set-route`: `host`, `lets_encrypt`,
  and `http2https` always off, see HTTPS only). There is an optional cluster-wide IP allowlist (`ip_allowlist`, present in
  ns8-traefik since 3.0.0, verified in its `set-route` schema), so an operator whose only client is
  their billing server can close the API to everyone else at Traefik. The service listens on
  127.0.0.1 on a port from `org.nethserver.tcp-ports-demand`.
- **The API host name's own DNS record** (decision 2026-11-21, from the operator): see
  [The API host name in DNS](#the-api-host-name-in-dns). The name is reserved: no API key may
  change its records, or `_acme-challenge.<host>`, whatever the key's zones.
- **Per-key IP allowlist:** enforced by the service, using the client address Traefik forwards.
  Verified on the test node (2026-11-21, ns8-traefik 4.2.5): with no trusted proxies, Traefik
  drops a client's `X-Forwarded-For` and `X-Real-Ip` and sends its own peer's address in both, so
  a client cannot inject one. With trusted proxies (`set-trusted-proxies`, `PROXIES_DEPTH`), the
  client is `PROXIES_DEPTH` entries left of the last one in `X-Forwarded-For`; dnsapi reads the
  depth from Traefik's environment (`bin/discover-runtime`) at start and on events, so a change of
  trusted proxies needs a restart of the service. The header is used only on requests from
  loopback (Traefik).
- **Brute force:** keys are random, so guessing is not the realistic risk, but failed
  authentications are still counted per source address and throttled (429 with `Retry-After`), and
  logged. Decision (2026-11-21, security review): an IPv6 client is counted by its /64 network,
  since one host usually has a whole /64 to rotate through; IPv4 by its address.
- **HTTPS only** (decision 2026-11-21, security review): Traefik also serves the route over plain
  HTTP, and with `http2https` off a client could send its key in the clear on every request. The
  service refuses a request that Traefik received over plain HTTP (its `X-Forwarded-Proto` is not
  `https`) with 403 `https_required`, whatever the setting, and logs the key id it carried so the
  administrator can revoke a key that went over the network unencrypted. Requests without the
  header come straight from the node (the systemd start check, local scripts) and are accepted.
  Verified on the test node (2026-11-21): Traefik replaces a client's `X-Forwarded-Proto`, as
  it does `X-Forwarded-For`. `http2https` cannot prevent the first cleartext request: the redirect comes
  after the key was sent. Clients must use the `https://` URL.
- **Keys sent over plain HTTP are revoked** (decision 2026-11-22, issue #12). A key that crossed
  the network in the clear has to be replaced anyway, and the request has already been refused,
  so revoking it at once only stops whoever captured it.
  - The route never redirects: `configure-module` always sends `http2https: false`, and the
    setting is gone (`http2https` in its input is accepted and ignored;
    `update-module.d/30route` republishes an existing route). With the redirect, Traefik answers
    a plain-HTTP request itself, so the service could neither tell the client why it failed nor
    revoke the key, and a well-behaved client does not send its key again to the new address.
  - The key is checked against its hash first, as authentication does: key ids are not secret
    (logs, the Keys and Activity pages), so a key-shaped string with a real id and the wrong
    secret is only logged. Basic is read on `/v1/acme/` too, where the ACME clients send it.
    The answer is the same 403 `https_required` whatever happens, so it reveals nothing.
  - The service calls `revoke-exposed-key` through the broker. Unlike `revoke-key`, it revokes
    operator keys too when the module calls it. Revoking only takes access away: a compromised
    service could already refuse every request, so this gives it nothing new; making operator
    keys stays out of its reach.
  - An audit line and an Activity entry (`revoke-exposed-key`, with the client address); the
    Status page lists the keys revoked so in the last 7 days (`get-overview` `exposed_keys`).
  - `revoke_cleartext_keys` in Settings, default on; off, the key id is only logged, as before.
- **Concurrency limits** (decision 2026-11-21, security review): the service started a thread per
  connection without limit, and a request waits up to 150 s for a DNS host. Now at most 64
  connections are served at once (one more is answered 503 `busy` and closed), at most 4 requests
  of one key are in progress at once (429 `too_many_concurrent`, `Retry-After: 5`), and at most 16
  NS8 tasks run at once for the whole service (beyond that, a request waits up to 10 s for a
  slot, then 503 `busy`). The per-key rate limit still applies on top.
- **Rate limits** per key, configurable (`rate_limit`), default 60 per minute. They protect the
  DNS hosts' own limits, which are shared by every user of a credential (GoDaddy is about 60 per
  minute). Decision (2026-11-21): every dnshelper call counts, reads included, because a read is a
  provider call too; a records read is two (`get-records` and `list-owners`). The list of
  assignable zones is cached for 30 s.
- **Limits:** request body at most 1 MB; at most 100 records per change (dnshelper's limit).
- **No CORS** by default: the API is for servers, not browsers. This becomes a setting if the
  customer control panel is built as a browser app on another origin.
- **Isolation:** two checks, one in each module. dnsapi checks that the tenant owns the zone;
  dnshelper checks that dnsapi may write the zone. A bug in dnsapi's tenant check cannot reach a
  zone the NS8 administrator did not grant to dnsapi.
- **Records written by other modules:** decision (2026-11-21): a tenant may change them, with a
  warning. These are records dnshelper's owner index says another module wrote, such as mail1's
  DKIM or MX.
  - `GET .../records` gives such records `owned_by: ["mail1"]`, from `list-owners`.
  - A change that removes or replaces one of them still goes through. Its response, including the
    `dry_run` response, carries `warnings: [{"code": "owned_by_module", "record", "modules"}]`,
    explaining that the module may write the record again.
  - The README tells portal authors to run a dry run first and show the warning before applying.
  - dnsapi's own writes carry `on_behalf_of`, so dnshelper records no owner for them. dnsapi is
    never in `owned_by`, and records written through it are not flagged when dnsapi is removed.
    A tenant who edits a module's record takes it over, as an administrator's edit does.
- **Audit:** one journald line per request that changes anything: key id, tenant, zone, records
  added and removed, outcome. Never the key. dnshelper records the same change with
  `on_behalf_of` (dnshelper 0.7.0), so its snapshot history and audit line name the tenant too.
- **Blast radius of a compromise:** the attacker gets the module's NS8 identity, which is
  dnshelper's `dnswriter` role limited by its policy rules, plus Traefik `routeadm` on the node.
  The `routeadm` grant is the wider of the two: it covers every route on the node, not only this
  module's. Accepted (2026-11-21), as for every module with a web route.

## Runtime

- One rootless container, the API service. State is written by actions (admin UI) and read by
  the service, which reloads when the files change. The service itself writes only last-used
  times; it keeps rate counters in memory.
  - The operator endpoints that change tenants, assignments and keys call this module's own
    actions through its `selfadm` role (`create-module/10grants`, and `update-module.d/10grants`
    for existing installs), so the actions stay the only writers. The service may make and revoke
    tenant keys only: `create-key` and `revoke-key` refuse operator keys when the caller is the
    module itself. The one exception is `revoke-exposed-key`, for a key the API received over
    plain HTTP (see Security).
  - The container runs with `--network=host`, as the module's uid (`--userns=keep-id`), with
    `state/api/` mounted read-only (the files it reads) and `state/usage/` writable (last-used
    times, activity). It has no NS8 credentials: see "The broker" below.
- **The broker** (decision 2026-11-21, security review; replaces option 2 below). The process that
  faces the internet no longer holds the module's NS8 identity. Those credentials (`agent.env`)
  give the api-server identity `module/dnsapi1`: dnshelper's `dnswriter` on every zone its rules
  grant, this module's own actions, Traefik's `routeadm` for every route on the node (so a
  compromised service could have sent another application's host name, and its users' logins,
  elsewhere) and `node:reader`, plus writes to the module's own Redis keys.
  - A second container, `dnsapi-broker.service`, from the same image (`dnsapi-server broker`),
    as restricted as the API container: the module's uid, no capabilities, read-only, host
    network. It alone mounts `agent.env` (read-only; it reads only `REDIS_USER` and
    `REDIS_PASSWORD`). It listens on a Unix socket (0600) in `%t/dnsapi-broker/`, the user's
    runtime directory, which both containers mount. It reads the dnshelper instance from
    `state/api/runtime.json`, written on the host by `bin/discover-runtime`, and runs tasks with
    the standard-library api-server client the service had before.
  - Why a container and not a host process under `runagent` (tried first, 2026-11-21): on a Rocky
    node, SELinux does not let a container (`container_t`) connect to a socket of an unconfined
    host process, without logging it; turning labelling off for the internet-facing container
    would have given up a real layer. Container to container is allowed (tried with different
    labels too). A loopback TCP port would have needed a second port (`update-module` records a
    new `tcp-ports-demand` but allocates nothing; `node/allocate-ports` needs the `portsadm`
    role) and a shared secret.
  - One JSON request per connection, `{"target": "dnshelper" | "self", "action", "data"}`,
    answered with the task's `{"exit_code", "output", "error"}`, or `{"refused"}` or
    `{"unavailable"}`. It runs only an allowlist: on dnshelper, `list-zones`, `get-records`,
    `list-owners`, `check-propagation`, `list-providers`, and the four writes (`append-records`, `set-records`,
    `delete-records`, `apply-changes`), which must carry `on_behalf_of`, so records written
    through the API never get dnsapi as their owner; on this module, `add-tenant`,
    `update-tenant`, `remove-tenant`, `assign-zone`, `unassign-zone`, `create-key` (never for the
    operator), `update-key` and `revoke-key` (both refuse operator keys for the module itself)
    and `revoke-exposed-key`. It finds dnshelper itself (discovery), so the service no longer
    needs to.
  - A compromised service can then do what its API allows, and nothing else: no Traefik, no other
    action of this module, no other module.
  - Redis needs no credentials to read `cluster/*`, `node/*` and `module/*` (its `default` user,
    checked on the test node), so the host network gives the container nothing the LAN does not;
    it stays, because Traefik's connections then come from loopback, which `X-Forwarded-For`
    handling relies on (through a published port they arrived from the node's LAN address).
- **Calling dnshelper from a long-running process.** `agent.tasks.run()` logs in to the api-server
  (`http://cluster-leader:9311`, `POST /api/login`, then `/api/<agent>/tasks` and `/ws`) with
  `REDIS_USER` / `REDIS_PASSWORD` from the environment. For a rootless module those come from
  `~/.config/state/agent.env` (verified in ns8-core `agent/tasks/apiclient.py` and `runagent`).
  The task then runs with `AGENT_TASK_USER=module/dnsapi1`, so dnshelper's policy applies.
  Options:
  1. A Python service using ns8-core's `agent` package, run with the agent environment.
  2. A service in any language that implements the api-server's task protocol itself.

  Either way, the process that faces the internet holds the module's api-server credentials.
  Splitting it into a front end without credentials and a local back end that holds them is
  possible, but probably not worth it in v1: the blast radius is the same dnswriter role.
  (Superseded by the broker above: with `routeadm` and `node:reader` the blast radius was not the
  same.)

  Decision (2026-11-21): option 2, replaced by the broker the same day. The protocol is three HTTP calls (login, `POST
  /api/<agent>/tasks`, then `GET /api/<agent>/task/<id>/status` until it stops answering 400 or
  404), done with the standard library (`server/dnsapi_server/backend.py`), so the image needs no
  aiohttp and no copy of ns8-core's agent package. Verified on the test node: a container on the
  host network logs in as `module/dnsapi2` with the credentials read from a read-only
  `agent.env` (only `REDIS_USER` and `REDIS_PASSWORD`; the file also sets `PATH` and
  `PYTHONPATH`, so it cannot be an env-file), and dnshelper applies its policy to that caller. The
  service keeps its token in memory and logs in again on 401; it does not share `apitoken.cache`
  with the actions.
- **Latency:** every API call is an NS8 task (process start, dnshelper's Python step, Go helper,
  provider call). Measured on the test node (2026-11-21): login 0.08 s; a `list-zones` task 0.07 s
  to 0.4 s; a request answered from the state 0.03 s. Calls that reach the provider add the
  provider's own time (Hetzner takes 8-15 s). The API is synchronous with a generous upstream timeout, and the docs tell clients
  to allow 60 s.
- **Discovery:** dnshelper through `agent.list_service_providers(rdb, 'dnshelper')`, as every
  consumer does, by install order when there are several. The service cannot read Redis, so
  `bin/discover-runtime` writes `state/runtime.json` (`dnshelper`, `proxies_depth`) before the
  service starts, from `configure-module`, and on `service-dnshelper-changed`, `module-added` and
  `module-removed`. The API answers 503 `dnshelper_missing` while dnshelper is missing.
- **dnshelper older than 0.7.0** returns no `access`/`full` from `list-zones` and has no
  `apply-changes` in `dnswriter`. dnsapi then offers no zones, and the Status page says that
  dnshelper needs updating, rather than guessing what the old rules allow.

## Module plumbing

- Image labels: `org.nethserver.authorizations=dnshelper@any:dnswriter traefik@node:routeadm
  node:reader` (`node:reader` for the node's `get-fqdn`, see [The API host name in
  DNS](#the-api-host-name-in-dns));
  `org.nethserver.tcp-ports-demand=1`; `min-core` at least dnshelper's (3.23.0 for 0.7.0).
  - `@any`, not `@cluster`. A `@cluster` grant follows the cluster's default dnshelper instance.
    ns8-core never picks a new default once that instance is removed, so after a second dnshelper
    is installed and the first removed, a `@cluster` module is granted nothing. This was seen on the
    test node with ns8-automx; see dnshelper's DESIGN.md, Authorization, and its user guide.
  - `@any` grants `dnswriter` on every dnshelper instance. That gives no access by itself: each
    instance's policy is default deny until its administrator adds a rule for dnsapi.
  - With more than one dnshelper, dnsapi uses the one discovery finds first (open question 7).
- State (all in `state-include.conf`): `state/api/tenants.json` (tenants and zone assignments),
  `state/api/keys.json` (key ids, hashes, scopes, allowlists), `state/api/settings.json`; all mode
  0600 and replaced atomically under a lock (`pypkg/dnsapi/state.py`). Not backed up, because they
  are recomputed or unimportant: `state/api/runtime.json`, `state/host-record.json` and
  `state/usage/`. The files the service reads are in `state/api/` (decision 2026-11-21, with the
  broker) so that it can mount them without the rest of the state directory, where `agent.env`
  and `apitoken.cache` are; `update-module.d` and `restore-module` move files from their earlier
  place in `state/`. Secrets are
  never in `state/environment`. A restore brings keys back as they were, so restored keys keep
  working.
- **No key secret is stored anywhere**, Redis included. Decision (2026-11-21): `create-key` takes
  the key id and the SHA-256 of the key, not the key. The API service makes a tenant key's secret
  itself and returns it in its response; the admin UI will make it in the browser; from a shell,
  `runagent -m dnsapi1 create-key --owner operator --scope write` makes one and prints it. That
  is how the first operator key is made. An NS8 task's input and output stay in Redis, so an
  action that returned the key would have left it there.
- Actions (admin UI): `configure-module` (host name, Let's Encrypt, Traefik IP allowlist, rate
  limits, the host record, revoking keys sent over plain HTTP), `get-configuration`, `list-tenants`, `add-tenant`, `update-tenant`, `remove-tenant`,
  `assign-zone`, `unassign-zone`, `list-assignable-zones`, `create-key` (takes the hash, see
  above), `update-key` (label, allowlist, expiry), `revoke-key`, `list-keys`; for the service only, `revoke-exposed-key`. Operator keys are made only by a cluster administrator; the
  API has no endpoint for them.
- Events: on dnshelper's `service-dnshelper-changed`, drop assignments of zones dnshelper no longer
  manages (`has-zone` says `managed: false`). Log it; never fail. Changed (2026-11-21, step 6): a
  zone dnsapi may merely not write in right now is kept. After a restore the module has a new id
  and dnshelper's rules still name the old one, so every zone looks unwritable until the
  administrator updates them; the earlier rule (drop what is not writable) emptied every tenant
  in that window, as shown on the test node. The API refuses an unwritable zone anyway.
- `destroy-module`: nothing to do for the route. Its instance name is `MODULE_ID`, and ns8-traefik's
  own `module-removed` handling deletes the routes whose name starts with it (the kickstart
  template relies on the same). dnshelper's own `module-removed` handling drops the module from its
  record owner index.

## Admin UI (NS8, cluster administrators)

- **Status:** API URL, dnshelper found or not, how many zones are assignable.
- **Tenants:** add, rename, disable; assign zones from the assignable list.
- **API keys:** create (shown once, with a copy button), edit (label, allowed addresses,
  expiry), revoke, last used.
- **Settings:** host name, certificate, Traefik allowlist, rate limits.
- **Activity:** recent changes from the audit lines.

This is not the customer control panel: only cluster administrators can reach it.

Built (2026-11-21), in the style of ns8-dnshelper's and ns8-automx's UIs (`ui/src/mixins/dnsapi.js`
wraps the task events in one promise, as theirs do):
- **Status**: `get-overview` (one task): the API's address, the dnshelper instance or why it is
  unusable, the zones dnsapi may use (in full, and assigned), tenants and keys, above the
  template's module status.
- **Tenants**: add and edit in one dialog (name, enabled, zones as check boxes: the zones dnsapi
  may write in that no other tenant has, "Some records" for a partial one); saving calls
  `add-tenant` or `update-tenant`, then `assign-zone` and `unassign-zone` for what changed.
  Remove asks for the name to be typed, as dnshelper's dialogs do.
- **Keys**: a filter by owner (the Tenants page's "Show keys" opens it filtered), and a create
  dialog with owner, access, label, records (every record, ACME only, or names and types),
  allowed addresses and an expiry day. Decision (2026-11-21): the key is made in the browser
  (`crypto.getRandomValues`, SHA-256 with `crypto.subtle`, the same format as `keys.py`; the
  base32 was checked against Python's), so only its hash reaches `create-key`. It is shown once
  with a copy button and forgotten when the dialog closes.
- **Activity**: `list-activity`. Decision (2026-11-21): the journal is not readable by the module's
  user (checked on the test node: `journalctl --user` and `_UID=` both refuse it), so the changes
  are also written to `state/usage/activity.jsonl` by the service and
  `state/usage/admin-activity.jsonl` by the actions (only for callers other than the module
  itself, so an API change is not listed twice), each trimmed to recent entries and not backed up.
  An entry names the acting key; a key the operator made or revoked is `target_key`.
- **Settings**: the template's fields plus `rate_limit`.
- **Screenshots** (2026-11-22): `ui/dev/` runs the built UI in a browser with faked actions, as
  ns8-automx's and ns8-dnshelper's do, and `screenshots.js` takes the user guide's pictures.
  Fixed from what they showed: a key's expiry, set as the start of a day in UTC, was shown in
  local time, so a day early west of Greenwich (now the UTC day); the "Some records" tag sat
  under its zone; long record values on the Activity page broke after every character.

## Build order

1. Scaffold from ns8-kickstart; route via Traefik; `GET /v1/status`. **Done** (2026-11-21):
   - `server/`: the service, Python standard library only (`http.server`, one thread per
     request), in its own image `dnsapi-server`, built and published beside the module image with
     the same tag and unit-tested inside it by `build-images.sh`. Non-root user, `--read-only`
     container, published on `127.0.0.1:${TCP_PORT}`.
   - `configure-module`: `host`, `lets_encrypt`, `http2https` (removed later, see Security,
     Keys sent over plain HTTP are revoked), `ip_allowlist`, kept in
     `state/settings.json` (backed up). It calls `set-route` before saving, with
     `lets_encrypt_check` when a certificate is requested, so a refused setting changes nothing.
     An omitted field keeps its value. `restore-module` re-runs it to recreate the route.
   - The kickstart smarthost example is removed: dnsapi sends no mail.
   - Tested on the test node (core 3.25.1, ns8-traefik 4.2.5): route, HTTPS redirect, JSON 404,
     allowlist on and off, `update-module` restart keeping the settings. Finding: when the
     allowlist changes twice within a second, Traefik can serve the previous one for about 2 s
     after the second `set-route` returns (seen in 1 of 3 tries). ns8-traefik's reload, not ours,
     and harmless for an admin setting, but a test that changes the allowlist must allow for it.
   - Backup and restore tested on the test node with a local ("cluster" provider) repository:
     the backup holds `environment` and `settings.json`; `restore-module` with `replace: true`
     brought every setting back in a new instance on a new port, `50call-configure-module`
     recreated the route, and removing the old instance removed its route. That confirms
     ns8-traefik's clean-up by `MODULE_ID`, so `destroy-module` needs nothing for the route.
2. Tenants, keys, authentication, rate limits; the read endpoints. **Done** (2026-11-21):
   - Endpoints: `GET /v1/zones`, `GET /v1/zones/{zone}/records` (`name`, `type` filters; records
     another module wrote carry `owned_by`), `GET /v1/zones/{zone}/propagation`, and the operator
     endpoints for tenants, zone assignments and tenant keys. A tenant key gets 404 for any zone
     it does not own and for the operator endpoints; a zone that is not assignable (not `full`)
     is 404 for every key.
   - Authentication: `Authorization: Bearer`, the hash compared in constant time; then expiry
     (401 `key_expired`), the tenant's enabled flag (403 `tenant_disabled`) and the key's
     allowlist (403 `address_not_allowed`). Ten failed authentications from one address in a
     minute give 429 with `Retry-After` for the rest of the minute. A read key may only `GET`.
   - Errors from dnshelper keep their code; `TaskRefused` maps by code (`not_permitted` 403,
     `zone_not_found` 404, `stale`/`conflict` 409, `auth_failed` 502, others 400); a failed step is
     502 `upstream_error`, a task over 150 s 504, the api-server unreachable 503.
   - Tested: 29 unit tests with a fake backend (in the image build), the robot suite on CI nodes
     without dnshelper, and on the test node after `update-module` from step 1: the grants and
     the new state files appeared, keys made from the shell and through the API worked, a
     disabled tenant's key was refused, a self-call making an operator key was refused, and
     `2v6.in` was refused as not assignable (dnshelper has no rule for dnsapi there).
   - Real records, on the test node (2026-11-21): with a temporary "API module (all records)"
     rule for `module/dnsapi2` on `example.com` (ns8-powerdns), removed afterwards. Two tenants:
     the zone assigned to A, and refused to B (409 `zone_assigned`). A's read key listed the zone
     and read its records, with the `type` filter and `propagation`; B's got an empty zone list
     and 404 for the zone; the operator saw the zone with its tenant; `2v6.in` (no rule) was 404
     for both; after unassigning, A got 404. dnshelper logged every call as
     `caller="module/dnsapi2"`. Records read in about 0.47 s (`get-records` and `list-owners` in
     parallel), propagation in 5 s. Not tested on a node: `owned_by`, because the zone had no
     record another module wrote (the unit tests cover it).
3. Write endpoints over `apply-changes`, `append-records`, `set-records`, `delete-records`
   (dnshelper's phase 1: released in 0.7.0). **Done** (2026-11-21):
   - `POST .../changes`, `POST .../records`, `PUT .../rrsets` (mode `rrset`), `DELETE .../records`.
     A write key is checked before the body is read; the body is checked (records at most 100,
     only `name`, `type`, `ttl`, `data`) before anything is sent, and dnsapi builds dnshelper's
     input itself, so a client cannot set `zone` or `on_behalf_of`.
   - `on_behalf_of` is `<tenant>:<key id>`: the zone's tenant, also for an operator key, or
     `operator` for a zone without a tenant.
   - `list-owners` is read before the write, because dnshelper forgets a record's owner when it is
     removed; the warnings come from what dnshelper reports it removes (`changes.remove`), so they
     are the same for a dry run and the write. A write counts twice against the rate limit.
   - Every change, including a refused one, logs one audit line: key, tenant, address, action,
     zone, records added and removed, outcome.
   - Tested on the test node (2026-11-21) on `example.com` (ns8-powerdns), with a temporary full
     rule for `module/dnsapi2`, removed afterwards, and test records only (the zone ended as it
     began, SOA and NS): add; an edit as a dry run (nothing written) and for real; the same edit
     again refused with 409 `stale`; an RRset replaced; a CNAME beside an A record refused (409
     `conflict`); the apex NS refused (403 `forbidden`); a TXT value with spaces kept unquoted; a
     read key refused; a record written by a module (`dnsapi2` itself, without `on_behalf_of`)
     shown with `owned_by` and its deletion warned about, as a dry run and for real; an operator
     key deleting a tenant's records. dnshelper's audit lines carry
     `on_behalf_of="<tenant>:<key id>"`. A write took about 0.8 s (`list-owners`, then the
     write), a read 0.42 s.
   - Finding for dnshelper, not changed here: adding a CNAME where A records exist is refused
     with the message "dnsapi-test-a has a CNAME, which cannot coexist with A records", which
     names the wrong side; the code (`conflict`) is right.
4. ACME DNS-01: key restrictions, zones with partial access, `/v1/acme/present` and `/cleanup`;
   walk-throughs for lego, acme.sh and certbot in the user guide. **Done** (2026-11-21):
   - `restrict` on a key: `create-key` and `bin/create-key --restrict acme` (or patterns with
     `--types`), and `POST /v1/tenants/{id}/keys`. Normalized as dnshelper normalizes rules
     (names lowercase without a trailing dot, `@` for the apex; types uppercase) and matched with
     the same `fnmatchcase`.
   - Assignable zones are those with `access: "write"`; `full` is shown in `GET /v1/zones` and
     `list-assignable-zones`, and the prune on `service-dnshelper-changed` keeps writable zones.
   - `/v1/acme/present` adds the TXT record with TTL 60; `/cleanup` deletes that value. Both run
     through the same path as the other changes (write scope, `restrict`, rate limit, audit line,
     `on_behalf_of`). Basic authentication is decoded only on `/v1/acme/`.
   - Tested on the test node (2026-11-21) on `2v6.in` (Cloudflare), with a temporary dnshelper
     rule for `module/dnsapi2` with the ACME preset only (names `_acme-challenge`,
     `_acme-challenge.*`, TXT), removed afterwards: the zone was assignable with `full: false`;
     an unrestricted tenant key was refused an A record by dnshelper (403 `not_permitted`) and a
     restricted key by dnsapi (403 `outside_restriction`); lego 5.6.0 with `httpreq`, Basic
     authentication and Let's Encrypt's staging CA obtained a certificate for
     `dnsapi-acme-test.2v6.in` in 34 s; `present` and `cleanup` each logged one audit line,
     dnshelper recorded `on_behalf_of`, and no challenge record was left. lego's own
     propagation checks failed twice on that node before Let's Encrypt was asked, for reasons
     outside dnsapi: the LAN resolver answered NXDOMAIN for the zone, and IPv6 to Cloudflare's
     name servers timed out; `--dns.resolvers 1.1.1.1:53 --dns.propagation.disable-ans` solved
     both (in the user guide's troubleshooting). acme.sh was not run; its format is covered by
     unit tests.
5. Admin UI; OpenAPI document; a Blesta/WHMCS-style walk-through (user guide for the
   administrator, README for the portal's developer). **Done** (2026-11-21):
   - The admin UI as described under [Admin UI](#admin-ui-ns8-cluster-administrators).
   - `/v1/openapi.json` (OpenAPI 3.1), served without a key, written by `server/make_openapi.py`;
     a unit test checks that it describes every route with its methods.
   - The user guide's "Connecting a billing or client portal" for the administrator, and the
     README's "Writing a portal integration" for the portal's developer.
   - CI takes screenshots of every page (and of the create-key dialog) when a commit changes
     `ui/`, after a tenant and keys exist; `test-module.yml` follows ns8-automx's.
   - Tested in a browser on the test node (2026-11-21, cluster admin UI, `dnsapi2`): every page;
     adding a tenant, disabling it (its key was then refused with 403 `tenant_disabled`) and
     removing it with its key; making a tenant key in the browser and using it against the API
     (200 on its zones, 404 on the operator endpoints), with its secret found neither in
     `keys.json` nor in the module's task records in Redis; an operator key limited to ACME
     records with an allowed address; revoking it; saving Settings. Fixed from what that showed:
     `NsComboBox` shows the raw value of a fixed choice (`write`, `none`), so fixed lists use
     `cv-select` as dnshelper does; a static `&#10;` placeholder is not decoded; the full API
     address did not fit its Status card (the host name is shown); a missing `type_to_confirm`
     string and "its 1 keys"; a removed tenant showed only its id on the Activity page (its name
     is now recorded with the change).
6. Node test: two tenants, isolation (a tenant key cannot read or write the other tenant's zone),
   a zone dnshelper's policy does not grant, rate limits, key revocation; a certificate from Let's
   Encrypt's staging CA with lego against a zone with only the ACME rule. **Done** (2026-11-21),
   on the master image (`8296e09`) on the test node, through Traefik, with temporary dnshelper
   rules for the test instance (full on `example.com`, the ACME preset on `2v6.in`), removed
   afterwards:
   - Tenants A (`example.com`) and B (`2v6.in`): the zone refused to a second tenant (409
     `zone_assigned`) and an ungranted zone (`desec.2v6.in`) refused (409 `zone_not_assignable`);
     each key's `GET /v1/zones` lists only its own zones, with `full` true and false.
   - Isolation, all 404: A reading, writing and ACME on B's zone; B reading and writing A's; any
     key on the ungranted zone; A on the operator endpoints. B's ACME-restricted key refused an A
     record (403 `outside_restriction`); B's unrestricted key was refused by dnshelper (403
     `not_permitted`); B's reads list only `_acme-challenge` records. A read operator key cannot
     add a tenant.
   - Rate limit 4 per minute: the first records read 200, then 429 with `Retry-After: 59`; another
     key of the tenant unaffected. Revoking a key through the API: 204, then 401 for it, 200 for
     the tenant's other key. Ten failed authentications from one address: 429 with `Retry-After:
     60` for a valid key from it too, ten journal lines.
   - ACME, both against Let's Encrypt's staging CA, with B's ACME-restricted key on the zone with
     only the ACME rule: lego 5.6.0 (`httpreq`, 40 s) and acme.sh 3.1.6 (`acmeproxy`, which
     needs the value echoed, 47 s) each got a certificate; one add and one delete audit line per
     challenge; no record left.
   - Backup and restore over the instance: tenants, assignments, keys and settings came back in
     the new instance, its keys worked and the revoked one stayed revoked; but no zone was
     reachable until dnshelper's rules were changed to the new instance name (user guide, Backup
     and restore). That showed the prune hazard fixed under Module plumbing, Events: the old
     prune emptied both tenants in that state, the new one keeps them.
   - Writes on `example.com` (ns8-powerdns, on node 2). Node 2 was offline during the first pass,
     and every call to the zone ended in 502 `upstream_error` after dnshelper's provider timeout,
     which is the right answer for a DNS host that does not answer. Rerun once node 2 was back,
     with the tenants and a full rule for the restored instance: 17 of 17 passed. Add; an edit as
     a dry run and for real; the same edit again refused (409 `stale`); an RRset replaced; a
     CNAME beside A records (409 `conflict`); the apex NS (403 `forbidden`); a TXT value with
     spaces kept; a read key refused (403); the other tenant's key refused (404) for writes and
     deletes; a module-written record shown with `owned_by` and its deletion warned about, as a
     dry run and for real; an operator key deleting the tenant's records. dnshelper logged every
     write with `on_behalf_of="<tenant>:<key id>"`; a write took 0.8 s, a read 0.42 s; the zone
     ended with its SOA and NS only.
   - Not covered: a Let's Encrypt certificate for the API's own host name (no public DNS record
     for the test host name; done later on a real node, see step 7), and `owned_by` for a record another module wrote through its own
     rule (only a record dnsapi wrote without `on_behalf_of`).
7. The API host name in DNS: the CNAME to the node before `set-route`, the reserved name, the
   Status and Settings pages; a node test with a real Let's Encrypt certificate for the API's
   host name. **Built** (2026-11-21):
   - `pypkg/dnsapi/hostrecord.py`, called by `configure-module` before `set-route`; checked
     against a fake dnshelper for every outcome (added, already there, another CNAME, an A
     record, a record dnsapi cannot read, not managed, no rule, apex, dnshelper not answering,
     the wait succeeding after two checks and giving up after 90 s).
   - `update-module` on an existing instance granted the new `node:reader` (`node/3: reader`).
   - Tested on the test node, DNS only (decision 2026-11-21: `ns8.2v6.in`, the node's host
     name, has no public record, so Let's Encrypt could not validate a CNAME to it), in `2v6.in`
     (Cloudflare) with temporary rules, everything removed afterwards: no rule, `not_permitted`;
     with a rule (write, CNAME), `created`, the CNAME to `ns8.2v6.in.` in the zone, listed in
     dnshelper's owner index as dnsapi's; run again, `ok`; a TXT record dnsapi may not read at
     the name, `conflict` (dnshelper refused the CNAME) and the TXT untouched; a zone dnshelper
     does not manage, `not_managed`; publishing off, `disabled`; `configure-module` succeeded in
     every case. Reserved name, all 403 `reserved_name`: a tenant key holding the zone repointing
     the CNAME, the operator key deleting it, ACME for `_acme-challenge.<host>`; reading it 200
     (with `owned_by`), another `_acme-challenge` name allowed.
   - In the browser: Settings with the switch and the notice; Status with the notice when the
     record needs attention. Found there and fixed: Settings lacked the shared mixin and did not
     render; the not-permitted notice now names the rule's name relative to the zone.
   - Not tested on the test node: the wait for the name servers before a real certificate, and
     the certificate itself, which need the node's host name to resolve publicly and port 80 to
     reach the node. Reported by the operator (2026-11-26) from a real install
     (`ns8.familybrown.org`, 0.1.0-testing.3): `configure-module` published the CNAME for the
     API's host name, and Let's Encrypt issued its certificate through it.
8. Hardening from the security review: the broker (the service holds no NS8 credentials), HTTPS
   only, concurrency limits, the IPv6 /64 throttle; the service's files moved to `state/api/`.
   **Done** (2026-11-21):
   - Unit tests: 67, including the broker's allowlist over its socket (allowed: dnshelper's reads
     and its writes with `on_behalf_of`, the tenant and key actions; refused: writes without
     `on_behalf_of`, `set-policy`, `add-zone`, `has-zone`, `configure-module`, operator keys,
     Traefik, the node), the socket's mode 0600, `https_required`, the per-key, task and
     connection caps, and the /64 throttle.
   - Test node (Rocky 9, SELinux enforcing): `update-module` moved the four files into
     `state/api/` and enabled the broker. Inside the API container: no `agent.env`, no `REDIS_`
     variable, all capability sets empty, `NoNewPrivs` 1, mounts `state/api` (ro), `state/usage`
     and the broker's directory only; the api-server refuses it (401). From inside it, the
     broker ran `list-zones` and refused `set-policy`, a write without `on_behalf_of`,
     `configure-module`, an operator key and Traefik's `set-route`. Through Traefik: adding a
     tenant (through the broker) 201, the zones 200; plain HTTP 403 `https_required`, also with
     a forged `X-Forwarded-Proto: https`, which Traefik replaces (the VERIFY item above), and the
     key id logged; `/v1/status` over HTTP still 200.
   - Found on the node and fixed: the first broker, a host process under `runagent`, could not be
     reached from the container (SELinux; see The broker), so it is a container; a file moved
     into `state/api/` by renaming kept a private SELinux label from an earlier mount and the
     container could not read it, so the moves write new files.
   - Restore: a restore runs the image recorded in the backup (`IMAGE_URL`), here `dnsapi:latest`,
     the build before this step, so it came back with the old layout and old code; updating it
     then moved its files and its restored tenants were served. `restore-module/40move_api`
     covers restoring an old backup once `latest` is this code.
   - Debian 13 node (node 2, AppArmor enabled, its own Traefik, dnshelper on node 3): an instance
     installed from master with a tenant and an operator key, then `update-module` to this
     branch: the four files moved into `state/api/`, both units enabled and active, the key made
     before the update still worked. Inside the API container the same as on Rocky (no
     `agent.env`, no `REDIS_` variable, empty capability sets, `NoNewPrivs` 1, the same three
     mounts); from inside it the broker ran `list-zones` on dnshelper across nodes and refused
     `set-policy`, `configure-module` and Traefik, and the api-server answered 401. Through
     node 2's Traefik: a tenant added through the broker 201, the zones 200, plain HTTP 403
     `https_required` (also with a forged `X-Forwarded-Proto`), `/v1/status` over HTTP 200. Podman
     on that node applies no AppArmor profile to either container, so the socket needs no rule.
   - Not tested on a node: the concurrency caps and the /64 throttle (unit tests only; the node
     has no working IPv6).
   - Added after 0.1.0-testing.1 (2026-11-22, issue #12): keys sent over plain HTTP are revoked,
     and the route no longer redirects (see Security). Unit tests: 72, covering a real key (an
     operator key), a real id with the wrong secret, Basic on `/v1/acme/` and not elsewhere, the
     switch off, and the revocation failing; the robot suite covers it through Traefik.
   - Tested on the test node (2026-11-23, `dnsapi4` on node 3, Rocky 9, ns8-traefik 4.2.5),
     after `update-module` from 0.1.0-testing.1: the new grant appeared in `selfadm`;
     `30route` ran `configure-module`, which dropped `http2https` from `settings.json` and left
     the route without the redirect; `revoke_cleartext_keys` read as on. Through Traefik over
     plain HTTP, all 403 `https_required`: a key with a real operator key's id and the wrong
     secret revoked nothing (logged as not a valid key; the real key still 200 over HTTPS); an
     operator key was revoked (then 401 over HTTPS, the other operator key 200); an ACME tenant
     key sent with Basic was not read on `/v1/zones` and was revoked on `/v1/acme/present`; with
     the switch off, a key was only logged and kept working. Each revocation gave the action's
     and the service's audit lines, an Activity entry and an `exposed_keys` entry in
     `get-overview` (with the tenant's name). The test keys and tenant were removed afterwards.
     Not tested on the node: the Status page's notice (checked in the `ui/dev` harness).
9. Editable keys (2026-11-25, see Concepts, API key): `update-key`, `PATCH
   /v1/tenants/{id}/keys/{key id}`, an Edit dialog on the Keys page that shows owner, access and
   records read-only, and the changed fields on the Activity page.
   - Unit tests: 77. The API: a PATCH changes the label and allowlist, the new allowlist applies
     at once, the Activity entry carries the old and new values; `scope`, `restrict`, `owner` and
     `hash` are refused (400 `not_editable`), an empty body is 400; another tenant's key, an
     unknown and a revoked key are 404, and a tenant key cannot reach the endpoint. The broker
     passes `update-key`.
   - The action, run against a scratch state directory: an expired key given a later expiry
     (with an offset, normalized to UTC) and a duplicated allowlist entry; a change to the same
     value records nothing; a bad address and a past expiry refused; an operator key refused for
     the module and changed by an administrator; a revoked and an unknown key refused.
   - In the `ui/dev` harness: the revoked key has no Edit item; the dialog for the expired key
     shows its fields and the "has expired" notice; a bad address is refused under the field;
     a later expiry and new addresses brought it back to the active keys, with "Changed".
   - The robot suite: through Traefik, a tenant key's allowlist and label changed (the key then
     refused from the node with 403 `address_not_allowed`, then accepted again), `scope` refused,
     and an operator key's label changed with `api-cli`.
   - Tested on the test node (2026-11-25, `dnsapi4` on node 3, Rocky 9, ns8-traefik 4.2.5), after
     `update-module` from an earlier branch image: `update-key` appeared in `selfadm`. With a
     temporary operator key, tenant and read key, through Traefik: the allowlist changed to
     `192.0.2.0/24` refused the key (403 `address_not_allowed`) on the next request, and changed
     back accepted it; an expiry 40 s ahead, then 401 `key_expired` once it passed, then a later
     expiry and the key worked again; a past expiry 400 `invalid_expiry`, a bad address 400
     `bad_ip_address`, `scope` and `restrict` 400 `not_editable`, an empty body 400; the tenant
     key on the endpoint, the operator key's id and another tenant's key all 404. From inside
     the API container, the broker ran `update-key` for the tenant key and the action refused
     the operator key (`not_permitted`); `api-cli` changed the operator key's label and
     allowlist. A revoked key: 404 through the API, `key_revoked` from the action. Each change
     gave the action's and the service's audit lines and an Activity entry with the old and new
     values. Removed afterwards: the tenant with its key; the operator key is revoked, and
     listed as such. The operator then tried the Edit dialog in the cluster admin UI on the
     same instance; it worked as expected.
   - Found on the node and fixed: the service's journal lines for key actions (`create-key`,
     `update-key`, `revoke-key`) had `key=` twice, the acting key and then the key acted on.
     The second is now `target_key=`, as it already was on the Activity page.
10. The provider list (2026-11-25, see [Providers](#providers)): `GET /v1/providers`, and in
    dnshelper `list-providers` in `dnsreader`.
    - Unit tests: 81. The endpoint for an operator key and a restricted one, only the documented
      keys passed on, the cache, 404 for tenant keys without calling dnshelper, 503
      `not_granted`; the broker passing `list-providers`, still refusing `add-credential` and
      `list-provider-zones`, and telling an api-server 403 apart from it being unreachable. The
      robot suite: 404 for a tenant key, 503 `dnshelper_missing` for the operator key (CI has no
      dnshelper).
    - Test node (2026-11-25, `dnsapi4` on node 3, Rocky 9, through Traefik), after
      `update-module` to the branch image: with dnshelper 0.7.0, 503 `not_granted` (the broker
      logged the api-server's 403) while `GET /v1/zones` still answered 200. Then `dnshelper4`
      updated to dnshelper's branch image (the operator's choice: left there until 0.7.1):
      `update-module.d/10grants` put `list-providers` in `dnsreader` and `dnswriter`, and the
      zones were all still there. `GET /v1/providers` 200 with 18 providers and only the
      documented keys (Cloudflare's `api_token` and `zone_token` marked secret); a second call
      ran no dnshelper task (the cache); a tenant key 404; the test keys revoked afterwards
      (then 401 `key_revoked`).
11. CI with dnshelper (2026-11-25, the operator's request: the CI screenshots showed only
    "dnshelper is not available", and the node tests above were by hand). The robot suite installs
    dnshelper partway through, after the cases that check dnsapi without it.
    - dnshelper is a pinned release (`DNSHELPER_IMAGE`, 0.7.1, the first with `list-providers`
      for modules), not `latest`, so a change on dnshelper's master cannot fail dnsapi's CI. It is
      raised by hand when dnsapi needs more.
    - Its DNS host is a throwaway PowerDNS on the node's loopback, as in dnshelper's own suite,
      with four zones: the "API module (all records)" rule on two, the ACME preset on one, no
      rule on the last. No real DNS host or credential, as for every robot test.
    - The API host name is in one of those zones, so the host record is published and the
      reserved name can be tested. A record is marked as `mail1`'s in dnshelper's owner index
      (as dnshelper's suite does) for `owned_by`.
    - Covered: everything step 6 tested by hand except rate limits, backup and restore, and
      Let's Encrypt; plus the host record, the providers, the prune when dnshelper drops a zone,
      and dnsapi finding dnshelper added and removed. Not covered: `propagation`, which asks a
      zone's public name servers.
12. Phase 2 (see [Phase 2](#phase-2-domains-added-through-the-api-design-not-built)): dnshelper's
    delegated zones first, then hosting, then one-shot on top. Then phase 3 (PowerDNS hosting), as
    needed.

## Further hardening (not built)

The security review of 2026-11-21 listed ten items; four were built in step 8 (the broker, HTTPS
only, concurrency limits, the IPv6 /64 throttle). The rest, kept here for later:

1. **Tenant isolation depends on dnsapi's own check.** For a zone under dnshelper's "API module
   (all records)" preset, dnshelper allows dnsapi every record, so a bug in dnsapi's tenant check
   is the only thing between two customers; dnshelper protects only the zones it did not grant.
   - A test that runs every route and method with every kind of key (operator, tenant, read,
     write, restricted, expired, disabled tenant) against every kind of zone (own, another
     tenant's, unassigned, not granted, partial) and checks each answer against a table.
   - The operator key reaches every customer. The UI could warn when an operator key has no
     allowed addresses, or require them.
2. **Container limits.** Both containers already run read-only, as the module's uid, with no
   capabilities and `no-new-privileges`. Not set: memory and process-count limits (`--memory`,
   `--pids-limit`). The host network stays (see The broker: it is what makes Traefik's
   connections come from loopback).
3. **A request limit in Traefik.** The service caps connections, requests per key and tasks
   (step 8), but every connection still reaches it. A Traefik rate-limit middleware on the route
   would refuse floods before they do; ns8-traefik's `set-route` has no such option, so this
   needs a change there.
4. **Input checks of dnsapi's own.** dnsapi passes record names and values to dnshelper, which
   validates them. dnsapi could also refuse control characters and newlines, and cap the nesting
   depth of JSON bodies, before anything reaches dnshelper or the logs.
5. **Every host name served by the cluster could be reserved.** Only the API's own host name and
   its `_acme-challenge` name are reserved now. If another name served on the cluster (the node's
   host name, webmail, other applications) is in a zone assigned to a tenant, that tenant can
   repoint it or obtain a certificate for it. dnsapi could treat every host name in Traefik's
   routes as reserved (needs read access to the routes of every node).
6. **The audit trail to trust.** A compromised API service could rewrite
   `state/usage/activity.jsonl`, and so the Activity page. The journal lines and dnshelper's own
   audit log are out of its reach. The user guide says so (2026-11-22); nothing else is done.
7. **Updates of the service image.** `server/Containerfile` pins an exact Python image
   (`python:<version>-slim-trixie`). Renovate's `dockerfile` manager reads it and opens a PR for
   each new image (the first, #18, moved from 3.14.10 to 3.15.1 on 2026-11-25); its CI runs the
   unit tests inside the new image and the robot suite on it. The Trivy scan in
   `publish-images.yml` runs only for stable releases and by hand.

## Open questions

1. ~~Name.~~ Decided 2026-11-21: `dnsapi` (repository `ns8-dnsapi`).
2. ~~Records owned by other modules.~~ Decided 2026-11-21: allowed, with a warning (see
   Security).
3. ~~`routeadm` is wide.~~ Decided 2026-11-21: granted, as for every module with a web route. The
   module calls `set-route` from `configure-module` and only for its own instance name; the
   blast-radius note under Security stays.
4. **Zone assignment.** Is one zone per tenant enough, or do sub-zones or shared zones need
   restrictions by name pattern (for example tenant A gets `shop.example.com` in the operator's
   zone)? v1: whole zones only.
5. **Tenant-level restrictions** (record types, names), like dnshelper's policy rules. Decided
   2026-11-21 for keys, not tenants: a key's `restrict` (see
   [ACME DNS-01 validation](#acme-dns-01-validation)). Restrictions on a whole tenant: none in v1.
6. **Customer control panel:** this module's own UI with OIDC, or a separate module? Deferred.
7. **More than one dnshelper instance.** Use the first one discovery finds, or let the
   administrator choose one in Settings? v1: the first, shown on the Status page.
