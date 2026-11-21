# ns8-dnsapi

An HTTPS API for [NethServer 8](https://github.com/NethServer/ns8-core) that lets software
outside the cluster (a billing or client portal such as Blesta or WHMCS, or the operator's own
scripts) manage DNS records for the operator's customers. It holds no DNS provider code: every
read and change goes through [ns8-dnshelper](https://github.com/danb35/ns8-dnshelper) (0.7.0 or
later), limited by the access rules its administrator grants this module.

See [DESIGN.md](DESIGN.md) for the design.

## Status

Steps 1 to 3 of DESIGN.md's build order: the API runs behind Traefik on its own host name, with
tenants, API keys, rate limits, and reading and changing records. The ACME additions (step 4) and
the admin UI pages for tenants and keys (step 5) are not built yet.

## Install

Instantiate the module with:

    add-module ghcr.io/danb35/dnsapi:latest 1

The output of the command will return the instance name.
Output example:

    {"module_id": "dnsapi1", "image_name": "dnsapi", "image_url": "ghcr.io/danb35/dnsapi:latest"}

## Configure

Let's assume that the dnsapi instance is named `dnsapi1`. The API needs a host name of its own,
with a DNS record pointing to the node:

    api-cli run module/dnsapi1/configure-module --data '{"host": "dnsapi.example.com", "lets_encrypt": true, "http2https": true, "ip_allowlist": []}'

- `host` (required the first time): the API is served at `https://<host>/v1/`.
- `lets_encrypt`: request a Let's Encrypt certificate. The action fails, changing nothing, if the
  certificate is not issued. Default `false`.
- `http2https`: redirect plain HTTP to HTTPS. Default `true`.
- `ip_allowlist`: IP addresses or CIDR networks that Traefik lets through, for example only the
  billing server. Empty allows every address. Default empty.
- `rate_limit`: DNS requests per minute for each key. Every request that calls dnshelper counts,
  reads too, since the DNS hosts' own limits count them. Default 60.

An omitted field keeps its current value. The settings are in `state/settings.json`, which is
backed up. Check the service:

    curl https://dnsapi.example.com/v1/status

which answers `{"status": "ok"}`.

## Give dnsapi zones

dnsapi can hand a tenant only a zone that dnshelper lets it write in full. On dnshelper's Access
page, add a rule for `module/dnsapi1` with the "API module (all records)" preset on the zones the
API may manage. Then:

    api-cli run module/dnsapi1/list-assignable-zones

## Keys

Keys look like `dnsapi_<id>_<secret>` and are shown once, when they are made: only their SHA-256
is stored. Make the first operator key (the one a billing portal uses) from a shell on the node:

    runagent -m dnsapi1 create-key --owner operator --scope write --label "billing portal"

`--allowlist 203.0.113.10,198.51.100.0/24` limits where it may be used from, `--expires
2027-12-31T00:00:00Z` when. `api-cli run module/dnsapi1/list-keys` lists the keys and when each
was last used; `api-cli run module/dnsapi1/revoke-key --data '{"id": "<key id>"}'` revokes one.

## API

Send the key as `Authorization: Bearer <key>`. Errors are `{"error": {"code", "message",
"field"}}`. A read key may only `GET`.

| Request | Key | |
|---|---|---|
| `GET /v1/status` | none | liveness |
| `GET /v1/zones` | any | the key's zones (operator: every assignable zone, with its tenant) |
| `GET /v1/zones/{zone}/records?name=&type=` | any | the records; those another module wrote carry `owned_by` |
| `GET /v1/zones/{zone}/propagation?name=&type=` | any | what the zone's name servers answer |
| `POST /v1/zones/{zone}/changes` `{"remove", "add", "dry_run"}` | write | remove exact records and add others as one change; refused as a whole (409 `stale`) if a record to remove is no longer there |
| `POST /v1/zones/{zone}/records` `{"records", "dry_run"}` | write | add records; never removes any |
| `PUT /v1/zones/{zone}/rrsets` `{"records", "dry_run"}` | write | make the given records the only ones of each name and type |
| `DELETE /v1/zones/{zone}/records` `{"records", "dry_run"}` | write | remove the matching records (`name` required; a `type`, `ttl` or `data` left out matches anything) |
| `GET`, `POST /v1/tenants` | operator | list, add (`{"name"}`) |
| `GET`, `PATCH`, `DELETE /v1/tenants/{id}` | operator | read, change (`{"name", "enabled"}`), remove with its keys |
| `PUT`, `DELETE /v1/tenants/{id}/zones/{zone}` | operator | assign, unassign a zone |
| `GET`, `POST /v1/tenants/{id}/keys` | operator | list, make a tenant key (`{"scope", "label", "allowlist", "expires"}`); the response has the key |
| `DELETE /v1/tenants/{id}/keys/{key id}` | operator | revoke |

A record is `{"name", "type", "ttl", "data"}`, as in dnshelper: `name` relative to the zone (`@` for
the apex), `data` in zone-file form without quotes (TXT is one plain string; MX is `"10
mail.example.com."`), `ttl` optional. At most 100 records per request. dnshelper refuses invalid
results (a CNAME beside other records) and never changes the apex NS and SOA records.

A change answers `{"zone", "dry_run", "changes": {"add", "remove"}, "warnings", "records"}`. To edit
a record, remove the old value and add the new one in one `changes` request. With `"dry_run":
true` nothing is written.

**Records written by other modules.** Some records were written by an NS8 module, for example the
mail server's MX or DKIM record. A tenant may change them, but the module may write them again.
A change that removes one carries a warning:

    "warnings": [{"code": "owned_by_module", "record": {...}, "modules": ["mail1"], "message": "..."}]

and `GET .../records` marks such records with `"owned_by": ["mail1"]`. A portal should send a dry
run first, show the warnings, and send the change only when the user confirms.

A tenant key gets 404 for a zone it does not own. Too many requests give 429 with `Retry-After`.
Calls that reach the DNS host can take as long as the host does (Hetzner: 8 to 15 s); allow 60 s.

    curl -H "Authorization: Bearer $KEY" https://dnsapi.example.com/v1/zones
    curl -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
        -d '{"remove": [{"name": "www", "type": "A", "data": "192.0.2.1"}],
             "add": [{"name": "www", "type": "A", "data": "192.0.2.2"}], "dry_run": true}' \
        https://dnsapi.example.com/v1/zones/example.com/changes

## Development

- `server/`: the API service (Python, standard library only) and its `Containerfile`.
  `build-images.sh` builds it as the `dnsapi-server` image and runs `server/tests` inside it. Run
  the tests locally with `cd server && python3 -m unittest discover -s tests`.
- `imageroot/`: the NS8 actions and the systemd unit; `ui/`: the admin UI.

## Uninstall

To uninstall the instance:

    remove-module --no-preserve dnsapi1

## Running tests locally

This module uses the NS8 standard testing infrastructure. For instructions on how to run the test
suite locally, refer to the [Running tests
locally](https://github.com/NethServer/ns8-github-actions/blob/v1/README.md#running-tests-locally)
section of the ns8-github-actions README.

## UI translation

Translated with [Weblate](https://hosted.weblate.org/projects/ns8/).
