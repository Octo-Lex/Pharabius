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


# S04 — Frontend Empty, Loading, and Error States

Risk: Medium  
Slice type: Frontend UX hardening  
Artifact impact: React components, frontend tests if available

## Scope

Polish the v2.2.0 frontend MVP so the hosted platform behaves professionally when there are no uploads, APIs are loading, errors occur, or data is partial.

## Goals

- Add reusable loading state component.
- Add reusable empty state component.
- Add reusable error state component with request ID display.
- Improve first-run state when no repositories exist.
- Improve repository dashboard when latest run is missing.
- Improve findings table when no findings match filters.
- Improve portfolio dashboard when there are no repositories.
- Improve upload page success/error presentation.
- Ensure sensitive upload details are not displayed.

## Patch Set

Expected files/modules:

```text
platform/frontend/src/components/LoadingState.tsx
platform/frontend/src/components/EmptyState.tsx
platform/frontend/src/components/ErrorState.tsx
platform/frontend/src/components/StatusBadge.tsx
platform/frontend/src/pages/RepositoryList.tsx
platform/frontend/src/pages/RepositoryDashboard.tsx
platform/frontend/src/pages/FindingsTable.tsx
platform/frontend/src/pages/PortfolioSummary.tsx
platform/frontend/src/pages/UploadPage.tsx
platform/frontend/src/api/client.ts
platform/frontend/tests/                        # if existing frontend test setup is available
```

Recommended UX states:

| Screen | Empty state |
|---|---|
| Repository list | “No repositories uploaded yet. Upload a `.ai-debt` bundle to begin.” |
| Portfolio | “No portfolio data yet.” |
| Findings | “No findings match these filters.” |
| Repository dashboard | “No run data available for this repository.” |
| Upload page | Shows validation status, warnings, and bundle ID |

## Tests

Add frontend tests if the test setup exists. If not, add static/component-level validation where feasible:

- Components render without crashing.
- Empty state copy appears for no repositories.
- Error state displays request ID.
- Upload success displays validation status.
- Upload error does not display token.
- API client extracts error envelope message.

## Targeted Verification

```bash
cd platform/frontend
npm run build
npm test -- --run || true
```

## Expected Behavior

The hosted UI is usable on a fresh installation and debuggable when API calls fail.

## Acceptance Criteria

- Frontend has visible empty/loading/error states.
- Error states display request IDs where available.
- Upload UX shows validation summary.
- No secrets are rendered in UI.
- Frontend build passes.
- All gates pass.

## Guardrails

- Preserve v2.2.0 architecture and product boundaries.
- Do not add external writes.
- Do not add repository cloning.
- Do not add OAuth or full user management.
- Do not add policy engine behavior.
- Do not add tracker integrations.
- Do not add background workers unless explicitly required for reliability; default is synchronous parsing.
- Do not mutate uploaded bundles after storage.
- Do not store raw API keys.
- Treat uploaded `.ai-debt` bundles as potentially sensitive source-derived artifacts.
- Keep all changes focused on diagnostics, safety, deployment readiness, and UX polish.


## Verification Commands

Run the full local gate suite for the CLI and platform:

```bash
ruff format --check .
ruff check .
mypy src
lint-imports
pytest
python -m build
python scripts/validate_repo.py .
```

Platform-specific verification should also run where available:

```bash
cd platform
# backend tests
cd backend && pytest
# frontend checks
cd ../frontend && npm test -- --run || true
cd ../frontend && npm run build
# docker smoke
cd .. && docker compose config
```
