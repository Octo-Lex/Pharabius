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


# S01 — Frontend Dependency Setup, Routing, and API Client

Risk: Medium-high  
Slice type: frontend foundation  
Artifact impact: React/Vite frontend

## Scope

Replace the static frontend scaffold with a proper React/Vite app shell, routing structure, shared layout, typed API client, and reusable loading/error/empty primitives.

This slice should make the frontend buildable and navigable, but pages may still show placeholders.

## Goals

- Install and lock frontend dependencies.
- Configure Vite + React + TypeScript.
- Configure Tailwind CSS v4.
- Add route structure.
- Add shared layout and navigation.
- Add typed API client.
- Add shared state components: loading, error, empty.
- Add environment-driven API base URL.
- Avoid hardcoded production URLs.

## Patch Set

Expected files:

```text
platform/frontend/package.json
platform/frontend/package-lock.json
platform/frontend/vite.config.ts
platform/frontend/tsconfig.json
platform/frontend/src/main.tsx
platform/frontend/src/App.tsx
platform/frontend/src/styles.css
platform/frontend/src/api/client.ts
platform/frontend/src/api/types.ts
platform/frontend/src/components/Layout.tsx
platform/frontend/src/components/LoadingState.tsx
platform/frontend/src/components/ErrorState.tsx
platform/frontend/src/components/EmptyState.tsx
platform/frontend/src/pages/HomePage.tsx
platform/frontend/src/pages/UploadPage.tsx
platform/frontend/src/pages/RepositoryPage.tsx
platform/frontend/src/pages/FindingsPage.tsx
platform/frontend/src/pages/PortfolioPage.tsx
```

Recommended routes:

```text
/                           Repository list
/upload                     Upload page
/repositories/:id           Repository dashboard
/repositories/:id/findings  Findings table
/portfolio                  Portfolio summary
```

## Tests

Add tests/static checks for:

- `npm run build` succeeds.
- Routes are declared.
- API client has configurable base URL.
- API client parses error envelope.
- No hardcoded production API URL.
- Tailwind CSS entry point exists.
- Layout renders navigation links.

## Expected Behavior

After S01, the frontend is no longer a static scaffold. It is a routed app shell with API utilities and shared UI primitives.

## Acceptance Criteria

- Frontend dependencies install.
- Frontend build passes.
- Five routes exist.
- API base URL is configurable.
- Loading/error/empty components exist.
- No OAuth/RBAC is introduced.

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
