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


# S05 — Portfolio/Finding Views and Frontend Error States

Risk: Medium-high  
Slice type: frontend product MVP / UX hardening  
Artifact impact: frontend UI

## Scope

Implement the Portfolio Summary and Findings Table views, and add consistent empty/loading/error states across all MVP screens.

## Goals

- Add findings table with basic filters.
- Add portfolio summary table.
- Add empty states for no uploads/no findings/no portfolio data.
- Add loading states for API calls.
- Add error states with request ID if backend returns one.
- Add simple gate/trend display where data exists.
- Keep UI desktop-oriented; mobile responsiveness is not required.

## Patch Set

Expected files:

```text
platform/frontend/src/pages/FindingsPage.tsx
platform/frontend/src/pages/PortfolioPage.tsx
platform/frontend/src/components/FindingsTable.tsx
platform/frontend/src/components/PortfolioSummary.tsx
platform/frontend/src/components/EmptyState.tsx
platform/frontend/src/components/ErrorState.tsx
platform/frontend/src/components/LoadingState.tsx
platform/frontend/src/components/FilterBar.tsx
```

Recommended findings columns:

```text
Finding ID
Priority
Category
Title
Risk Score
Confidence
```

Recommended portfolio columns:

```text
Repository
Latest Run
Critical
High
Medium
Low
Gate
Readiness
Last Uploaded
```

## Tests

Add tests/build checks for:

- Findings page calls findings API.
- Findings table renders rows.
- Findings table supports severity/category filter params.
- Portfolio page calls portfolio API.
- Empty states render when arrays are empty.
- Error state renders backend error message and request ID.
- Loading state renders before data resolves.

## Expected Behavior

The frontend becomes minimally useful for reviewing uploaded repository findings and portfolio summaries.

## Acceptance Criteria

- Findings table is usable.
- Portfolio page is usable.
- Empty/loading/error states exist across MVP views.
- Backend request IDs are surfaced when available.
- No charts are required.
- No claims/gaps dedicated frontend pages are required.

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
