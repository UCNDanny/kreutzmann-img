# Release scan status — 2026-09-06

The GitHub Actions workflow is configured, but publication is currently blocked
by Keycloak's Trivy findings. It has not been run in a GitHub repository yet.

| Image | Architecture | Release scan |
| --- | --- | --- |
| kreutzmann-img/oauth2-proxy | AMD64 and ARM64 | Pass with the single enforced OpenPGP non-applicability exclusion |
| kreutzmann-img/keycloak | AMD64 and ARM64 | Blocked: 52 package findings, representing 34 distinct advisory IDs |

Keycloak's findings comprise 4 high, 30 medium, and 18 low package findings.
Trivy 0.74.0 reports no fixed versions for them; the workflow's Trivy 0.69.3 also
reports 52 findings on ARM64. The Java dependencies have no reported findings.
The current distroless Java 21 base digest was checked and still matches the lock:
`sha256:bb0b3c7edc4417acdf76ea0f52bb5fae28881fe05aae6cc55af4cc4cb0200d2d`.

The affected package names are libbz2-1.0, libc-bin, libc6, libexpat1, liblcms2-2,
libpng16-16t64, libuuid1, and zlib1g. Some advisories describe utilities rather than
the library delivered in this image. That requires an advisory-specific assessment;
it is not grounds to ignore all unfixed findings or the entire package.

Docker Scout reported zero findings for Keycloak. That scanner-specific result
does not mean every scanner agrees or that the image is vulnerability-free.

Before publication, resolve applicable findings through upstream patches, or add
individually justified non-applicability evidence and enforce its assumptions.
Do not disable the all-severity gate merely to publish. The workflow preserves
unfiltered JSON reports as scan artifacts, including when its release gate fails.

Both images pass the hardening smoke test: fixed non-root identity, start-up under the
read-only/no-capability restrictions, and FIPS build posture (gateway) / BCFIPS Approved
Mode (Keycloak). Database-backed login and production deployment have not been tested.
