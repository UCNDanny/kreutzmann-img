# kreutzmann-img

Own-image builds of oauth2-proxy and Keycloak for `linux/amd64` and `linux/arm64`.
The GitHub Actions pipeline builds on native runners, tests and scans before
publication, and publishes signed multi-platform images to GHCR.

The publication gate blocks any release with a vulnerability that has an available
upstream fix, at every severity. Findings with no fix — currently Debian base-OS
packages in both distroless images — are tracked in [SECURITY-SCAN.md](SECURITY-SCAN.md)
and `compliance/vulnerability-findings.csv` rather than gated. A single scanner's clean
result does not by itself satisfy the gate.

**These are not CIS-certified, STIG-assessed, or deployment-qualified FIPS images.**
Go's pinned FIPS module and Keycloak's strict BCFIPS provider are configured.
The remaining assessment boundaries are recorded in [SECURITY-CONTROLS.md](SECURITY-CONTROLS.md).
Do not advertise compliance without completing that evidence. This matters on Railway,
where the underlying FIPS host and runtime controls have not been established.

## Put this in your repository

Copy the **contents** of this directory to the root of your GitHub repository,
including `.github`, `.dockerignore`, and `.gitignore`. Use `main` as the default
branch, or update every `refs/heads/main`/branch condition in `release.yml`.
The workflows must be at the repository root to be discovered by GitHub.

In GitHub:

1. Enable Actions and allow GitHub Actions to create pull requests.
2. Protect `main`; require the four native `build` matrix checks and human review.
3. Enable the daily update workflow. You can also run it manually in Actions.
4. Ensure native `ubuntu-24.04-arm` runners are available for your repository/plan.
   Assign equivalent runners if necessary.
5. Artifact attestations require a public repo or an org/Enterprise plan. On a
   user-owned private repo the workflow skips them; everything else still runs.

No PAT is needed. The updater uses `GITHUB_TOKEN` to create a dependency PR and
explicitly dispatches validation, avoiding GitHub's token-created-PR trigger suppression.
Merging triggers publication. For the first release, push these files to `main`,
then open **Actions → Build, validate, and release** and wait for all jobs to finish.
You can also select **Run workflow** on `main`. Each final `index` job prints the
exact image digest to use in your service. Set the service image source to that
reference, provide deployment variables through the hosting service, and deploy.
There is **no automatic production deployment**.

Images are published as:

- `ghcr.io/<lowercase-owner>/kreutzmann-img/oauth2-proxy`
- `ghcr.io/<lowercase-owner>/kreutzmann-img/keycloak`

The successful workflow summary contains deployable `@sha256:...` references.
Release tags include source SHA, run ID, and run attempt; architecture tags add
`-amd64` or `-arm64`. There is no mutable `latest` release tag.
Only use one publishing repository per owner for these package names, or rename
both occurrences in the workflow before setting up another repository.

Set GHCR package visibility/access so Railway can pull the images. Public packages
avoid registry credentials; private packages require a suitably scoped pull credential.

## Build locally

Requires a running Docker engine with Buildx and Compose, Python 3.10+, and Make.
Run from this directory:

```sh
make setup
# Edit .env: database connection and upstream URLs.
make build
make identity
# Configure host HTTPS forwarding for your Keycloak hostname to localhost:8080.
# Once the apps realm issuer is reachable over HTTPS:
make gateway
```

`make setup` generates the client, cookie, and bootstrap administrator secrets in a
mode-0600 `.env`. It preserves an existing `.env` without rotating credentials.
Provide your existing external database credentials yourself. Local Compose needs
upstreams reachable from its containers; replace the example Railway private names.
Configure host HTTPS forwarding for your gateway hostname to localhost:4180 as well.

Use `make logs` to follow logs, `make down` to stop services, and `make up` for
subsequent starts after the realm and HTTPS routing have been configured.
Setup and build commands do not run tests. To run checks or build individual images:

```sh
python3 -m unittest discover -s tests -v
python3 scripts/dependencies.py --build oauth2-proxy
python3 scripts/dependencies.py --build keycloak
python3 scripts/smoke.py oauth2-proxy
python3 scripts/smoke.py keycloak
```

The default platform matches the local machine. To build AMD64 explicitly:

```sh
python3 scripts/dependencies.py --build oauth2-proxy --platform linux/amd64 --tag kreutzmann-img/oauth2-proxy:amd64
python3 scripts/dependencies.py --build keycloak --platform linux/amd64 --tag kreutzmann-img/keycloak:amd64
```

Build through this script so all required build arguments come from the lock.
Base-image ARGs also have valid digest-pinned defaults, synchronized by the dependency
updater, so Docker's default-image checks do not emit warnings. Do not replace them
with `latest`.
Upstream source archives are downloaded from locked URLs. Keycloak also copies
its launcher, JVM options, security-update script, and lock from this repository.
Neither build needs deployment secrets.

## Updates and supply chain

`dependencies.lock.json` is the source of truth for release archives, checksums,
base-image index digests, source commit, compatible Go patch, and BCFIPS artifacts.

```sh
python3 scripts/dependencies.py --update
```

