# ns8-dnsapi

An HTTPS API for [NethServer 8](https://github.com/NethServer/ns8-core) that lets software
outside the cluster manage DNS records: a billing or client portal (Blesta, WHMCS, the operator's
own) acting for the operator's customers, customers' own scripts, and systems that validate
certificates with ACME DNS-01, including ones the internet cannot reach. It holds no DNS provider
code: every read and change goes through [ns8-dnshelper](https://github.com/danb35/ns8-dnshelper)
(0.7.0 or later), limited by the access rules its administrator grants this module. See
[DESIGN.md](DESIGN.md) for the design, the decisions and what was tested on a node, and
[TERMS.md](TERMS.md) for what data goes where.

**Administering it?** The [user guide](docs/USER-GUIDE.md) explains publishing the API, letting
it use zones, tenants and keys, connecting a portal, setting up ACME clients, and what the errors
mean. This README is for people who build, test or work on dnsapi, and for developers who write a
client for its API.

- [Status](#status)
- [Install](#install)
- [Actions](#actions)
- [API](#api)
- [ACME endpoints](#acme-endpoints)
- [Writing a portal integration](#writing-a-portal-integration)
- [How it fits together](#how-it-fits-together)
- [Using dnshelper](#using-dnshelper)
- [Backup and restore](#backup-and-restore)
- [Development](#development)
- [Testing](#testing)

## Status

[0.1.0](https://github.com/danb35/ns8-dnsapi/releases/tag/0.1.0) is the latest release, the
first stable one, listed in the [danb35 software repository](https://github.com/danb35/ns8-repomd).
Steps 1 to 11 of DESIGN.md's build order are done: the API behind Traefik on its
own host name; tenants, keys, authentication and rate limits; reading and changing records; ACME
DNS-01; the admin UI (Status, Tenants, Keys, Activity, Settings) and the OpenAPI document; a full
node test; the API's host name published through dnshelper; and the hardening from a security
review (the broker, HTTPS only, concurrency limits); editable keys; the provider list; and CI
that tests against a real dnshelper. Phase 2, adding customers' domains through the API, is
built on this branch and tested on a node: it needs dnshelper 0.8.0, which is not released
yet. Hardening that was considered and not built is listed in DESIGN.md, "Further hardening".

## Install

dnshelper 0.7.0 or later, from NethForge, must be installed for dnsapi to reach any zone (NS8 has no dependencies
between modules, so this is not enforced at install). `GET /v1/providers` needs dnshelper 0.7.1.

From the software center: add the repository `https://danb35.github.io/ns8-repomd/` (Settings →
Software repositories) and install dnsapi. From a shell on the leader node:

    add-module ghcr.io/danb35/dnsapi:0.1.0 1
    api-cli run module/dnsapi1/configure-module --data '{"host": "dnsapi.example.com", "lets_encrypt": true}'
    runagent -m dnsapi1 create-key --owner operator --scope write --label "first key"

`ghcr.io/danb35/dnsapi:latest` is the master branch, which may be ahead of the last release. The
user guide has the details. To remove an instance: `remove-module --no-preserve dnsapi1`.

## Actions

The schemas are in `imageroot/actions/<action>/validate-*.json`.

| Action | Input | |
|---|---|---|
| `configure-module` | `host`, `lets_encrypt`, `ip_allowlist`, `rate_limit`, `publish_host_record`, `revoke_cleartext_keys` (`http2https` is ignored: the route never redirects) | publish the API, adding the host name's CNAME to the node through dnshelper first when it can; an omitted field keeps its value |
| `get-configuration` | none | the settings, and `host_record`: what configure-module found about the host name's DNS record |
| `list-tenants`, `add-tenant`, `update-tenant`, `remove-tenant` | `name`, `enabled`, `id` | tenants; removing one removes its keys |
| `assign-zone`, `unassign-zone` | `tenant`, `zone` | a zone dnshelper lets dnsapi write in; at most one tenant per zone |
| `list-assignable-zones` | none | those zones, with `full` and their tenant |
| `create-key` | `id`, `hash`, `owner`, `scope`, `label`, `allowlist`, `expires`, `restrict` | stores a key from its SHA-256: the action never sees the key |
| `update-key` | `id`; any of `label`, `allowlist`, `expires` | changes only those (a field left out keeps its value) and records `modified`; owner, scope and `restrict` are fixed; a revoked key cannot be changed; an expired key given a later expiry works again |
| `revoke-key`, `list-keys` | `id`; optional `owner` | a revoked key keeps its record, marked `revoked` (time) and `revoked_reason` (`revoked` or `plain_http`); `list-keys` returns every key with its `status` (`active`, `expired`, `revoked`) |
| `revoke-exposed-key` | `id`, `address` | called by the API service for a valid key it received over plain HTTP; revokes operator keys too |
| `get-overview` | none | what the Status page shows: the API's address, the dnshelper instance, how many zones, tenants and keys, and `exposed_keys`: keys revoked in the last 7 days for being sent over plain HTTP |
| `list-activity` | optional `limit` | the most recent changes, made through the API or the actions, newest first |

`bin/create-key`, run with `runagent -m dnsapi1`, makes a key, stores its hash and prints it: it
is how the first operator key is made. The API service calls the tenant and key actions itself
(see [How it fits together](#how-it-fits-together)); it cannot make, change or revoke operator keys.

## API

Base URL `https://<host>/v1`. Plain HTTP is not redirected: it is refused with 403
`https_required`, and a valid key sent over it is revoked at once (unless the administrator turned
that off), so a client configured with `http://` loses its key on the first request.
The OpenAPI 3.1 document is at `/v1/openapi.json`, without a key (`server/make_openapi.py` writes
it; a unit test checks that it describes every route). Send the key as `Authorization: Bearer
<key>`; keys look like `dnsapi_<8 hex>_<52 base32>`. Bodies are JSON, at most 1 MB. A read key may only `GET`. Errors
are `{"error": {"code", "message", "field"}}`:

| Status | Codes |
|---|---|
| 400 | `invalid_request`, `invalid_json` (with `field`), `invalid_zone`, `unknown_provider`, `unknown_field`, `required` (a credential field), and dnshelper's `invalid_request`, `unsupported` |
| 401 | `missing_key`, `invalid_key`, `key_expired`, `key_revoked` |
| 403 | `insufficient_scope`, `tenant_disabled`, `address_not_allowed`, `restricted_key`, `outside_restriction`, `reserved_name` (the API's own host name and its `_acme-challenge`), `https_required` (the request came over plain HTTP); dnshelper's `not_permitted`, `forbidden` (apex NS, SOA) |
| 404 | `not_found`, `zone_not_found`, `tenant_not_found`, `key_not_found` |
| 405 | `method_not_allowed` |
| 409 | `stale` (a record to remove is gone), `conflict` (e.g. a CNAME beside other records), `zone_assigned` (another tenant has the zone), `zone_not_assignable` (dnshelper does not let dnsapi write in it), `zone_already_configured` (dnshelper manages the domain already), `zone_overlaps` (it is inside or around a zone dnsapi did not add) |
| 413 | `body_too_large` |
| 429 | `rate_limited`, `too_many_concurrent` (more than 4 requests of one key at once), with `Retry-After` |
| 502 | `upstream_error` (the DNS host failed), dnshelper's `auth_failed` (the DNS host refused its credentials), `cleanup_failed` (one-shot: the credentials are still in dnshelper and will be removed by a later clean-up) |
| 503 | `dnshelper_missing`, `not_granted` (dnshelper does not let dnsapi run what the request needs: dnshelper is too old for it), `unavailable`, `busy` (too many requests at once for the whole service) |
| 504 | `upstream_timeout` |

A tenant key gets 404, not 403, for a zone it does not own and for the operator endpoints, so a
key cannot be used to find out which zones are managed.

| Request | Key | |
|---|---|---|
| `GET /v1/status` | none | liveness only |
| `GET /v1/zones` | any | `{"zones": [{"zone", "provider", "full", "tenant", "hosted"}]}`: the key's zones (operator: every assignable zone; `tenant` and `hosted` only for operator keys) |
| `POST /v1/zones` `{"zone", "provider", "credentials", "tenant", "dry_run"}` | operator | add a customer's domain with its DNS host and credentials, kept in dnshelper; see [Domains added through the API](#domains-added-through-the-api) |
| `DELETE /v1/zones/{zone}` | operator | remove a domain added with `POST /v1/zones` |
| `POST /v1/zones/provision` `{"zone", "provider", "credentials", "records", "dry_run"}` | operator | write records into a customer's domain without keeping its credentials |
| `GET /v1/zones/{zone}/records?name=&type=` | any | the records; those another module wrote carry `owned_by` |
| `GET /v1/zones/{zone}/propagation?name=&type=` | any | what the zone's name servers answer, compared with the DNS host |
| `POST /v1/zones/{zone}/changes` `{"remove", "add", "dry_run"}` | write | remove exact records and add others as one change; refused as a whole with 409 `stale` if a record to remove is no longer there |
| `POST /v1/zones/{zone}/records` `{"records", "dry_run"}` | write | add records; never removes any |
| `PUT /v1/zones/{zone}/rrsets` `{"records", "dry_run"}` | write | make the given records the only ones of each name and type |
| `DELETE /v1/zones/{zone}/records` `{"records", "dry_run"}` | write | remove the matching records (`name` required; a `type`, `ttl` or `data` left out matches anything) |
| `GET`, `POST /v1/tenants` | operator | list, add (`{"name"}`) |
| `GET`, `PATCH`, `DELETE /v1/tenants/{id}` | operator | read, change (`{"name", "enabled"}`), remove with its keys |
| `PUT`, `DELETE /v1/tenants/{id}/zones/{zone}` | operator | assign, unassign a zone |
| `GET`, `POST /v1/tenants/{id}/keys` | operator | list (`?revoked=true` to include revoked keys; each key has a `status`: `active`, `expired` or `revoked`), make a tenant key (`{"scope", "label", "allowlist", "expires", "restrict"}`); only the response holds the key |
| `PATCH /v1/tenants/{id}/keys/{key id}` | operator | change a tenant key's `label`, `allowlist` or `expires` (fields left out keep their value; any other field is 400 `not_editable`); what a key reaches (`scope`, `restrict`) is fixed |
| `DELETE /v1/tenants/{id}/keys/{key id}` | operator | revoke |
| `GET /v1/providers` | operator | `{"providers": [{"name", "label", "notes", "types", "fields": [{"name", "label", "secret", "required", "default"}]}]}`: the DNS hosts dnshelper supports, the credential fields each one takes and the record types it supports (cached 10 minutes; needs a dnshelper newer than 0.7.0, otherwise 503 `not_granted`) |
| `POST /v1/acme/present`, `/v1/acme/cleanup` | write | see [ACME endpoints](#acme-endpoints) |

A restricted operator key (`restrict`) reaches the zones and `GET /v1/providers`, but not the
tenant and key endpoints.

**Records** use dnshelper's shape, `{"name", "type", "ttl", "data"}`: `name` relative to the zone
(`@` for the apex), `data` in zone-file form without quotes (TXT is one plain string of any
length; MX is `"10 mail.example.com."`; SRV is `"priority weight port target"`), `ttl` optional.
At most 100 records per request. dnshelper refuses invalid results and never changes the apex NS
and SOA records; which types and values work depends on the DNS host (dnshelper's README,
"Providers").

**A change** answers `{"zone", "dry_run", "changes": {"add", "remove"}, "warnings", "records"}`.
To edit a record, remove the old value and add the new one in one `changes` request: if someone
changed it meanwhile, the request is refused with `stale` instead of adding a second record. With
`"dry_run": true` nothing is written, and the answer is the same.

**Records written by other modules.** Some records were written by an NS8 module, for example the
mail server's MX or DKIM record; `GET .../records` marks them `"owned_by": ["mail1"]`. A tenant
may change them, but the module may write them again, so a change that removes one carries

    "warnings": [{"code": "owned_by_module", "record": {...}, "modules": ["mail1"], "message": "..."}]

A portal should send a dry run first, show the warnings, and apply only when the user confirms.

**Time.** Each call that reaches the DNS host is an NS8 task plus the host's own time: about 0.4 s
for a read and 0.8 s for a change on the test node, and 8 to 15 s per call on Hetzner. Allow 60 s.
Every call to dnshelper counts against the key's rate limit (a records read or a change counts
twice).

    curl -H "Authorization: Bearer $KEY" https://dnsapi.example.com/v1/zones
    curl -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
        -d '{"remove": [{"name": "www", "type": "A", "data": "192.0.2.1"}],
             "add": [{"name": "www", "type": "A", "data": "192.0.2.2"}], "dry_run": true}' \
        https://dnsapi.example.com/v1/zones/example.com/changes

## Domains added through the API

The operator's portal can add a customer's domain with the customer's own DNS host and
credentials, instead of the administrator adding it in dnshelper (DESIGN.md, Phase 2). This needs
dnshelper 0.8.0 or later, with dnsapi listed in its **Delegate modules** setting; otherwise these
requests answer 403 `not_permitted` (not listed) or 503 `not_granted` (dnshelper too old).
Operator keys without `restrict` only; a tenant key gets 404.

- `credentials` holds the DNS host's fields, by the names `GET /v1/providers` gives, for example
  `{"api_token": "..."}`. dnsapi checks the names and the required fields, then has dnshelper
  check that they reach the zone at the DNS host before anything is stored (a refusal is 502
  `auth_failed`). They are passed to dnshelper and never stored or logged by dnsapi.
- **Hosting**, `POST /v1/zones`: the domain and its credentials stay in dnshelper, and the zone is
  managed through the other endpoints like any other. `tenant` assigns it in the same request.
  `dry_run` only checks the credentials. Answers 201 `{"zone", "provider", "tenant", "full",
  "hosted", "dry_run"}`. `DELETE /v1/zones/{zone}` removes it (and its credentials) from
  dnshelper again; the records stay at the DNS host. A zone not added this way is 404.
- **One-shot**, `POST /v1/zones/provision`: for a domain that only needs some records written,
  such as for transactional mail. dnsapi adds the credentials and the zone, writes `records` (at
  most 100, as `POST .../records` does), and removes both again, whatever happened. Answers 200
  `{"zone", "dry_run", "changes", "records"}`. A `dry_run` shows what would be written. If the
  removal fails, the answer is 502 `cleanup_failed`, and dnsapi retries within minutes.
- A domain dnshelper manages already is 409 `zone_already_configured`; one inside or around a
  zone dnsapi did not add is 409 `zone_overlaps`.
- Removing a tenant unassigns its hosted zones and keeps them, for another tenant or `DELETE
  /v1/zones/{zone}`.
- dnshelper's administrator sees these zones and credentials tagged "Delegated to dnsapi1", and
  can remove them or take them over; a taken-over zone is no longer `hosted`, and `DELETE` gives
  404.

Ask customers for credentials limited to their zone, and with an expiry, where the DNS host offers
them: dnshelper holds hosted credentials for as long as the domain is hosted.

## ACME endpoints

`POST /v1/acme/present` and `POST /v1/acme/cleanup` take `{"fqdn": "_acme-challenge.www.example.com.",
"value": "<token>"}`: the protocol of lego's `httpreq` provider, acme.sh's `acmeproxy` and
Caddy's `acmeproxy` DNS module (checked against their sources, and each run against dnsapi; see DESIGN.md). They accept HTTP Basic authentication with the
key as the password and any user name, as those clients send it; nowhere else does.

- The `fqdn` must start with the label `_acme-challenge`; the trailing dot is optional. The zone
  is the longest of the key's zones that contains it.
- `present` adds the TXT value with a TTL of 60 and keeps any other value at that name;
  `cleanup` removes only that value. They run as any other change (write scope, `restrict`, rate
  limit, audit line).
- The answer is 200 with `{"fqdn", "value", "zone", "changes"}`, `fqdn` and `value` exactly as
  sent: acme.sh needs the value echoed, and Caddy's module refuses any other status or a changed
  `fqdn` or `value`.
- lego's `RAW` mode is not supported. A CNAME on `_acme-challenge` pointing to a name that does
  not start with `_acme-challenge` is refused (lego sends the CNAME's target).

The user guide shows the lego, acme.sh, Caddy and certbot setups.

## Writing a portal integration

A billing or client portal (a Blesta or WHMCS module, for example) holds one operator key and acts
for whichever customer is logged in. The administrator gives it the key and the API's address
(user guide, "Connecting a billing or client portal").

- **Customer signs up**: `POST /v1/tenants` `{"name"}`, and store the returned `id` with the
  customer. For each of their domains, `PUT /v1/tenants/{id}/zones/{zone}`; 409
  `zone_not_assignable` means the administrator has not let dnsapi use that zone yet, 409
  `zone_assigned` that another tenant has it.
- **Customer opens the DNS page**: `GET /v1/zones/{zone}/records`. Check first that the zone is
  the customer's: the operator key reaches every zone, so the portal must not trust a zone name
  from the browser. `GET /v1/zones` gives each zone's tenant. Show records with `owned_by` as
  managed by that module.
- **Customer edits a record**: send the old and the new value as `remove` and `add` to `POST
  .../changes` with `"dry_run": true`. If the answer has `warnings`, show them and ask for
  confirmation; then send the same request without `dry_run`. On 409 `stale`, someone changed the
  record meanwhile: reload and let the customer try again.
- **Customer adds or deletes records**: `POST .../records`, `DELETE .../records` (exact `data`
  to delete one value of several), with a dry run first when warnings matter.
- **Waiting for a change to be visible**: `GET .../propagation?name=&type=`.
- **Which DNS hosts dnshelper works with**: `GET /v1/providers`, for example to tell a customer
  whether their DNS host can be used, which record types it takes, and which credential fields to
  ask for. It is dnshelper's own list, so a DNS host added to dnshelper appears there without a
  change to the portal.
- **Customer adds a domain at their own DNS host**: ask for the fields `GET /v1/providers` lists,
  then `POST /v1/zones` with `tenant` (a `dry_run` first checks the credentials). For records
  written once, `POST /v1/zones/provision` instead. See [Domains added through the
  API](#domains-added-through-the-api).
- **Customer scripts their own DNS**: `POST /v1/tenants/{id}/keys` makes a tenant key; show it
  once. Change its label, allowed addresses or expiry with `PATCH .../keys/{key id}`; revoke it
  with `DELETE .../keys/{key id}`. A key that should reach more (write instead of read, other
  records) is a new key.
- **Customer leaves**: `DELETE /v1/tenants/{id}` removes the tenant and its keys and unassigns its
  zones; no record changes. Remove the domains added for it with `DELETE /v1/zones/{zone}`.

Set a timeout of at least 60 s, and back off on 429 for `Retry-After` seconds. Every request is
listed on the administrator's Activity page with the operator key and the tenant; dnshelper's
history names the tenant.

## How it fits together

- **Two images.** `dnsapi` is the NS8 module (actions, systemd units, UI); `dnsapi-server`
  (`server/Containerfile`) is the API service, Python standard library only. They are published
  together with the same tag.
- **The service** runs rootless with `--network=host`, listens on `127.0.0.1:${TCP_PORT}`, and
  Traefik routes the API host name to it. It runs as the module's uid with no capabilities,
  mounts only `state/api/` read-only, `state/usage/` and the broker's socket directory, and
  **holds no NS8 credentials**.
- **The broker** (`dnsapi-broker.service`, `server/dnsapi_server/broker.py`) is a second
  container from the same image, as restricted as the first, and the only one with the module's
  credentials (`agent.env`, read-only). For the service, over a Unix socket both mount, it runs
  only dnshelper's reads, its four writes (only with `on_behalf_of`), and this module's tenant
  and key actions (never an operator key). The tasks are three HTTP calls to the api-server
  (`apiclient.py`) and run as `module/dnsapi1`, so dnshelper's policy applies. A host process
  would have been simpler, but SELinux does not let a container connect to one.
- **Limits**: at most 64 connections, 4 requests per key and 16 NS8 tasks at once; failed
  authentications counted per IPv4 address or IPv6 /64.
- **Only actions write state.** The operator endpoints that change tenants, assignments and keys
  call this module's own actions through its `selfadm` role, granted in
  `create-module/10grants` (and `update-module.d/10grants`). A key's secret is made by the caller
  and only its hash reaches an action, so no secret is ever kept in Redis.
- **State** (`pypkg/dnsapi/state.py`): `api/settings.json`, `api/tenants.json`,
  `api/keys.json`, all 0600, replaced atomically under a lock; `api/runtime.json`, written by
  `bin/discover-runtime` (Traefik's `PROXIES_DEPTH`); `usage/last-used.json`, written by the
  service. An update or a restore moves them from their place before the broker, `state/`.
  The service rereads a file when its modification time changes. The Activity page reads
  `usage/activity.jsonl` (the service's changes) and `usage/admin-activity.jsonl` (the actions'
  changes not made by the service), each trimmed to recent entries: the module's user cannot read
  the journal.
- **Admin UI** (`ui/`): keys are made in the browser (`mixins/dnsapi.js`, `crypto.getRandomValues`
  and SHA-256 with `crypto.subtle`), and only their hash is sent to `create-key`.
- **The client address** is the last `X-Forwarded-For` entry, or `PROXIES_DEPTH` entries left of
  it when Traefik has trusted proxies. Traefik replaces a header a client sends itself.
- **Events**: `service-dnshelper-changed`, `module-added` and `module-removed` rerun discovery;
  the first also drops assignments of zones dnshelper no longer manages. A zone dnsapi may merely
  not write in right now is kept: after a restore, dnshelper's rules still name the old instance.
- **Route**: `configure-module` calls Traefik's `set-route` with the instance name `MODULE_ID`,
  before saving anything; ns8-traefik removes the route with the module.
- **The host name's record** (`pypkg/dnsapi/hostrecord.py`): before `set-route`, `has-zone` with
  the CNAME (rules only), `get-records` at the name, `append-records` of a CNAME to the node's
  `get-fqdn` (role `node:reader`) when nothing is there, then `check-propagation` until the name
  servers answer, when a certificate is requested. Never overwrites, never fails the action; the
  result is `state/host-record.json`. The service refuses changes to that name
  (`reserved_name`).

## Using dnshelper

dnsapi is an ordinary dnshelper consumer
([its README, "Using dnshelper from another module"](https://github.com/danb35/ns8-dnshelper#using-dnshelper-from-another-module)):

- the grant is `dnshelper@any:dnswriter,dnszoneadmin` (not `@cluster`: DESIGN.md, Module plumbing,
  says why). `dnszoneadmin` (dnshelper 0.8.0) is for the domains added through the API;
  `dnswriter` stays so that an older dnshelper, without that role, grants the rest;
- it finds dnshelper with `list_service_providers`, the first by install order when there are
  several;
- it calls `list-zones` (cached 30 s), `list-providers` (cached 10 minutes), `get-records`, `list-owners`,
  `check-propagation`, and for changes `apply-changes`, `append-records`, `set-records` (mode
  `rrset`) and `delete-records`, always with `on_behalf_of="<tenant>:<key id>"`, so dnshelper's
  history names the tenant and records no owner;
- a zone can be assigned when its rule for dnsapi has `access: "write"`; `full` says whether it
  covers every name and type;
- as one of dnshelper's delegates, it also calls `validate-zone` (with inline fields),
  `add-credential`, `add-zone`, `remove-zone` and `remove-credential`; dnshelper reports the zones
  it added with `delegated: true`.

## Backup and restore

`etc/state-include.conf` backs up `api/settings.json`, `api/tenants.json` and `api/keys.json`;
`restore-module/40move_api` moves an older backup's files into `api/`.
`restore-module/50call-configure-module` runs `configure-module` with no input, which keeps the
restored settings and recreates the route. Restored keys keep working.

## Development

- `server/`: the API service and its tests. `cd server && python3 -m unittest discover -s tests`
  runs them; `build-images.sh` runs them inside the built image too.
- `imageroot/`: actions, `bin/`, events, `pypkg/dnsapi/`, the systemd units and the update hooks.
- `ui/`: the admin UI (Vue 2, ns8-ui-lib). Strings are written in English
  (`ui/public/i18n/en/translation.json`) and translated into Arabic, Basque, French, German,
  Italian, Portuguese (`pt` and `pt_BR`), Spanish, Tamil and Ukrainian. None of the translations
  has been reviewed by a native speaker. In the languages dnshelper is translated into, its pages
  and presets are named as its UI names them; elsewhere by their English names. The UI uses two
  plural forms only, so the Arabic and Ukrainian counts are not always grammatical. A browser
  set to `pt-BR` gets `pt_BR`, any other language its two-letter code, and a string a translation
  lacks falls back to English (`ui/src/main.js`). Add a string to every language, and run a
  locale's screenshots (`ui/dev/README.md`, `LOCALE`) to check that it fits. `ui/dev/` is a harness that runs the built UI in a browser with
  faked module data, and takes the user guide's screenshots (`ui/dev/README.md`).
- The logo is `ui/src/assets/module_default_logo.png`, rendered at 256×256 from
  `module_default_logo.svg` beside it.

## Testing

`tests/*.robot` is what CI runs on throwaway NS8 nodes (Rocky 9 and Debian 13). It runs in two
parts:

- **Without dnshelper:** the route, the settings, keys made from the shell and through the API,
  tenants through the module's own actions, restricted keys, Basic authentication on the ACME
  endpoints, keys sent over plain HTTP, editing and revoking keys, and the 503 while dnshelper
  is missing.
- **With dnshelper**, installed partway through (a pinned release, `DNSHELPER_IMAGE`), with a
  throwaway PowerDNS on the node's loopback as its DNS host and four test zones: one rule for
  every record on two of them, the ACME preset on one, none on the last. It covers:
  - dnsapi finding dnshelper, the provider list, the host record published and found again;
  - assignable zones, two tenants that cannot reach each other's zones, the zone with no rule;
  - every write endpoint, checked against what PowerDNS holds, with `stale`, `conflict` and the
    apex NS refused, and `on_behalf_of` in dnshelper's audit line;
  - the reserved host name, `owned_by` and its warning, ACME `present` and `cleanup` with
    Basic authentication, and both limits on ACME records (the key's and dnshelper's rule);
  - a zone dnshelper drops, tenants removed with their keys, and dnshelper removed.

  The propagation check is not covered: it asks a zone's public name servers. Nothing in it
  talks to a real DNS host or uses a real credential. When an API feature needs a newer
  dnshelper, raise `DNSHELPER_IMAGE` in `tests/dnsapi.robot`.

To run it on your own node, see [Running tests
locally](https://github.com/NethServer/ns8-github-actions/blob/v1/README.md#running-tests-locally);
the second part installs a dnshelper, so use a node without one.
What was tested against real zones on a node is recorded in DESIGN.md, build order.

## Author

[Dan Brown](https://community.nethserver.org/u/dan)
