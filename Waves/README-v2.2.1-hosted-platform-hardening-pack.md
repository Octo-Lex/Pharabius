# v2.2.1 — Hosted Platform Hardening & UX Polish

Goal: Harden the hosted platform after the v2.2.0 category shift by improving upload diagnostics, platform health checks, API error consistency, frontend empty/error states, Docker/deployment documentation, and storage safety.

Release posture: patch release, not feature release.

Core boundary:
- No new product capability beyond hosted-platform hardening
- No GitHub OAuth
- No RBAC/user-account expansion
- No policy engine
- No tracker writes
- No PR comments
- No issue creation
- No SARIF upload
- No repository cloning
- No remediation
- No source-code modification


## Pack contents

| Slice | File | Purpose |
|---|---|---|
| S01 | `S01-upload-diagnostics-validation-report-readability.md` | Improve upload diagnostics and validation reports |
| S02 | `S02-platform-health-readiness-storage-checks.md` | Add deeper health/readiness/storage checks |
| S03 | `S03-api-error-envelope-request-id-consistency.md` | Ensure consistent API error envelopes and request IDs |
| S04 | `S04-frontend-empty-loading-error-states.md` | Polish frontend empty/loading/error states |
| S05 | `S05-docker-deployment-backup-docs.md` | Improve Docker, deployment, backup, and storage docs |
| S06 | `S06-docs-tests-changelog-release.md` | Final docs, changelog, release checklist |

## Recommended branch

```text
roadmap/v2.2.1-hosted-platform-hardening
```

## Recommended release headline

```text
Pharabius v2.2.1 hardens the hosted platform with clearer upload diagnostics, health and storage checks, consistent API errors, frontend UX states, and deployment documentation while preserving artifact-only, no-external-write behavior.
```

## Patch-release principle

v2.2.1 should make v2.2.0 safer and easier to operate. It should not broaden the platform into OAuth, policies, tracker writes, repository crawling, background processing, or remediation.
