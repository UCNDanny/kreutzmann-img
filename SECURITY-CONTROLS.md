# Security scope and evidence

Status: **hardened engineering builds; compliance assessment incomplete**.

CIS/STIG compliance is not a property inferred from a small image or a vulnerability
scan. FIPS validation concerns exact modules and their Security Policies, including
operating environments and approved use. No badges or compliance labels are emitted.

## Implemented image/runtime controls

| Control | Implementation | Boundary |
| --- | --- | --- |
| Fixed non-root identity | UID/GID 65532 gateway; 1000 Keycloak | Images and Compose |
| No build toolchain in final image | Multi-stage source builds | Images |
| Read-only root filesystem | Compose and smoke test | Railway enforcement unverified |
| Dropped capabilities / no privilege escalation | Compose and smoke test | Railway enforcement unverified |
| Restricted temporary storage | Owned bounded tmpfs with noexec/nosuid/nodev | Compose and smoke test |
| Verified build inputs | Digest-pinned bases and checksum-pinned archives/JARs | Distroless runtime digests in dependencies.lock.json |
| Authenticated database TLS | Explicit JDBC verify-full + CA path | Requires live certificate/hostname test |
| Supply-chain evidence | Native builds, fix-available CVE gate at all severities, enforced OpenPGP non-applicability, Cosign signing + SBOM attestation on every image; GitHub-native SLSA provenance only on a public/Enterprise repo | GitHub Actions must run in user's repo |
| Public access boundary | Private upstreams, only gateway app domain | Operator must verify Railway exposure |

These are descriptive engineering controls, not invented CIS/STIG control IDs.
Before making a compliance claim select the exact benchmark/STIG revisions, populate
`compliance/control-matrix.csv` with their real identifiers, and collect evidence.
Host requirements do not become image requirements simply because an OS is in the image.
Do not add host daemons or kernel settings to a distroless image to appease a scanner.

## Cryptography

- oauth2-proxy builds with `GOFIPS140=v1.0.0` and `CGO_ENABLED=0`. Go documents module
  v1.0.0 under CMVP certificate 5247. Verify its current status and Security Policy
  against the actual operating environment before use in an assessed system.
- Go's module mode does not prove every oauth2-proxy dependency or operation is inside
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
