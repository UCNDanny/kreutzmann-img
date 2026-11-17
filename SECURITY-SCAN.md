# Release scan status — 2026-11-17

Trivy **0.76.2** is pinned in `dependencies.lock.json` and used by release CI,
monitoring and local preflight. The release gate blocks vulnerabilities with an
available upstream fix at every severity (`ignore-unfixed`). A passing gate does
not mean that no vulnerabilities exist.

The current upstream application releases are oauth2-proxy **7.15.6**, Keycloak
**26.8.2** and OpenBao **2.7.2**. Their versions and base-image digests were checked
against upstream on this date; no newer stable inputs were available.

## Current findings

Unfiltered scans of the rebuilt images report:

| Image | Findings | Fixable findings | Remaining scope |
| --- | --- | --- | --- |
| oauth2-proxy | 0 | 0 | None reported. |
| Keycloak | 87 | 0 | Debian 13 base packages: 8 high, 50 medium, 23 low, 6 unknown. No Java-library findings. |
| OpenBao | 3 | 0 | `github.com/go-jose/go-jose/v3` v3.0.5: 1 high, 2 medium. |

The current findings replace the older RPM/base-image entries in
`compliance/vulnerability-findings.csv`. Scan results are a dated snapshot, not a
permanent clean bill of health. The published-image monitor checks both AMD64 and
ARM64; it scans published `:latest` images, not the deployment inventory. Production
operators must explicitly deploy reviewed image digests after release.

Keycloak's Java 21 distroless base is pinned at
`sha256:6b60e44d652d66a9e2e584364c96adac4df7133674b2834b6f71741b7cdb1ff3`.
OpenBao's remaining findings are CVE-2026-116585, CVE-2026-116586 and
CVE-2026-116587. No upstream fix is reported for its v3 dependency; the separately
pinned v4 dependency does not remove v3 from the binary.

## Detection and patching

- Every six hours, the monitor scans all three published images on both platforms
  and reports upstream changes and fixable findings in one standing monitor issue.
- The update job proposes verified upstream releases, base-image digests, all five
  Go security pins and the scanner version in one PR. It dispatches all six native
  build/smoke/scan checks on the candidate branch. Review their outcome before merging.
- Java and Debian replacement pins still require a human to select and review
  them. A new upstream release that changes an overridden library fails the build
  until the override is reviewed. Go FIPS module changes remain manual as well.
- Neither PR approval, merging nor production deployment is automated.
- Release jobs preserve the unfiltered JSON scan artifact even when the gate fails.

The GO-2026-5932 OpenPGP exclusions remain limited to the two Go binary paths and
package. Both builds enforce that OpenPGP is absent from their target dependency
graphs. No exclusions were widened for this update. Do not ignore fixable findings
or equate a scanner result with FIPS, CIS or STIG compliance.

## Validation boundary

`make check` builds, smoke-tests and scans every image on ARM64 and AMD64. Smoke
tests check the fixed non-root identity, restricted runtime startup and the Go FIPS
or BCFIPS posture. They do not exercise database-backed login or production traffic.
