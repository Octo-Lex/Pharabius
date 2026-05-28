# v2.2 — Hosted Platform Foundation + CI Ingestion

Goal: Build the first hosted Pharabius platform for artifact ingestion, repository/portfolio visibility, trend review, claims/gaps inspection, and CI upload — without source-code storage, repository cloning, tracker writes, PR comments, issue creation, or remediation.

Release target: `v2.2.0`  
Branch target: `roadmap/v2.2.0-hosted-platform-foundation`  
Posture: Large release, category change, strict MVP boundary.

Primary product loop:

```text
Run Pharabius locally or in CI
→ generate .ai-debt artifacts
→ upload artifact bundle
→ validate artifact contract
→ parse normalized records
→ view repository dashboard
→ view portfolio dashboard
→ inspect findings, trends, claims, gaps, gates, and readiness
```


# S01 — Platform Scaffold: FastAPI, Database, Docker Compose, Base Data Model

Risk: High  
Slice type: Platform foundation / architecture  
Artifact impact: New hosted platform package, database model, deployment scaffold

## Scope

Create the minimal hosted-platform scaffold needed to support artifact ingestion and read-only dashboards.

This slice establishes the web application structure, database connection, Docker Compose development environment, and normalized base data model. It should not implement full upload parsing or dashboard UI yet.

## Goals

- Add hosted platform package/module without destabilizing the existing CLI.
- Add FastAPI application entrypoint.
- Add database configuration.
- Add SQLAlchemy or SQLModel models for core hosted entities.
- Add Alembic or migration path if selected.
- Add Docker Compose for local development.
- Add health endpoint.
- Add basic platform test harness.
- Preserve existing CLI package behavior.

## Patch Set

Expected files/directories:

```text
src/pharabius_platform/
  __init__.py
  app.py
  config.py
  database.py
  models.py
  schemas.py
  health.py

platform/
  Dockerfile
  docker-compose.yml
  README.md
  .env.example

tests/platform/
  test_platform_health.py
  test_platform_database.py
  test_platform_models.py
```

Recommended architecture:

```text
Backend: FastAPI
Database: PostgreSQL for platform/dev, SQLite allowed for tests
Migrations: Alembic or equivalent
Frontend: defer full UI until S03/S04; placeholder route acceptable
Storage: local filesystem for uploaded bundle files in v2.2
```

Recommended base entities:

```text
Organization
Project
Repository
ArtifactBundle
Run
Finding
QualityGateResult
TrendPoint
OperationalClaim
Gap
Question
ReadinessSnapshot
UploadToken
```

Minimum fields:

```python
Organization:
  id
  name
  created_at

Repository:
  id
  organization_id
  name
  external_key | slug
  latest_run_id
  created_at
  updated_at

ArtifactBundle:
  id
  repository_id
  upload_source: manual | ci
  uploaded_at
  artifact_contract_status
  storage_path
  source_commit
  source_branch
  tool_version

Run:
  id
  repository_id
  run_id
  timestamp
  commit
  branch
  total_findings
  critical
  high
  medium
  low
```

## Tests

Add tests for:

- FastAPI app imports successfully.
- Health endpoint returns 200.
- Database session can initialize.
- Core models can be created in test DB.
- Required relationships work.
- Docker Compose file exists and references app + database.
- Existing CLI imports still work.
- Platform package does not require database on normal CLI import.

## Targeted Verification

```bash
pytest tests/platform/test_platform_health.py
pytest tests/platform/test_platform_database.py
pytest tests/platform/test_platform_models.py
python -c "import pharabius; import pharabius_platform"
docker compose -f platform/docker-compose.yml config
```

## Expected Behavior

After this slice:

- Existing `ai-debt` CLI still works.
- `pharabius_platform` app can start locally.
- `/health` responds.
- Database models exist and can be tested.
- No artifact upload or real dashboard is required yet.

## Acceptance Criteria

- Platform scaffold exists.
- FastAPI app starts in test mode.
- Database models are test-covered.
- Docker Compose validates.
- Existing CLI behavior is unaffected.
- No external integrations are added.
- No source code is uploaded or stored.
- All local gates pass.
## Guardrails

- Do not require source-code upload.
- Do not clone repositories.
- Do not store full source files by default.
- Do not create issues, PR comments, tracker items, or external writes.
- Do not call Jira, Linear, GitHub Issues, Azure DevOps, GitHub, GitLab, or other external write APIs.
- Do not upload SARIF to code scanning by default.
- Do not perform autonomous remediation.
- Do not generate patches.
- Do not modify production code.
- Treat uploaded `.ai-debt` bundles as analysis artifacts, not as implementation authority.
- Keep v2.2 hosted behavior read-only with respect to source systems.


## Verification Commands

Minimum local verification:

```bash
ruff format --check .
ruff check .
mypy src
lint-imports
pytest
python -m build
python scripts/validate_repo.py .
```

Hosted-platform verification should additionally include the new platform checks introduced in this release, such as API tests, database migration checks, frontend checks, and Docker Compose smoke tests.
