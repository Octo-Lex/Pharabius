# v2.2.4 — Repository Identity & Upload UX Patch

Goal: Fix repository identity handling so uploaded bundles produce human-readable repository names across backend persistence, frontend display, and `ai-debt upload`.

Release posture: focused patch release. This release should fix the hash-named repository usability problem without adding new product capability.

Core boundaries:
- No OAuth
- No RBAC
- No API key management UI
- No claims/gaps/readiness UI
- No policy engine
- No tracker writes
- No PR comments
- No repository cloning
- No remediation
- No source-code modification


## Pack contents

| Slice | File |
|---|---|
| S01 | `S01-backend-repository-name-resolution-slug-rules.md` |
| S02 | `S02-upload-api-cli-repository-name-propagation.md` |
| S03 | `S03-frontend-upload-display-polish.md` |
| S04 | `S04-regression-tests-docs-release.md` |

## Recommended branch

```text
roadmap/v2.2.4-repository-identity-upload-ux
```

## Recommended release headline

```text
Pharabius v2.2.4 improves hosted platform repository identity by preserving human-readable repository names through browser upload, API upload, and ai-debt upload.
```

## Problem statement

The hosted platform currently may display repositories using a content-hash fallback, for example:

```text
6bcbe18c41c2
```

That is technically deterministic but poor for first-time usability. The platform should prefer explicit or artifact-derived repository names and use the hash only as a last resort.

## Required repository-name priority

```text
1. Explicit repository_name form field from upload request
2. repository_name passed by ai-debt upload
3. Artifact-derived project/repository name from .ai-debt metadata
4. Git remote-derived name if available in metadata
5. Current directory name from CLI upload
6. Content hash fallback
```

## Non-goals

```text
OAuth
RBAC
policy engine
tracker writes
browser E2E
repository cloning
source upload
claims/gaps views
API key management UI
```
