# ns8-dnsapi

An HTTPS API for [NethServer 8](https://github.com/NethServer/ns8-core) that lets software
outside the cluster manage DNS records: a billing or client portal (Blesta, WHMCS, the operator's
own) acting for the operator's customers, customers' own scripts, and systems that validate
certificates with ACME DNS-01, including ones the internet cannot reach. It holds no DNS provider
code: every read and change goes through [ns8-dnshelper](https://github.com/danb35/ns8-dnshelper)
(0.7.0 or later), limited by the access rules its administrator grants this module. See
[DESIGN.md](DESIGN.md) for the design, the decisions and what was tested on a node.

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

Not released yet. Steps 1 to 5 of DESIGN.md's build order are done: the API behind Traefik on its
own host name; tenants, keys, authentication and rate limits; reading and changing records; ACME
DNS-01; the admin UI (Status, Tenants, Keys, Activity, Settings) and the OpenAPI document.

## Install

    add-module ghcr.io/danb35/dnsapi:latest 1
    api-cli run module/dnsapi1/configure-module --data '{"host": "dnsapi.example.com", "lets_encrypt": true}'

The user guide has the details. To remove an instance: `remove-module --no-preserve dnsapi1`.

## Actions

The schemas are in `imageroot/actions/<action>/validate-*.json`.

| Action | Input | |
|---|---|---|
| `configure-module` | `host`, `lets_encrypt`, `http2https`, `ip_allowlist`, `rate_limit`, `publish_host_record` | publish the API, adding the host name's CNAME to the node through dnshelper first when it can; an omitted field keeps its value |
| `get-configuration` | none | the settings, and `host_record`: what configure-module found about the host name's DNS record |
| `list-tenants`, `add-tenant`, `update-tenant`, `remove-tenant` | `name`, `enabled`, `id` | tenants; removing one removes its keys |
| `assign-zone`, `unassign-zone` | `tenant`, `zone` | a zone dnshelper lets dnsapi write in; at most one tenant per zone |
| `list-assignable-zones` | none | those zones, with `full` and their tenant |
| `create-key` | `id`, `hash`, `owner`, `scope`, `label`, `allowlist`, `expires`, `restrict` | stores a key from its SHA-256: the action never sees the key |
| `revoke-key`, `list-keys` | `id`; optional `owner` | |
| `get-overview` | none | what the Status page shows: the API's address, the dnshelper instance, how many zones, tenants and keys |
| `list-activity` | optional `limit` | the most recent changes, made through the API or the actions, newest first |

`bin/create-key`, run with `runagent -m dnsapi1`, makes a key, stores its hash and prints it: it
is how the first operator key is made. The API service calls the tenant and key actions itself
(see [How it fits together](#how-it-fits-together)); it cannot make or revoke operator keys.

## API

Base URL `https://<host>/v1`; plain HTTP is refused, and a key sent over it should be revoked. The OpenAPI 3.1 document is at `/v1/openapi.json`, without a key
(`server/make_openapi.py` writes it; a unit test checks that it describes every route). Send the key as `Authorization: Bearer <key>`; keys look like
`dnsapi_<8 hex>_<52 base32>`. Bodies are JSON, at most 1 MB. A read key may only `GET`. Errors
are `{"error": {"code", "message", "field"}}`:

| Status | Codes |
|---|---|
| 400 | `invalid_request`, `invalid_json` (with `field`), and dnshelper's `invalid_request`, `unsupported` |
| 401 | `missing_key`, `invalid_key`, `key_expired` |
| 403 | `insufficient_scope`, `tenant_disabled`, `address_not_allowed`, `restricted_key`, `outside_restriction`, `reserved_name` (the API's own host name and its `_acme-challenge`), `https_required` (the request came over plain HTTP); dnshelper's `not_permitted`, `forbidden` (apex NS, SOA) |
| 404 | `not_found`, `zone_not_found`, `tenant_not_found`, `key_not_found` |
| 409 | `stale` (a record to remove is gone), `conflict` (e.g. a CNAME beside other records), `zone_assigned` |
| 413 | `body_too_large` |
| 429 | `rate_limited`, `too_many_concurrent` (more than 4 requests of one key at once), with `Retry-After` |
| 502, 503, 504 | `upstream_error` (the DNS host failed), `dnshelper_missing`, `unavailable` or `busy` (too many requests at once for the whole service), `upstream_timeout` |

A tenant key gets 404, not 403, for a zone it does not own and for the operator endpoints, so a
key cannot be used to find out which zones are managed.

| Request | Key | |
|---|---|---|
| `GET /v1/status` | none | liveness only |
| `GET /v1/zones` | any | `{"zones": [{"zone", "provider", "full", "tenant"}]}`: the key's zones (operator: every assignable zone; `tenant` only for operator keys) |
| `GET /v1/zones/{zone}/records?name=&type=` | any | the records; those another module wrote carry `owned_by` |
| `GET /v1/zones/{zone}/propagation?name=&type=` | any | what the zone's name servers answer, compared with the DNS host |
| `POST /v1/zones/{zone}/changes` `{"remove", "add", "dry_run"}` | write | remove exact records and add others as one change; refused as a whole with 409 `stale` if a record to remove is no longer there |
| `POST /v1/zones/{zone}/records` `{"records", "dry_run"}` | write | add records; never removes any |
| `PUT /v1/zones/{zone}/rrsets` `{"records", "dry_run"}` | write | make the given records the only ones of each name and type |
| `DELETE /v1/zones/{zone}/records` `{"records", "dry_run"}` | write | remove the matching records (`name` required; a `type`, `ttl` or `data` left out matches anything) |
| `GET`, `POST /v1/tenants` | operator | list, add (`{"name"}`) |
| `GET`, `PATCH`, `DELETE /v1/tenants/{id}` | operator | read, change (`{"name", "enabled"}`), remove with its keys |
| `PUT`, `DELETE /v1/tenants/{id}/zones/{zone}` | operator | assign, unassign a zone |
| `GET`, `POST /v1/tenants/{id}/keys` | operator | list, make a tenant key (`{"scope", "label", "allowlist", "expires", "restrict"}`); only the response holds the key |
| `DELETE /v1/tenants/{id}/keys/{key id}` | operator | revoke |
| `POST /v1/acme/present`, `/v1/acme/cleanup` | write | see [ACME endpoints](#acme-endpoints) |

A restricted operator key (`restrict`) reaches the zones but not the tenant and key endpoints.

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

## ACME endpoints

`POST /v1/acme/present` and `POST /v1/acme/cleanup` take `{"fqdn": "_acme-challenge.www.example.com.",
"value": "<token>"}`: the protocol of lego's `httpreq` provider and acme.sh's `acmeproxy`
(checked against their sources, see DESIGN.md). They accept HTTP Basic authentication with the
key as the password and any user name, as those clients send it; nowhere else does.

- The `fqdn` must start with the label `_acme-challenge`; the trailing dot is optional. The zone
  is the longest of the key's zones that contains it.
- `present` adds the TXT value with a TTL of 60 and keeps any other value at that name;
  `cleanup` removes only that value. They run as any other change (write scope, `restrict`, rate
  limit, audit line).
- The answer is `{"fqdn", "value", "zone", "changes"}`: acme.sh needs the value echoed.
- lego's `RAW` mode is not supported. A CNAME on `_acme-challenge` pointing to a name that does
  not start with `_acme-challenge` is refused (lego sends the CNAME's target).

The user guide shows the lego, acme.sh and certbot setups.

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
- **Customer scripts their own DNS**: `POST /v1/tenants/{id}/keys` makes a tenant key; show it
  once. Revoke it with `DELETE .../keys/{key id}`.
- **Customer leaves**: `DELETE /v1/tenants/{id}` removes the tenant and its keys and unassigns its
  zones; no record changes.

Set a timeout of at least 60 s, and back off on 429 for `Retry-After` seconds. Every request is
listed on the administrator's Activity page with the operator key and the tenant; dnshelper's
history names the tenant.

## How it fits together

- **Two images.** `dnsapi` is the NS8 module (actions, systemd unit, UI); `dnsapi-server`
  (`server/Containerfile`) is the API service, Python standard library only. They are published
  together with the same tag.
- **The service** runs rootless with `--network=host`, listens on `127.0.0.1:${TCP_PORT}`, and
  Traefik routes the API host name to it. It runs as the module's uid with no capabilities,
  mounts only `state/api/` read-only, `state/usage/` and the broker's socket directory, and
  **holds no NS8 credentials**.
- **The broker** (`dnsapi-broker.service`, `bin/dnsapi-broker`, `pypkg/dnsapi/broker.py`) runs
  on the host under `runagent` with the module's credentials, and runs only the tasks the API
  needs, for the service, over a Unix socket: dnshelper's reads, its four writes (only with
  `on_behalf_of`), and this module's tenant and key actions (never an operator key). The tasks
  are three HTTP calls to the api-server (`pypkg/dnsapi/apiclient.py`; ns8-core's
  `agent.tasks.run` cannot run in the broker's threads) and run as `module/dnsapi1`, so
  dnshelper's policy applies.
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
  the first also drops assignments of zones dnsapi may no longer write in.
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

- the grant is `dnshelper@any:dnswriter` (not `@cluster`: DESIGN.md, Module plumbing, says why);
- it finds dnshelper with `list_service_providers`, the first by install order when there are
  several;
- it calls `list-zones` (cached 30 s), `get-records`, `list-owners`,
  `check-propagation`, and for changes `apply-changes`, `append-records`, `set-records` (mode
  `rrset`) and `delete-records`, always with `on_behalf_of="<tenant>:<key id>"`, so dnshelper's
  history names the tenant and records no owner;
- a zone can be assigned when its rule for dnsapi has `access: "write"`; `full` says whether it
  covers every name and type.

## Backup and restore

`etc/state-include.conf` backs up `api/settings.json`, `api/tenants.json` and `api/keys.json`;
`restore-module/40move_api` moves an older backup's files into `api/`.
`restore-module/50call-configure-module` runs `configure-module` with no input, which keeps the
restored settings and recreates the route. Restored keys keep working.

## Development

- `server/`: the API service and its tests. `cd server && python3 -m unittest discover -s tests`
  runs them; `build-images.sh` runs them inside the built image too.
- `imageroot/`: actions, `bin/`, events, `pypkg/dnsapi/`, the systemd unit and the update hooks.
- `ui/`: the admin UI (Vue 2, ns8-ui-lib), translated with
  [Weblate](https://hosted.weblate.org/projects/ns8/).

## Testing

`tests/*.robot` is what CI runs on throwaway NS8 nodes (Rocky 9 and Debian 13), which have no
dnshelper: it covers the route, the settings, keys made from the shell and through the API,
tenants through the module's own actions, isolation, restricted keys, Basic authentication on
the ACME endpoints, revocation, and the 503 while dnshelper is missing. To run it on your own
node, see [Running tests
locally](https://github.com/NethServer/ns8-github-actions/blob/v1/README.md#running-tests-locally).
What was tested against real zones on a node is recorded in DESIGN.md, build order.

## Author

[Dan Brown](https://community.nethserver.org/u/dan)
