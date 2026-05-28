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


# S05 — Portfolio Summary and Frontend Empty/Error States

Risk: Medium-high  
Slice type: frontend portfolio MVP / UX hardening  
Artifact impact: frontend UI

## Scope

Implement the portfolio summary page and apply consistent empty/loading/error states across all MVP screens.

The portfolio view should summarize repositories, severity distribution, gate status, and readiness where available.

## Goals

- Add portfolio summary page.
- Show aggregate severity counts.
- Show repository rollup table.
- Show gate/readiness status where available.
- Add consistent empty states across pages.
- Add consistent loading states across pages.
- Add consistent error states with request ID.
- Add minimal frontend troubleshooting guidance.

## Patch Set

Expected files:

```text
platform/frontend/src/pages/PortfolioPage.tsx
platform/frontend/src/components/PortfolioSummary.tsx
platform/frontend/src/components/SeveritySummary.tsx
platform/frontend/src/components/EmptyState.tsx
platform/frontend/src/components/ErrorState.tsx
platform/frontend/src/components/LoadingState.tsx
platform/frontend/src/components/GateStatusBadge.tsx
platform/frontend/src/api/client.ts
platform/frontend/src/api/types.ts
```

Portfolio table columns:

```text
Repository
Critical
High
Medium
Low
Gate
Readiness
Last uploaded
```

## Tests

Add tests/static checks for:

- Portfolio page calls `GET /api/v1/portfolio`.
- Portfolio summary renders aggregate counts.
- Empty portfolio state renders.
- Error state renders backend request ID.
- Loading state exists.
- All MVP pages use shared empty/loading/error components.

## Expected Behavior

A user can see a cross-repository summary and understand empty/error states without reading backend logs.

## Acceptance Criteria

- Portfolio summary is usable.
- Empty/loading/error state coverage exists.
- Request IDs are surfaced in error UI.
- No charts are required.
- No policy engine or org governance is introduced.

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
