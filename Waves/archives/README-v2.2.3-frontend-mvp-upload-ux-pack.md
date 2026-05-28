# v2.2.3 — Frontend MVP & Upload UX

Goal: Replace the static frontend scaffold with a minimal usable UI for upload, repository browsing, findings, and portfolio summary, using the now-runtime-validated backend APIs.

Release posture: hosted-platform frontend MVP release. This release should make the platform usable through the browser, but it must not add OAuth, RBAC, policy engine, tracker writes, PR comments, background workers, or remediation.

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
- Backend changes limited to API shape fixes required by the frontend


## Pack contents

| Slice | File |
|---|---|
| S01 | `S01-frontend-dependency-routing-api-client.md` |
| S02 | `S02-repository-list-dashboard.md` |
| S03 | `S03-findings-table-basic-filters.md` |
| S04 | `S04-upload-page-validation-feedback.md` |
| S05 | `S05-portfolio-summary-empty-error-states.md` |
| S06 | `S06-docs-frontend-build-changelog-release.md` |

## Recommended branch

```text
roadmap/v2.2.3-frontend-mvp-upload-ux
```

## Recommended release headline

```text
Pharabius v2.2.3 replaces the hosted platform’s static frontend scaffold with a minimal usable UI for uploads, repository browsing, findings, and portfolio summaries.
```

## Product definition

v2.2.3 should prove this browser flow:

```text
Open platform frontend
→ see repository list or empty state
→ upload .ai-debt bundle with token
→ see validation result
→ navigate to repository dashboard
→ inspect findings
→ view portfolio summary
```

## Non-goals

```text
OAuth
RBAC
policy engine
tracker writes
PR comments
background workers
mobile-first design
formal browser E2E suite unless easy
```
