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


# S04 — Upload Page with Validation Feedback

Risk: Medium-high  
Slice type: frontend upload workflow  
Artifact impact: frontend UI and upload API client

## Scope

Implement the upload page for manual `.ai-debt` bundle uploads, with clear validation feedback and warnings about source-derived artifacts.

The upload page should call the existing backend upload endpoint and display the returned bundle ID, content hash, validity, warnings, and parsed counts where available.

## Goals

- Add manual file upload form.
- Support admin token or upload token input.
- Support optional repository name field if backend accepts it.
- Show source-derived artifact warning before upload.
- Show upload progress or loading state.
- Show validation report after upload.
- Show upload error with request ID when available.
- Link to repository list after successful upload.

## Patch Set

Expected files:

```text
platform/frontend/src/pages/UploadPage.tsx
platform/frontend/src/components/UploadWarning.tsx
platform/frontend/src/components/ValidationReport.tsx
platform/frontend/src/components/TokenInput.tsx
platform/frontend/src/api/client.ts
platform/frontend/src/api/types.ts
platform/docs/frontend-mvp.md
```

Required warning text:

```text
.ai-debt bundles may contain source-derived evidence snippets, file paths, hashes, and analysis metadata. Upload only to a trusted Pharabius platform instance.
```

## Tests

Add tests/static checks for:

- Upload warning is visible.
- Upload page accepts file input.
- Upload page includes token input.
- Upload page calls `POST /api/v1/bundles`.
- Upload success displays bundle ID/hash/validation status.
- Upload failure displays backend error message and request ID.
- Upload page does not imply source repository upload.

## Expected Behavior

A user can upload a `.ai-debt` bundle from the browser and understand whether validation succeeded.

## Acceptance Criteria

- Upload page is usable.
- Validation feedback is visible.
- Sensitive-artifact warning is visible.
- Errors are actionable.
- No automatic external calls are added.

## Guardrails

- Preserve the v2.2.2 runtime-validated backend path.
- Do not introduce new backend product capability except minor API response-shape fixes needed by the UI.
- Do not add external writes.
- Do not add repository cloning or source-code upload.
- Do not add OAuth, RBAC, policy engine, tracker writes, PR comments, or remediation.
- Keep frontend MVP desktop-oriented.
- Keep charts optional; tables and summary cards are sufficient.
- Make empty/loading/error states explicit and useful.
- Keep source-derived artifact warning visible on upload.


## Verification Commands

Run the standard gates plus frontend-specific checks:

```bash
ruff format --check .
ruff check .
mypy src
lint-imports
pytest
python -m build
python scripts/validate_repo.py .
pytest platform/backend/tests
npm --prefix platform/frontend install
npm --prefix platform/frontend run build
```

Optional runtime verification when Docker is available:

```bash
platform/scripts/smoke_docker_compose.sh
```
