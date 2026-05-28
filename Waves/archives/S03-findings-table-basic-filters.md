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


# S03 — Findings Table with Basic Filters

Risk: Medium-high  
Slice type: frontend product MVP  
Artifact impact: frontend UI, minor API query-polish if needed

## Scope

Implement the findings table for a repository with basic filtering and readable finding metadata.

Pagination is optional for v2.2.3 because backend list endpoints currently return full results. The UI should still be structured so pagination can be added later.

## Goals

- Add findings page.
- Render findings table.
- Support basic client-side or API-backed filters for severity and category.
- Show priority, category, risk score, confidence, and title.
- Link back to repository dashboard.
- Show empty state when no findings exist.
- Show error/loading states.

## Patch Set

Expected files:

```text
platform/frontend/src/pages/FindingsPage.tsx
platform/frontend/src/components/FindingsTable.tsx
platform/frontend/src/components/FilterBar.tsx
platform/frontend/src/components/PriorityBadge.tsx
platform/frontend/src/components/ConfidenceBadge.tsx
platform/frontend/src/api/client.ts
platform/frontend/src/api/types.ts
```

Backend changes allowed only if necessary:

```text
platform/backend/src/pharabius_platform/api/findings.py
```

## UI Requirements

Finding table columns:

```text
Finding ID
Priority
Severity
Category
Title
Risk Score
Confidence
```

Filters:

```text
Severity
Category
Clear filters
```

## Tests

Add tests/static checks for:

- Findings page calls `GET /api/v1/repositories/{id}/findings`.
- Findings table renders rows.
- Severity filter changes query params or client-side filtered rows.
- Category filter changes query params or client-side filtered rows.
- Empty findings state renders.
- API error state renders.
- Back-to-repository link exists.

## Expected Behavior

Users can inspect repository findings in the browser without reading raw JSON or Markdown.

## Acceptance Criteria

- Findings table is usable.
- Basic filters exist.
- Empty/loading/error states exist.
- No pagination is required.
- No source-code display is introduced.

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
