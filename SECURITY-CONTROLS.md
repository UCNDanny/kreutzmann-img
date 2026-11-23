# Security scope and evidence

Status: **hardened; not assessed or certified**. The CIS Docker Benchmark image
controls (section 4) are met and self-checked; see `compliance/control-matrix.csv`.

CIS/STIG compliance is not a property inferred from a small image or a vulnerability
scan. FIPS validation concerns exact modules and their Security Policies, including
operating environments and approved use. No badges or compliance labels are emitted.

## Implemented image/runtime controls

| Control | Implementation | Boundary |
| --- | --- | --- |
| Fixed non-root identity | UID/GID 65532 gateway and OpenBao; 1000 Keycloak | Images and Compose |
| No web console | OpenBao built without the `ui` tag; smoke test fails on any build tag | Image |
| No build toolchain in final image | Multi-stage source builds | Images |
| Health check | `HEALTHCHECK` runs `/usr/bin/healthcheck` (FIPS build) against `HEALTHCHECK_URL` | Image; Railway uses its own health checks |
| No setuid/setgid files | Smoke test fails on any such file | Images |
| `COPY` only | Remote inputs fetched with `curl` and verified with `sha256sum` | Build stages |
| Read-only root filesystem | Compose and smoke test | Railway enforcement unverified |
| Dropped capabilities / no privilege escalation | Compose and smoke test | Railway enforcement unverified |
| Restricted temporary storage | Owned bounded tmpfs with noexec/nosuid/nodev | Compose and smoke test |
| Verified build inputs | Digest-pinned bases and checksum-pinned archives/JARs | Distroless runtime digests in dependencies.lock.json |
| Authenticated database TLS | Explicit JDBC verify-full + CA path | Requires live certificate/hostname test |
| Supply-chain evidence | Native builds, fix-available CVE gate at all severities, enforced OpenPGP non-applicability, Cosign signing + SBOM attestation on every image; GitHub-native SLSA provenance only on a public/Enterprise repo | GitHub Actions must run in user's repo |
| Public access boundary | Private upstreams, only gateway app domain | Operator must verify Railway exposure |

`compliance/control-matrix.csv` maps these controls to the CIS Docker Benchmark section 4
identifiers with their evidence. Before an assessment, confirm the benchmark revision and
have the rows checked independently; host, daemon and runtime sections are out of image scope.
Host requirements do not become image requirements simply because an OS is in the image.
Do not add host daemons or kernel settings to a distroless image to appease a scanner.

## Cryptography

- oauth2-proxy, OpenBao and the health check build with `GOFIPS140=v1.0.0` and
  `CGO_ENABLED=0`, which turns FIPS mode on by default. Go Cryptographic Module v1.0.0 is
  FIPS 140-3 validated under CMVP certificate 5247 (active as of November 2026). Check its
  Security Policy against the actual operating environment before use in an assessed system.
- Go's module mode does not prove every oauth2-proxy or OpenBao dependency or operation is inside
  that module's boundary. A complete cryptographic call-path audit is outstanding.
  Do not use `GODEBUG=fips140=only` as a production substitute for that assessment.
- Keycloak uses the BCFIPS versions declared by the pinned release POM and strict
  mode. The smoke test confirms `Approved Mode` initialization before an intentional
  unreachable-database exit; it does not claim a working database-backed login or an
  assessed host.
- BCFIPS uses its Java implementation on both architectures so AMD64 does not
  extract executable JNI libraries into the non-executable `/tmp` mount.
- Keycloak's supported FIPS setup has JVM and host requirements. `FIPS-JVM: unknown`
  on a non-qualified host is **not a passing compliance result**, even if the BCFIPS
  provider reports Approved Mode.
- BCFIPS certificate applicability, Java build, other crypto providers, JDBC TLS,
  AMD64/ARM64 environments, and Railway's host/edge/database remain unassessed.
- A Let's Encrypt server certificate does not establish FIPS qualification of the TLS
  implementation serving it. Define whether the external edge/database are in scope.

Do not auto-upgrade cryptographic module identities under an existing validation claim.
A dependency PR may update BCFIPS versions to match Keycloak, but requires human review
of the corresponding certificates and operating conditions. If the combination cannot
be qualified on Railway, the deployment cannot be called compliant there.

## Required assessment records

Record benchmark/STIG version, control ID, scope, implementation, evidence, status,
owner, and exception expiry. `not assessed` is not `pass`; `not applicable` needs a
rationale. Scan results alone do not complete manual/operational controls. Qualify each
architecture independently on a permitted operating environment; QEMU is only a build
and functional test aid.

Sources:

- https://www.cisecurity.org/benchmark/docker
- https://www.cyber.mil/stigs/downloads/
- https://dl.dod.cyber.mil/wp-content/uploads/devsecops/pdf/Final_DevSecOps_Enterprise_Container_Hardening_Guide_1.2.pdf
- https://go.dev/doc/security/fips140
- https://www.keycloak.org/server/fips
- https://csrc.nist.gov/projects/cryptographic-module-validation-program/validated-modules/search
- https://jdbc.postgresql.org/documentation/ssl/
- https://docs.railway.com/networking/private-networking
