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


# S04 — Upload Page and Repository Dashboard UI

Risk: Medium-high  
Slice type: frontend product MVP  
Artifact impact: frontend UI and backend API polish if needed

## Scope

Implement the first two usable platform screens: Upload Page and Repository Dashboard.

The upload page should support manual `.ai-debt` bundle upload using the existing backend upload API. The repository dashboard should display latest persisted repository/run summary.

## Goals

- Add manual upload form.
- Support admin token or upload token input.
- Show validation result after upload.
- Show bundle ID, hash, and parsed counts where available.
- Add repository list.
- Add repository dashboard.
- Show severity counts, latest run, gate result, and uploaded time.
- Keep source-derived-content warning visible before upload.

## Patch Set

Expected files:

```text
platform/frontend/src/pages/UploadPage.tsx
platform/frontend/src/pages/HomePage.tsx
platform/frontend/src/pages/RepositoryPage.tsx
platform/frontend/src/components/SeveritySummary.tsx
platform/frontend/src/components/GateStatusBadge.tsx
platform/frontend/src/components/UploadWarning.tsx
platform/frontend/src/api/client.ts
platform/docs/frontend-mvp.md
```

Required upload warning:

```text
.ai-debt bundles may contain source-derived evidence snippets, file paths, hashes, and analysis metadata. Upload only to a trusted Pharabius platform instance.
```

## Tests

Add tests or static checks for:

- Upload page includes source-derived-content warning.
- Upload page calls `/api/v1/bundles`.
- Upload success state displays validation summary.
- Repository list calls `/api/v1/repositories`.
- Repository dashboard calls `/api/v1/repositories/{id}`.
- Severity summary renders Critical/High/Medium/Low counts.
- Empty repository state is visible.

## Expected Behavior

A user can open the frontend, upload a bundle, and navigate to a repository summary screen.

## Acceptance Criteria

- Upload page is functional.
- Repository dashboard is functional.
- Source-derived-content warning is visible.
- UI handles upload success and upload failure.
- No source repository cloning or external API call is introduced.

## Guardrails

- Preserve the v2.2.1 platform persistence model.
- Do not add external tracker writes.
- Do not add PR comments, GitHub Checks API, or issue creation.
- Do not add repository cloning.
- Do not require source-code upload.
- Do not introduce policy engine behavior.
- Do not add remediation or patch generation.
- Keep frontend MVP focused on upload, repository summary, findings, and portfolio state.
- Keep Docker/PostgreSQL validation practical and repeatable.


## Verification Commands

Run the standard gates plus platform-specific checks:

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
docker compose -f platform/docker-compose.yml config
```

When Docker is available for runtime validation:

```bash
docker compose -f platform/docker-compose.yml up --build -d
curl -f http://localhost:8000/api/v1/health
curl -f http://localhost:3000/
docker compose -f platform/docker-compose.yml down -v
```
