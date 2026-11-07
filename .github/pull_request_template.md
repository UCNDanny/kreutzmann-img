## Before opening this pull request

- [ ] `make check` passed: every image on `linux/arm64` and `linux/amd64` (unit tests, build, smoke test, vulnerability gate)
- [ ] Every changed input in `dependencies.lock.json` is reviewed, and its Dockerfile `ARG` defaults match the lock
- [ ] New unfixed findings are recorded in `compliance/vulnerability-findings.csv`; `SECURITY-SCAN.md` matches the gate
- [ ] A new or renamed image is in every matrix in `release.yml`, in `monitor.yml`, and in the README
