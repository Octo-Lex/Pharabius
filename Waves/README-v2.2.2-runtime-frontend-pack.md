# v2.2.2 — Platform Runtime Validation & Frontend MVP

Goal: Verify the hosted platform against a real PostgreSQL/Docker runtime and replace the static frontend scaffold with a minimal usable UI for upload, repository view, findings, and portfolio summary.

Release posture: hosted-platform hardening release. This release should make the v2.2 platform demonstrably runnable and minimally usable, without adding governance, tracker, remediation, or automation scope.

Core boundaries:
- No GitHub OAuth
- No RBAC
- No policy engine
- No tracker writes
- No PR comments
- No background workers
- No source-code upload by default
- No autonomous remediation
- No production code modification


## Pack contents

| Slice | File |
|---|---|
| S01 | `S01-docker-compose-runtime-smoke-test.md` |
| S02 | `S02-real-postgresql-integration-test-path.md` |
| S03 | `S03-frontend-mvp-routes-and-api-client.md` |
| S04 | `S04-upload-page-and-repository-dashboard-ui.md` |
| S05 | `S05-portfolio-finding-views-and-error-states.md` |
| S06 | `S06-docs-limitations-changelog-release.md` |

## Recommended branch

```text
roadmap/v2.2.2-runtime-frontend-mvp
```

## Recommended release headline

```text
Pharabius v2.2.2 validates the hosted platform against a real Docker/PostgreSQL runtime and adds a minimal usable frontend for upload, repositories, findings, and portfolio summaries.
```

## Product definition

v2.2.2 should prove this loop:

```text
docker compose up
→ backend and frontend start
→ PostgreSQL is reachable
→ sample .ai-debt bundle uploads
→ records persist in PostgreSQL
→ repository and portfolio APIs return data
→ frontend shows upload, repository, findings, and portfolio screens
```
