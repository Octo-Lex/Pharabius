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


# S03 — Frontend MVP Routes and API Client

Risk: Medium-high  
Slice type: frontend foundation  
Artifact impact: React/Vite frontend

## Scope

Replace the static JSX scaffold with a minimal routed React frontend and typed API client. This slice creates the frontend structure for upload, repository, findings, and portfolio screens, but does not need full UI polish.

## Goals

- Add route structure.
- Add API client wrapper.
- Add shared layout.
- Add navigation.
- Add loading and error primitives.
- Add typed DTOs matching backend responses.
- Keep build simple and deterministic.

## Patch Set

Expected files:

```text
platform/frontend/src/main.tsx
platform/frontend/src/App.tsx
platform/frontend/src/api/client.ts
platform/frontend/src/api/types.ts
platform/frontend/src/components/Layout.tsx
platform/frontend/src/components/LoadingState.tsx
platform/frontend/src/components/ErrorState.tsx
platform/frontend/src/pages/HomePage.tsx
platform/frontend/src/pages/UploadPage.tsx
platform/frontend/src/pages/RepositoryPage.tsx
platform/frontend/src/pages/FindingsPage.tsx
platform/frontend/src/pages/PortfolioPage.tsx
platform/frontend/package.json
platform/frontend/vite.config.ts
platform/frontend/tsconfig.json
```

Recommended routes:

```text
/                          Repository list
/upload                    Upload page
/repositories/:id          Repository dashboard
/repositories/:id/findings Findings table
/portfolio                 Portfolio summary
```

## Tests

Add tests or build checks for:

- Frontend TypeScript compiles.
- Vite build succeeds.
- Routes are declared.
- API client uses configurable base URL.
- API client attaches admin token/upload token when configured.
- Shared error state renders useful message.
- No hardcoded production API URL.

## Expected Behavior

The frontend becomes a usable shell with real routes and an API client.

## Acceptance Criteria

- `npm run build` passes.
- Frontend has five MVP routes.
- API client calls backend endpoints.
- API base URL is configurable.
- Error/loading components exist.
- No OAuth/RBAC is added.

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
