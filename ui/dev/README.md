# UI harness

The dnsapi UI only runs inside the NS8 shell (it reads `window.parent.core`), which makes it
awkward to look at. This harness fakes the shell so the built UI can be exercised in a browser.
It is adapted from [ns8-automx's](https://github.com/danb35/ns8-automx/tree/master/ui/dev) and
[ns8-dnshelper's](https://github.com/danb35/ns8-dnshelper/tree/master/ui/dev).

- `harness.html` is the parent page: it provides `window.core` (an event emitter, `apiUrl`,
  `$t`) and relays task results to the app, the way the shell does over its websocket.
- `server.py` is a mock NS8 API. dnsapi's actions need a node (dnshelper, Traefik, the API
  service), so they are faked in memory: dnshelper lets dnsapi write in four zones (three in full,
  `internal.example.net` with the ACME preset only), three tenants, seven keys (one expired, one revoked) and some activity.
  Tenant and key views come from the module's real `dnsapi.state` code; the outputs follow each
  action's `validate-output.json`, so check them again when an output schema changes. Changes made
  through the UI are kept until the harness stops.

```bash
cd ui && yarn build                    # or copy a node's /var/lib/nethserver/cluster/ui/apps/<dnsapi id>/ to ui/dist
CORE_CSS=/path/to/core.css python3 dev/server.py
```

then open <http://127.0.0.1:8099/>. Without Node.js on the machine, build in a container as
`build-images.sh` does:

```bash
docker run --rm -v "$PWD:/usr/src" -w /usr/src/ui -e NODE_OPTIONS=--openssl-legacy-provider \
    docker.io/library/node:26.13.1-slim \
    sh -c "npm install -g corepack@0.36.0 && corepack enable && yarn install && yarn build"
```

Saving Settings with a host name starting with `norule.` (such as `norule.example.com`) acts
as a node where dnshelper has no rule for the host record: the record is reported as not
permitted and, with Let's Encrypt on, the save fails with a certificate error.

`CORE_CSS` is the NS8 core UI's stylesheet: the concatenation of its `css/app~*.css` files, for
example `ssh root@<node> 'cat /var/lib/nethserver/cluster/ui/css/app~*.css' > core.css`. Without
it the app renders without the shell's Carbon styles.

## Screenshots

`screenshots.js` drives the harness in a headless browser and takes the pictures used in
[docs/USER-GUIDE.md](../../docs/USER-GUIDE.md), so that they can be redone when the UI changes.
Pages are taken 1056 pixels wide, where the tables fit and dialogs show as a window over the page.
It makes a key in the Create key dialog, which needs `crypto.subtle` and so a secure context: the
script loads the harness from `localhost` inside the container, through a forwarder to `HARNESS`.

```bash
# in one terminal: the harness, with the shell's stylesheet
CORE_CSS=/path/to/core.css python3 ui/dev/server.py

# in another: the browser, in Docker (Docker Desktop reaches the host as host.docker.internal)
mkdir -p /tmp/shots
docker run --rm -v "$PWD/ui/dev:/work:ro" -v /tmp/shots:/out mcr.microsoft.com/playwright:v1.49.1-jammy \
    bash -c "mkdir /tmp/w && cd /tmp/w && npm init -y >/dev/null && npm i playwright-core@1.49.1 >/dev/null \
             && cp /work/screenshots.js . && OUT=/out node screenshots.js"
```

Set `LOCALE` (for example `-e LOCALE=de-DE` on the `docker run`) to take the pictures in another
language, to check that translated labels fit; the script finds pages by their place in the menu,
not their name.

Start from a fresh harness, then copy the pictures into `docs/images/`.
