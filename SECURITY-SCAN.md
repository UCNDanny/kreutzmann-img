# Release scan status — 2026-09-06

The release workflow blocks any image that has a vulnerability with an available
upstream fix, at every severity (`ignore-unfixed` is set on the gate). Findings with
no fix are recorded but do not gate the release.

| Image | Architecture | Release gate |
| --- | --- | --- |
| kreutzmann-img/oauth2-proxy | AMD64 and ARM64 | Pass. One enforced non-applicability exclusion: GO-2026-5932 (OpenPGP). |
| kreutzmann-img/keycloak | AMD64 and ARM64 | Pass. 52 unfixed Debian base-OS findings, carried and tracked below. |

## Keycloak base-OS findings (no upstream fix)

Trivy 0.69.3 reports 52 findings on each architecture: 4 high, 30 medium, 18 low. All
are in the distroless Java 21 Debian 13 base image; `keycloak.jar` and the other Java
dependencies report zero. Trivy 0.74.0 also reports no fixed versions. The base digest
matches the lock:
`sha256:bb0b3c7edc4417acdf76ea0f52bb5fae28881fe05aae6cc55af4cc4cb0200d2d`.

Affected packages include libbz2-1.0, libc-bin, libc6, libexpat1, liblcms2-2,
libpng16-16t64, libuuid1, and zlib1g. The full list per run is in the workflow's scan
artifacts; the tracked register is `compliance/vulnerability-findings.csv`. Some
advisories describe utilities rather than the library delivered here; an
advisory-specific assessment is still owed before any compliance claim.

These are carried, not dismissed:

- `python3 scripts/dependencies.py --update` refreshes the base digest. A release with
  patched packages ships automatically once upstream publishes them.
- Every workflow run uploads the unfiltered JSON report as a scan artifact, including
  when the gate fails on a fixable finding.
- Review `compliance/vulnerability-findings.csv` when updating the base image.
- Docker Scout reports zero findings for Keycloak. One scanner's result does not mean
  every scanner agrees or that the image is vulnerability-free.

Do not widen the gate to ignore fixable findings, and do not add blanket
`.trivyignore` entries without individually justified non-applicability evidence.

## Smoke test

Both images pass the hardening smoke test: fixed non-root identity, start-up under the
read-only/no-capability restrictions, and FIPS build posture (gateway) / BCFIPS Approved
Mode (Keycloak). Database-backed login and production deployment have not been tested.
