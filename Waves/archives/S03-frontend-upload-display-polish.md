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


# S03 — Frontend Upload and Display Polish

Risk: Low-medium  
Slice type: frontend usability patch  
Artifact impact: upload page, repository list, repository dashboard

## Scope

Update the frontend so users can provide a repository name during manual upload and see clear repository identity in list/dashboard views.

## Goals

- Add repository name input to upload page.
- Explain that repository name controls dashboard display.
- Preserve artifact sensitivity warning.
- Display human-readable `Repository.name` in repository list.
- Display human-readable `Repository.name` in repository dashboard title.
- Label hash fallback clearly if used.
- Avoid showing raw hash as the primary name when better metadata exists.

## Patch Set

Expected files:

```text
platform/frontend/src/pages/UploadPage.tsx
platform/frontend/src/pages/HomePage.tsx
platform/frontend/src/pages/RepositoryPage.tsx
platform/frontend/src/components/RepositoryTable.tsx
platform/frontend/src/components/UploadWarning.tsx
platform/frontend/src/api/client.ts
platform/frontend/src/api/types.ts
platform/docs/frontend-mvp.md
```

Recommended upload helper text:

```text
Repository name controls how this bundle appears in the dashboard.
Use a stable name such as "Pharabius" or "my-service-api".
```

Fallback display:

```text
Unknown repository · 6bcbe18c41c2
```

## Tests

Add tests/static checks for:

- Upload page includes repository name input.
- Upload page sends `repository_name` with upload request.
- Repository list displays `name`, not slug/hash, as primary label.
- Repository dashboard title displays `name`.
- Hash fallback is labeled as unknown/fallback.
- Upload warning remains visible.

## Expected Behavior

Users no longer see hash-only repository names when they provide a name.

## Acceptance Criteria

- Repository name input exists.
- Upload request includes repository name.
- Repository list/dashboard display human-readable names.
- Hash fallback is clearly labeled.
- No new auth, RBAC, or external integration is added.

## Guardrails

- Keep this patch narrow.
- Do not change the hosted platform’s persistence model beyond repository identity resolution.
- Do not add external writes.
- Do not add authentication UI, OAuth, RBAC, policy engine, tracker writes, or remediation.
- Preserve the content-hash fallback only as a last resort.
- Preserve duplicate bundle handling.
- Keep source-derived artifact warnings intact.


## Verification Commands

Run:

```bash
ruff format --check .
ruff check .
mypy src
lint-imports
pytest
pytest platform/backend/tests
npm --prefix platform/frontend run build
python -m build
python scripts/validate_repo.py .
```

Optional runtime check:

```bash
platform/scripts/smoke_docker_compose.sh
```
