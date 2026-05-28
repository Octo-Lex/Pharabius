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


# S01 — Docker Compose Runtime Smoke Test

Risk: High  
Slice type: runtime validation / infrastructure hardening  
Artifact impact: Docker Compose, scripts, platform test harness

## Scope

Add a repeatable Docker Compose runtime smoke test for the hosted platform. The goal is to verify that PostgreSQL, backend, and frontend can start together and that the backend health endpoint works against a real containerized runtime.

This slice does not need to run Docker in every CI environment if unavailable, but it must provide an explicit script and a CI-safe fallback.

## Goals

- Validate `platform/docker-compose.yml` syntax.
- Build backend and frontend containers.
- Start PostgreSQL, backend, and frontend services.
- Verify backend health endpoint.
- Verify frontend root responds.
- Capture useful logs on failure.
- Document disk-space cleanup commands.
- Keep runtime smoke test isolated from unit tests.

## Patch Set

Expected files:

```text
platform/docker-compose.yml
platform/backend/Dockerfile
platform/frontend/Dockerfile
platform/scripts/smoke_docker_compose.sh
platform/scripts/check_docker_available.py
platform/docs/runtime-validation.md
tests/test_platform_docker_config.py
```

## Tests

Add tests for:

- Docker Compose file exists.
- `docker compose config` can be run when Docker is available.
- Service names include `db`, `backend`, `frontend`.
- Backend and frontend Dockerfiles exist.
- `.dockerignore` exists for backend and frontend.
- Runtime script exists and is executable.
- Runtime script includes cleanup.

## Expected Behavior

A developer can run:

```bash
platform/scripts/smoke_docker_compose.sh
```

and verify the platform starts locally.

## Acceptance Criteria

- Docker Compose config validation exists.
- Runtime smoke script exists.
- Script verifies backend health and frontend root.
- Script cleans up containers and volumes.
- Docs include disk-space and `docker system prune` guidance.
- If CI cannot run Docker, CI still validates compose syntax/static structure.

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
