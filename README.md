# ns8-dnsapi

An HTTPS API for [NethServer 8](https://github.com/NethServer/ns8-core) that lets software
outside the cluster (a billing or client portal such as Blesta or WHMCS, or the operator's own
scripts) manage DNS records for the operator's customers. It holds no DNS provider code: every
read and change goes through [ns8-dnshelper](https://github.com/danb35/ns8-dnshelper) (0.7.0 or
later), limited by the access rules its administrator grants this module.

See [DESIGN.md](DESIGN.md) for the design.

## Status

Step 1 of DESIGN.md's build order: the API service runs behind Traefik on its own host name and
answers `GET /v1/status`. Tenants, keys and the DNS endpoints are not built yet.

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

An omitted field keeps its current value. The settings are in `state/settings.json`, which is
backed up. Check the service:

    curl https://dnsapi.example.com/v1/status

which answers `{"status": "ok"}`.

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
