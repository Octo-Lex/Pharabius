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


# S02 — Real PostgreSQL Integration Test Path

Risk: High  
Slice type: database integration / persistence validation  
Artifact impact: platform backend tests and fixtures

## Scope

Add a real PostgreSQL integration test path for platform persistence. v2.2.1 used mock-based tests; v2.2.2 must prove that ORM models, migrations/bootstrap, upload parser, and query APIs work against an actual PostgreSQL database.

## Goals

- Add optional PostgreSQL-backed integration tests.
- Support environment-gated execution, e.g. `PHARABIUS_RUN_PG_TESTS=1`.
- Run migrations or `init_dev_db.py` before tests.
- Upload sample `.ai-debt` bundle through API.
- Assert persisted rows exist.
- Assert repository, findings, and portfolio APIs query real rows.
- Keep tests skippable when PostgreSQL is unavailable.

## Patch Set

Expected files:

```text
platform/backend/tests/integration/test_postgres_upload_pipeline.py
platform/backend/tests/conftest.py
platform/backend/tests/fixtures/sample_ai_debt_bundle.tar.gz
platform/backend/src/pharabius_platform/db.py
platform/backend/scripts/init_dev_db.py
platform/backend/alembic/versions/*.py
platform/docs/postgres-testing.md
```

## Tests

Add integration tests for:

- Database schema initializes.
- Upload creates persisted rows.
- Duplicate upload reuses storage path but creates expected DB record behavior.
- Repository API returns uploaded repository.
- Findings API returns persisted findings.
- Portfolio API aggregates persisted records.
- API key auth works against DB-backed keys.

## Expected Behavior

When PostgreSQL is available:

```bash
PHARABIUS_RUN_PG_TESTS=1 pytest platform/backend/tests/integration
```

proves persistence and API queries against a real database.

When PostgreSQL is unavailable, tests skip with a clear reason.

## Acceptance Criteria

- Real PostgreSQL integration path exists.
- Tests are environment-gated.
- Tests do not falsely pass against mocks.
- Upload → persist → query is verified.
- Docs explain how to run integration tests locally and in CI.

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