This refreshes stable upstream releases and base digests and derives BCFIPS versions
from Keycloak's release POM. Review changes, especially major releases and crypto
provider changes. The Go FIPS module version stays explicitly pinned for manual review.
The initial archive hashes are obtained from trusted HTTPS upstreams and then locked;
this is not a substitute for upstream signature verification or a CMVP assessment.

Both runtime images use digest-pinned distroless Debian 13 bases: static for the
gateway and Java 21 for Keycloak. UBI and its RPM tooling exist only in Keycloak's
build stage. Neither runtime contains a shell or package manager. Keycloak starts
directly in Java; use `JAVA_TOOL_OPTIONS` for additional JVM options and keep
`start --optimized` for server startup.
Base distro major/minor upgrades, action updates, and Go FIPS module upgrades require
review. Dependabot handles pinned GitHub Action updates.

Vulnerabilities with an available upstream fix, at every severity, block publication;
the gate sets `ignore-unfixed`. Findings with no fix — currently Debian base-OS packages
in both distroless images — are kept in each run's scan artifacts and in
`compliance/vulnerability-findings.csv`, and reviewed there instead of blocking. The
only explicit exclusion is GO-2026-5932 on the gateway binary: the
advisory concerns OpenPGP, which is absent from its target-platform dependency graph.
Every gateway build and the smoke test enforce that absence. If OpenPGP is introduced,
the build fails before scanning. The evidence is retained in the image at
`/usr/share/ourimageshardened/packages.txt`. `.trivyignore-oauth2-proxy.yaml` scopes
the exclusion to that finding, package, and binary path; it is never applied to Keycloak.
The unfiltered JSON report remains available in each workflow run’s scan artifacts.
A clean scan does not establish compliance.
The gateway applies explicitly pinned `golang.org/x/crypto` and gRPC security updates
from `go_security_updates` in the lock, verified through Go's checksum database.
These pins require review when upstream dependencies change. Keycloak also applies checksum-pinned
Netty 4.1.137.Final, OpenTelemetry API/context/common 1.62.0, and SQL Server JDBC
13.4.0.jre11 updates before augmentation. The exact artifacts are recorded in
`keycloak_security_updates`; review them when updating Keycloak. Keycloak's distroless runtime leaves build tooling outside the final image. Upstream vulnerabilities with an available fix must be taken before a release can publish.
Native build jobs have read-only repository permissions. Publication jobs download
the tested artifacts and never execute application images or untrusted PR code.

SBOMs and build provenance are attested per architecture where GitHub allows it
(public repos, or org/Enterprise plans); a user-owned private repo skips that step.
Each architecture image is signed immediately after publication regardless, and the
final multi-platform index is signed after assembly. Signing uses GitHub Actions OIDC
with Cosign; no signing key or extra repository secret is needed. Local builds are unsigned until published by this workflow.
Verify the GitHub workflow identity, issuer, and exact digest when consuming
signatures. Signatures prove publisher identity, not compliance.

## Deployment

See [DEPLOY-RAILWAY.md](DEPLOY-RAILWAY.md) for the primary deployment.

`docker-compose.yml` is a host reference: external PostgreSQL and a trusted host TLS
reverse proxy are required. Ports bind only to loopback. It cannot resolve Railway
private names on an ordinary host. Use private connectivity appropriate for the host;
do not expose protected upstreams as a workaround.

Run `make setup` to generate `.env`, then supply connection settings and image digests.
Both images include public CA certificates from the digest-pinned CA base; no manual
certificate download or host mount is required. Keycloak uses the distroless Java trust store
and automatically prepares `/tmp/database-ca.pem` for the supplied JDBC configuration.
For an external service using a private CA, its trusted certificate must be provided
as `DATABASE_CA_PEM` by the deployment environment. The image cannot establish trust
in an unknown private CA automatically. Protect `.env` with mode 0600.
`docker compose config --quiet` checks configuration without printing
expanded secrets. Never share the output of a full expanded Compose configuration.

```sh
make setup
# Supply connection settings in .env before continuing.
docker compose config --quiet
docker compose up -d
```

Realm and client provisioning is managed separately through Keycloak's admin console
or your own provisioning process. This repository does not ship or import realm
configuration. Configure the matching issuer URL, client ID, client secret, callback
URL, scopes, groups, and upstreams through deployment variables. Existing realms
remain in the external database. Keycloak's local data is temporary. Remove bootstrap
administrator credentials after initial setup. Do not use `start-dev` in production.

## Verification limits

CI builds each image natively from locked inputs, runs the repository unit tests,
smoke-tests the built image under the production runtime restrictions, and blocks any
finding with an available fix before publishing signatures and, where GitHub supports
it, SBOM and provenance attestations. The
smoke test checks the fixed non-root identity, that the image starts read-only with no
capabilities, the gateway's FIPS build flags and OpenPGP absence, and that Keycloak
reaches BCFIPS Approved Mode. It does not exercise OIDC login, database TLS, HTTP
routing, or the FIPS qualification of the host.

Before production, run the checklist in `DEPLOY-RAILWAY.md` against an isolated test
database and users. No database container or production credentials are used by CI.
