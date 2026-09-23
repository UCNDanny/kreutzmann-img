# kreutzmann-img

Own-image builds of oauth2-proxy and Keycloak for `linux/amd64` and `linux/arm64`.
Dependency refreshes, builds, tests, scans, signing, and publication are manual. This
repository does not include Dependabot or GitHub Actions workflows. Findings without
an upstream fix are tracked in [SECURITY-SCAN.md](SECURITY-SCAN.md) and
`compliance/vulnerability-findings.csv`.

**These are not CIS-certified, STIG-assessed, or deployment-qualified FIPS images.**
Go's pinned FIPS module and Keycloak's strict BCFIPS provider are configured.
The remaining assessment boundaries are recorded in [SECURITY-CONTROLS.md](SECURITY-CONTROLS.md).
Do not advertise compliance without completing that evidence. This matters on Railway,
where the underlying FIPS host and runtime controls have not been established.

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
Base distro major/minor upgrades and Go FIPS module upgrades require manual review.

Before publication, manually scan both architectures and resolve every vulnerability
with an available upstream fix. Findings with no fix — currently Debian base-OS
packages in both distroless images — are tracked in
`compliance/vulnerability-findings.csv`. The
only explicit exclusion is GO-2026-5932 on the gateway binary: the
advisory concerns OpenPGP, which is absent from its target-platform dependency graph.
Every gateway build and the smoke test enforce that absence. If OpenPGP is introduced,
the build fails before scanning. The evidence is retained in the image at
`/usr/share/ourimageshardened/packages.txt`. `.trivyignore-oauth2-proxy.yaml` scopes
the exclusion to that finding, package, and binary path; it is never applied to Keycloak.
Retain the unfiltered scan report with the release evidence. A clean scan does not
establish compliance.
The gateway applies explicitly pinned `golang.org/x/crypto` and gRPC security updates
from `go_security_updates` in the lock, verified through Go's checksum database.
These pins require review when upstream dependencies change. Keycloak also applies checksum-pinned
Netty 4.1.137.Final, OpenTelemetry API/context/common 1.62.0, and SQL Server JDBC
13.4.0.jre11 updates before augmentation. The exact artifacts are recorded in
`keycloak_security_updates`; review them when updating Keycloak. Keycloak's distroless
runtime leaves build tooling outside the final image. Upstream vulnerabilities with an
available fix must be taken before a release can publish. Signing, SBOM generation,
attestation, registry publication, and verification are operator responsibilities.

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

The local test and smoke commands verify locked build inputs and runtime behavior, but
they are not run automatically. The smoke test checks the fixed non-root identity,
that the image starts read-only with no
capabilities, the gateway's FIPS build flags and OpenPGP absence, and that Keycloak
reaches BCFIPS Approved Mode. It does not exercise OIDC login, database TLS, HTTP
routing, or the FIPS qualification of the host.

Before production, run the checklist in `DEPLOY-RAILWAY.md` against an isolated test
database and users. The supplied tests use no database container or production credentials.

## Attribution and disclaimer

These are unofficial rebuilds. Their only purpose is to rebuild the upstream
projects from locked, verified inputs so that vulnerabilities with an available
upstream fix are picked up promptly. No application code is forked or changed
beyond the checksum-pinned security updates recorded in `dependencies.lock.json`.

All rights, trademarks, and credit for the underlying software belong to their
respective projects and maintainers — oauth2-proxy (MIT), Keycloak (Apache-2.0),
the base images, the FIPS Go toolchain, BouncyCastle FIPS, and every bundled
library. Each stays under its own license inside the images. The full list is in
[THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md). This project is not affiliated
with, endorsed by, or supported by any of them, Red Hat, or the CNCF.

The original content of this repository — the Dockerfiles, scripts,
configuration, and documentation authored here — is **not open source and carries
no license**. It is published for transparency only; see [LICENSE](LICENSE). Do
not treat its availability as permission to reuse it, and do not treat anything in
it as production-ready. Ask first.

Nothing here has been formally assessed, audited, or certified by anyone. "Hardened"
describes the intent of the build choices — pinned inputs, distroless runtimes,
non-root read-only execution, prompt uptake of fixed CVEs — not a verified or
accredited state. There is no third-party review, no CMVP validation, and no
compliance claim. Treat every security property as unverified until you check it
yourself.

This repository and the images it produces are provided "as is", without warranty
of any kind. The maintainer accepts no responsibility or liability for any error,
vulnerability, misconfiguration, data loss, downtime, or damage arising from their
use. This is a personal project, built primarily for the maintainer's own
deployments and privacy needs. Anyone else using it is responsible for reviewing,
testing, and qualifying whatever they deploy.

This repository processes no personal data. Any privacy, data-protection, consent,
and terms-of-service obligations that arise from *running* Keycloak or oauth2-proxy
against real users belong entirely to whoever operates that deployment, not to
this repository or its maintainer.

Parts of this repository — code, configuration, and documentation — were produced
with the help of AI tools, including Claude and ChatGPT. It has not been
exhaustively reviewed line by line. The maintainer makes no guarantee of
correctness and is not responsible for any consequences of its use.
