# Third-party notices

The container images produced by this repository bundle software written and
owned by other people. All credit, copyright, and trademark rights for that
software belong to its respective authors and projects. This repository only
rebuilds it from locked, verified inputs so that fixed vulnerabilities are
picked up promptly; it does not fork or modify the applications beyond the
checksum-pinned security updates recorded in `dependencies.lock.json`.

This project is not affiliated with, endorsed by, or supported by any of the
projects below, Red Hat, the CNCF, the Cloud Native Computing Foundation, or the
Eclipse Foundation.

Exact versions, source URLs, and checksums for every component are in
`dependencies.lock.json`. Each published image also carries an SBOM listing its
full dependency set; consult it for the transitive libraries that upstream
projects vendor.

## Applications

| Component | Upstream | License |
| --- | --- | --- |
| oauth2-proxy | https://github.com/oauth2-proxy/oauth2-proxy | MIT |
| Keycloak | https://github.com/keycloak/keycloak | Apache License 2.0 |

oauth2-proxy vendors many Go modules and Keycloak bundles many Java libraries;
those retain their own licenses (variously MIT, BSD, Apache-2.0, EPL, and
others). The per-image SBOM is the authoritative list.

## Pinned security updates and crypto providers

| Component | Upstream | License |
| --- | --- | --- |
| Bouncy Castle FIPS (`bc-fips`, `bctls-fips`, `bcpkix-fips`, `bcutil-fips`) | https://www.bouncycastle.org/fips-java/ | Bouncy Castle Licence (MIT-style) |
| Go FIPS cryptographic module | https://github.com/golang-fips/openssl | Apache License 2.0 / BSD-3-Clause |
| `golang.org/x/crypto` | https://cs.opensource.google/go/x/crypto | BSD-3-Clause |
| gRPC-Go (`google.golang.org/grpc`) | https://github.com/grpc/grpc-go | Apache License 2.0 |
| Netty | https://github.com/netty/netty | Apache License 2.0 |
| OpenTelemetry Java (`opentelemetry-api`, `-context`, `-common`) | https://github.com/open-telemetry/opentelemetry-java | Apache License 2.0 |
| Microsoft JDBC Driver for SQL Server (`mssql-jdbc`) | https://github.com/microsoft/mssql-jdbc | MIT |

## Base images

| Base | Source | Notes |
| --- | --- | --- |
| `golang:*-bookworm` (build stage) | https://hub.docker.com/_/golang | Go toolchain (BSD-3-Clause) on Debian; Debian packages under their own licenses |
| `gcr.io/distroless/static-debian13` | https://github.com/GoogleContainerTools/distroless | Debian userland fragments under their own licenses |
| `gcr.io/distroless/java21-debian13` | https://github.com/GoogleContainerTools/distroless | OpenJDK (GPLv2 with Classpath Exception) on Debian |
| `registry.access.redhat.com/ubi9/ubi-minimal` (Keycloak build stage only) | https://catalog.redhat.com/software/base-images | Red Hat Universal Base Image EULA; not present in the final runtime image |
| `alpine:*` (CA-certificate stage) | https://hub.docker.com/_/alpine | Alpine packages under their own licenses (mostly MIT/BSD) |

The full text of each license is distributed with the corresponding component
inside the image and/or is available at the source links above.
