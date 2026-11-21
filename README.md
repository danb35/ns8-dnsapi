# ns8-dnsapi

An HTTPS API for [NethServer 8](https://github.com/NethServer/ns8-core) that lets software
outside the cluster (a billing or client portal such as Blesta or WHMCS, or the operator's own
scripts) manage DNS records for the operator's customers. It holds no DNS provider code: every
read and change goes through [ns8-dnshelper](https://github.com/danb35/ns8-dnshelper) (0.7.0 or
later), limited by the access rules its administrator grants this module.

See [DESIGN.md](DESIGN.md) for the design.

## Status

Under development: nothing of the API is built yet. The module is still the ns8-kickstart
scaffold (an echo server behind a Traefik route), renamed to `dnsapi`.

## Install

Instantiate the module with:

    add-module ghcr.io/danb35/dnsapi:latest 1

The output of the command will return the instance name.
Output example:

    {"module_id": "dnsapi1", "image_name": "dnsapi", "image_url": "ghcr.io/danb35/dnsapi:latest"}

## Configure

Let's assume that the dnsapi instance is named `dnsapi1`.

    api-cli run module/dnsapi1/configure-module --data '{}'

The above command starts the instance and routes the `/dnsapi` path to it. Send a test HTTP
request to the backend service:

    curl http://127.0.0.1/dnsapi/

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
