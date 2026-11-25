Read @DESIGN.md before doing anything; items marked VERIFY must be checked against the NS8 docs or a
live node, not assumed.

## Documentation

As in ns8-dnshelper and ns8-automx: `README.md` is for developers (people who build, test or work
on dnsapi, and who write a client for its API), `docs/USER-GUIDE.md` for the system
administrator (publishing the API, zones, tenants, keys, ACME clients, troubleshooting). Each
starts by pointing to the other. DESIGN.md keeps the design, the decisions and what was tested.

## dnshelper (DNS records)

This module reads and changes DNS records only by calling the `dnshelper` module, which lives in
its own repository: https://github.com/danb35/ns8-dnshelper (checked out locally at
`/Users/dan/Documents/GitHub/ns8-dnshelper`). Before writing or changing any code that calls it,
read its README section "Using dnshelper from another module", its DESIGN.md section "Delegated
access for an API module", and the JSON schemas in `imageroot/actions/<action>/validate-*.json`.
Do not work from memory of the API.

- The grant is `dnshelper@any:dnswriter` (not `@cluster`; DESIGN.md, Module plumbing, says why).
- Find it with `agent.list_service_providers(rdb, 'dnshelper')`; handle it being absent.
- dnshelper denies everything until its administrator adds an access rule for this module.
  `not_permitted` means a missing rule, not a bug.
- If dnshelper needs a change, make it in the dnshelper repo, as its own branch and PR; do not work
  around it here.
- Do not modify or remove the dnshelper instance on the test node (it holds real zones and
  credentials).

## GitHub Actions setup

This repo came from the ns8-kickstart template, whose workflows do not work unmodified. The fixes
already applied (the same as in ns8-dnshelper and ns8-automx):

- Every `kickstart` placeholder renamed to `dnsapi`. The test workflow derives the image name from
  the repository, so `reponame` in `build-images.sh` must stay `dnsapi`.
- `permissions: contents: write` in `build-apidoc.yml` and `clean-apidoc.yml`: a reusable workflow
  cannot exceed its caller's permissions and the default token is read-only (`startup_failure`
  otherwise). Do not raise the repository-wide default instead.
- `clean-registry.yml` replaced with dnshelper's version, which computes the tag the same way as
  the publish workflow, uses the built-in token, refuses `master`, `main` and `latest`, and can be
  run by hand: `gh workflow run clean-registry.yml -f tag=<branch with / as ->`.
- `test-ui-build-renovate.yml` targets `master`, the default branch here.

Two images are published: `dnsapi` (the module) and `dnsapi-server` (the API service, from
`server/Containerfile`); `clean-registry.yml` lists both. Both ghcr packages must be pullable
anonymously, or the test fails at "cannot resolve ghcr.io/danb35/<image>:<branch>" (403), or the
node can't pull the service image. After a new image's first publish, check the package's
visibility and set it to public if needed. `publish-images.yml` skips the very first run
(`if: github.run_number > 1`); that is normal.

How the tests run: `test-module.yml` starts after "Publish images" succeeds (`workflow_run`), boots
throwaway NS8 nodes (Rocky 9 and Debian 13) and runs `tests/*.robot` against the image just
published as `ghcr.io/danb35/dnsapi:<branch>`. Robot tests must use fake credentials only; nothing
in CI may talk to a real service. Partway through, the suite installs a pinned dnshelper
(`DNSHELPER_IMAGE`) with a throwaway PowerDNS on the node's loopback as its DNS host. It has failed for reasons unrelated to the code (SSH refused
right after the VM starts; NS8's cluster setup failing to pull its `metrics` module): re-run before
suspecting the module, and read the failing step with `gh run view --job <id> --log`.

Releases are listed in danb35/ns8-repomd (`dnsapi/` there holds the logo and screenshots).
`notify-repomd.yml` (copied from ns8-powerdns) asks it to rebuild once a release tag's images
are published; it needs the repository secret `REPOMD_DISPATCH_TOKEN`, a fine-grained token for
danb35/ns8-repomd with "Contents: read and write". Without it the workflow only warns, and
ns8-repomd picks the release up at its next scheduled build (every six hours). `workflow_run`
workflows run from the default branch, so a change to it takes effect once merged.

Image tags: every pushed branch or tag publishes `ghcr.io/danb35/dnsapi:<ref>` with `/` replaced by
`-`; `master` also updates `latest`. Release tags are plain semver without a `v` (for example
`0.1.0`), annotated, on a commit whose checks all passed.
