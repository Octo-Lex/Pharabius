# v2.4.0 — Finding Detail & Evidence Linking

Goal: Persist and display richer finding detail from uploaded Pharabius artifacts, including descriptions, locations, and evidence references, so reviewers can make decisions with more context.

Release posture: feature release. This release expands the hosted platform’s persisted finding detail contract and review context surface. It is not a patch release.

Core boundaries:
- No claim review
- No gap closure tracking
- No readiness sign-off
- No policy engine
- No tracker writes
- No PR comments
- No repository source browsing or cloning
- No autonomous remediation
- No source-code modification
- No external integration writes

Trust boundary:
- The platform ingests uploaded Pharabius `.ai-debt` artifacts.
- Uploaded artifacts may contain source-derived file paths, line references, hashes, summaries, and evidence snippets.
- Evidence linking must display artifact-derived evidence context, not fetch or browse source repositories.


# S01 — Finding Detail Schema Migration

Risk: High

## Scope

Extend the hosted platform `Finding` persistence model to store richer artifact-derived finding detail required for review context.

This is a feature release because it changes the hosted platform’s stored data contract.

## Goals

- Add backward-compatible nullable columns to `Finding`.
- Add JSON columns for variable artifact-derived structures.
- Add Alembic migration.
- Ensure existing rows remain valid.
- Ensure migration works against PostgreSQL.
- Avoid changing canonical semantics such as severity/risk/category.

## Patch Set

Expected files:

```text
platform/backend/src/pharabius_platform/models/findings.py
platform/backend/src/pharabius_platform/schemas/findings.py
platform/backend/alembic/versions/*_finding_detail_evidence.py
platform/backend/tests/test_finding_detail_model.py
platform/backend/tests/test_finding_detail_migration.py
```

Recommended fields:

```text
description TEXT nullable
locations JSONB nullable
evidence_ids JSONB nullable
evidence_references JSONB nullable
artifact_context JSONB nullable
```

If JSONB is not abstracted cleanly across SQLite and PostgreSQL, use SQLAlchemy JSON with PostgreSQL-compatible migration.

Recommended `locations` shape:

```json
[
  {
    "path": "src/example.py",
    "start_line": 10,
    "end_line": 20,
    "symbol": "optional"
  }
]
```

Recommended `evidence_references` shape:

```json
[
  {
    "evidence_id": "EV-001",
    "source": "scanner",
    "path": "src/example.py",
    "line": 10,
    "content_hash": "sha256:...",
    "snippet": "optional, source-derived"
  }
]
```

## Tests

Add tests for:

- New fields are nullable.
- Existing finding rows without details remain valid.
- Finding detail values serialize/deserialize.
- Migration contains expected columns.
- PostgreSQL migration path succeeds when integration tests are enabled.
- New fields do not alter severity, risk score, priority, category, or finding ID.

## Expected Behavior

Existing platform data remains compatible, while new uploads can persist richer finding context.

## Acceptance Criteria

- Migration exists.
- New fields are nullable/backward-compatible.
- Tests cover serialization.
- Existing tests continue passing.
- No source browsing/cloning is added.

## Guardrails

- Do not mutate uploaded `.ai-debt` bundles.
- Do not mutate canonical finding semantics: finding ID, severity, risk score, category, and evidence provenance remain analyzer-derived.
- Do not add repository cloning or source browsing.
- Do not add tracker writes, PR comments, webhooks, policy enforcement, or remediation.
- Keep evidence context clearly labeled as artifact-derived.
- Treat missing evidence as normal and show honest empty states.
- Preserve v2.3 review decision behavior and audit history.
- Ensure schema migration is backward-compatible for existing finding rows.


## Verification Commands

```bash
ruff format --check .
ruff check .
mypy src
lint-imports
pytest
pytest platform/backend/tests
npm --prefix platform/frontend run build
python -m build
python scripts/validate_repo.py .
```

Optional runtime validation:

```bash
platform/scripts/smoke_docker_compose.sh
```

Recommended PostgreSQL validation:

```bash
PHARABIUS_RUN_PG_TESTS=1 pytest platform/backend/tests/integration
```
