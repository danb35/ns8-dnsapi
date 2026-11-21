# ns8-dnsapi: design brief (draft)

A separate NS8 module that puts an HTTPS API in front of dnshelper, so that software outside the
cluster (a billing or client portal such as Blesta or WHMCS, or the operator's own scripts) can
manage DNS records for the operator's customers. It is a dnshelper consumer like any other module:
it holds no DNS provider code and talks to DNS hosts only through dnshelper's actions.

The dnshelper side is in
[dnshelper's DESIGN.md](https://github.com/danb35/ns8-dnshelper/blob/master/DESIGN.md#delegated-access-for-an-api-module-draft),
"Delegated access for an API module". Items marked **VERIFY** were not confirmed from the sources
or on a node.

Status: build order step 1 is done (the service, its Traefik route and `GET /v1/status`); the rest
is design. dnshelper's side, phase 1, is released in dnshelper 0.7.0 (2026-11-21), which this
module needs at least.

Origin: forum request, community.nethserver.org topic 28774, posts 32-37 (2026-11-18/20).

## Scope

- **In:** a REST API with API keys; tenants (the operator's customers), each limited to their own
  zones; record reads and changes through dnshelper; an NS8 admin UI to manage tenants, zones and
  keys.
- **Later (phase 2):** the operator's tool adds domains and their DNS provider credentials through
  the API. Needs the dnshelper changes in its DESIGN.md, phase 2 (not built).
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
  write in full: `list-zones` and `has-zone` report `"full": true` for a zone where one write rule
  allows every name and type (dnshelper 0.7.0). The NS8 administrator grants that on dnshelper's
  Access page, with the "API module (all records)" preset, and dnsapi cannot widen it.
- **API key:** belongs to either the operator or one tenant.
  - Operator key: manages tenants and assignments, and acts on any tenant's zones. This is the key
    a billing portal uses: it acts for whichever customer is logged into it.
  - Tenant key: reaches only that tenant's zones. For customers who script their own DNS.
  - Every key has: a scope (`read` or `write`), an optional IP allowlist (CIDR), an optional
    expiry, a label, and created and last-used times.
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
| `GET/POST/PATCH/DELETE /v1/tenants[/{id}]` | operator | none (dnsapi's own state) |
| `PUT/DELETE /v1/tenants/{id}/zones/{zone}` | operator | `has-zone` checks that dnsapi may write all of it (`full`) |
| `POST/DELETE /v1/tenants/{id}/keys[/{key id}]` | operator | none |
| `GET /v1/status` | none | none (liveness only, says nothing about zones) |

A tenant key that names a zone it doesn't own gets 404, not 403, so that a key cannot be used to
find out which zones are managed.

Phase 2 adds `POST /v1/zones` (add a domain with a provider and credentials) and `DELETE
/v1/zones/{zone}`, using dnshelper's delegated-zone actions.

## Security

- **Transport:** a Traefik route on a dedicated host name (`set-route`: `host`, `lets_encrypt`,
  `http2https`). There is an optional cluster-wide IP allowlist (`ip_allowlist`, present in
  ns8-traefik since 3.0.0, verified in its `set-route` schema), so an operator whose only client is
  their billing server can close the API to everyone else at Traefik. The service listens on
  127.0.0.1 on a port from `org.nethserver.tcp-ports-demand`.
- **Per-key IP allowlist:** enforced by the service, using the client address Traefik forwards
  (`X-Forwarded-For` / `X-Real-Ip`). The header is trusted only on requests from Traefik.
  **VERIFY** which header ns8-traefik sets, and that a client cannot inject one.
- **Brute force:** keys are random, so guessing is not the realistic risk, but failed
  authentications are still counted per source address and throttled (429 with `Retry-After`), and
  logged.
- **Rate limits** per key, configurable, default 60 changes per minute. They protect the DNS
  hosts' own limits, which are shared by every user of a credential (GoDaddy is about 60 per
  minute).
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
- **Calling dnshelper from a long-running process.** `agent.tasks.run()` logs in to the api-server
  (`http://cluster-leader:9311`, `POST /api/login`, then `/api/<agent>/tasks` and `/ws`) with
  `REDIS_USER` / `REDIS_PASSWORD` from the environment. For a rootless module those come from
  `~/.config/state/agent.env` (verified in ns8-core `agent/tasks/apiclient.py` and `runagent`).
  The task then runs with `AGENT_TASK_USER=module/dnsapi1`, so dnshelper's policy applies.
  Options:
  1. A Python service using ns8-core's `agent` package, run with the agent environment.
  2. A service in any language that implements the api-server's task protocol itself.

  Option 1 is less code. Either way, the process that faces the internet holds the module's
  api-server credentials. Splitting it into a front end without credentials and a local back end
  that holds them is possible, but probably not worth it in v1: the blast radius is the same
  dnswriter role.
  **VERIFY** on a node: that a service unit can load agent.env and reach `cluster-leader:9311`
  from inside the container (host network?), and the token cache (`AGENT_STATE_DIR/apitoken.cache`)
  when a service and actions share it.
- **Latency:** every API call is an NS8 task (process start, dnshelper's Python step, Go helper,
  provider call). **VERIFY** the overhead; expect about 1 s plus the provider's own time (Hetzner
  takes 8-15 s). The API is synchronous with a generous upstream timeout, and the docs tell clients
  to allow 60 s.
- **Discovery:** dnshelper through `agent.list_service_providers(rdb, 'dnshelper')`, as every
  consumer does. The API is unavailable (503) while dnshelper is missing.
- **dnshelper older than 0.7.0** returns no `access`/`full` from `list-zones` and has no
  `apply-changes` in `dnswriter`. dnsapi then offers no zones, and the Status page says that
  dnshelper needs updating, rather than guessing what the old rules allow.

## Module plumbing

- Image labels: `org.nethserver.authorizations=dnshelper@any:dnswriter traefik@node:routeadm`;
  `org.nethserver.tcp-ports-demand=1`; `min-core` at least dnshelper's (3.23.0 for 0.7.0).
  - `@any`, not `@cluster`. A `@cluster` grant follows the cluster's default dnshelper instance.
    ns8-core never picks a new default once that instance is removed, so after a second dnshelper
    is installed and the first removed, a `@cluster` module is granted nothing. This was seen on the
    test node with ns8-automx; see dnshelper's DESIGN.md, Authorization, and its user guide.
  - `@any` grants `dnswriter` on every dnshelper instance. That gives no access by itself: each
    instance's policy is default deny until its administrator adds a rule for dnsapi.
  - With more than one dnshelper, dnsapi uses the one discovery finds first (open question 7).
- State (all in `state-include.conf`): `state/tenants.json` (tenants and zone assignments),
  `state/keys.json` (key ids, hashes, scopes, allowlists, mode 0600), `state/settings.json`.
  Secrets are never in `state/environment`. A restore brings keys back as they were, so restored
  keys keep working.
- Actions (admin UI): `configure-module` (host name, Let's Encrypt, Traefik IP allowlist, rate
  limits), `get-configuration`, `list-tenants`, `add-tenant`, `update-tenant`, `remove-tenant`,
  `assign-zone`, `unassign-zone`, `list-assignable-zones`, `create-key` (returns the key once),
  `revoke-key`, `list-keys`.
- Events: on dnshelper's `service-dnshelper-changed`, drop assignments of zones dnshelper no longer
  manages, or that dnsapi may no longer write. Log it; never fail.
- `destroy-module`: nothing to do for the route. Its instance name is `MODULE_ID`, and ns8-traefik's
  own `module-removed` handling deletes the routes whose name starts with it (the kickstart
  template relies on the same). dnshelper's own `module-removed` handling drops the module from its
  record owner index.

## Admin UI (NS8, cluster administrators)

- **Status:** API URL, dnshelper found or not, how many zones are assignable.
- **Tenants:** add, rename, disable; assign zones from the assignable list.
- **API keys:** create (shown once, with a copy button), revoke, last used.
- **Settings:** host name, certificate, Traefik allowlist, rate limits.
- **Activity:** recent changes from the audit lines.

This is not the customer control panel: only cluster administrators can reach it.

## Build order

1. Scaffold from ns8-kickstart; route via Traefik; `GET /v1/status`. **Done** (2026-11-21):
   - `server/`: the service, Python standard library only (`http.server`, one thread per
     request), in its own image `dnsapi-server`, built and published beside the module image with
     the same tag and unit-tested inside it by `build-images.sh`. Non-root user, `--read-only`
     container, published on `127.0.0.1:${TCP_PORT}`.
   - `configure-module`: `host`, `lets_encrypt`, `http2https`, `ip_allowlist`, kept in
     `state/settings.json` (backed up). It calls `set-route` before saving, with
     `lets_encrypt_check` when a certificate is requested, so a refused setting changes nothing.
     An omitted field keeps its value. `restore-module` re-runs it to recreate the route.
   - The kickstart smarthost example is removed: dnsapi sends no mail.
   - Tested on the test node (core 3.25.1, ns8-traefik 4.2.5): route, HTTPS redirect, JSON 404,
     allowlist on and off, `update-module` restart keeping the settings. Finding: when the
     allowlist changes twice within a second, Traefik can serve the previous one for about 2 s
     after the second `set-route` returns (seen in 1 of 3 tries). ns8-traefik's reload, not ours,
     and harmless for an admin setting, but a test that changes the allowlist must allow for it.
2. Tenants, keys, authentication, rate limits; the read endpoints.
3. Write endpoints over `apply-changes`, `append-records`, `set-records`, `delete-records`
   (dnshelper's phase 1: released in 0.7.0).
4. Admin UI; OpenAPI document; README with a Blesta/WHMCS-style walk-through.
5. Node test: two tenants, isolation (a tenant key cannot read or write the other tenant's zone),
   a zone dnshelper's policy does not grant, rate limits, key revocation.
6. Phase 2 (delegated zones), then phase 3 (PowerDNS hosting), as needed.

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
5. **Tenant-level restrictions** (record types, names), like dnshelper's policy rules. v1: none
   beyond the safety rails.
6. **Customer control panel:** this module's own UI with OIDC, or a separate module? Deferred.
7. **More than one dnshelper instance.** Use the first one discovery finds, or let the
   administrator choose one in Settings? v1: the first, shown on the Status page.
