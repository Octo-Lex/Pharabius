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


# S02 — Repository List and Repository Dashboard

Risk: Medium-high  
Slice type: frontend product MVP  
Artifact impact: frontend UI, minor backend response-shape fixes if needed

## Scope

Implement the repository list page and repository dashboard page against the existing backend APIs.

This slice should allow users to browse repositories created by uploaded artifact bundles and inspect latest run summary details.

## Goals

- Add repository list page.
- Add repository dashboard page.
- Show latest severity counts.
- Show latest run metadata where available.
- Show gate status where available.
- Show last uploaded timestamp.
- Link to findings page.
- Show empty state when no repositories exist.
- Show error state when API fails.

## Patch Set

Expected files:

```text
platform/frontend/src/pages/HomePage.tsx
platform/frontend/src/pages/RepositoryPage.tsx
platform/frontend/src/components/RepositoryTable.tsx
platform/frontend/src/components/SeveritySummary.tsx
platform/frontend/src/components/GateStatusBadge.tsx
platform/frontend/src/components/RunMetadataCard.tsx
platform/frontend/src/api/client.ts
platform/frontend/src/api/types.ts
```

Backend changes allowed only if necessary:

```text
platform/backend/src/pharabius_platform/api/repositories.py
platform/backend/src/pharabius_platform/schemas/*.py
```

## UI Requirements

Repository list columns:

```text
Repository
Latest run
Critical
High
Medium
Low
Gate
Readiness
Last uploaded
```

Repository dashboard cards:

```text
Latest gate result
Severity summary
Latest run metadata
Readiness status
Links to findings and portfolio
```

## Tests

Add tests/static checks for:

- Repository list calls `GET /api/v1/repositories`.
- Empty repository state renders.
- Repository table renders rows.
- Repository dashboard calls `GET /api/v1/repositories/{id}`.
- Severity counts render correctly.
- Gate status badge renders pass/fail/unknown.
- API error displays request ID when available.

## Expected Behavior

Users can open the platform and see uploaded repositories, then click into a repository dashboard.

## Acceptance Criteria

- Repository list is usable.
- Repository dashboard is usable.
- Empty and error states work.
- Backend response-shape changes, if any, are backward-compatible.
- No new backend product capability is added.

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
