# v2.3.0 — Human Validation Workflow

Goal: Turn findings, claims, gaps, readiness, and work packages into a hosted human-review workflow with review states, comments, audit history, and sign-off, without external writes or remediation.

Release posture: major hosted-platform workflow release. This release adds human review state and auditability inside the Pharabius platform, but must not create external issues, post PR comments, modify repositories, or perform remediation.

Core boundaries:
- No OAuth / RBAC
- No policy engine
- No tracker writes
- No PR comments
- No GitHub Checks API
- No external integrations
- No autonomous remediation
- No source-code modification
- No approval automation
- No replacement for Product Engineering Team responsibility


# S01 — Review Data Model and State Machine

Risk: High  
Slice type: hosted platform backend model / migration  
Artifact impact: database tables, schemas, state rules

## Scope

Add a hosted review data model that records human validation state for findings, claims, gaps, readiness, and work packages.

Review state must be separate from canonical uploaded artifact data. A review can reference a finding or claim but must not overwrite the finding, evidence, risk score, or claim content parsed from uploaded `.ai-debt` bundles.

## Goals

- Add review target model.
- Add review status enum.
- Add review comment model.
- Add audit event model.
- Add state transition rules.
- Add initial Alembic migration.
- Add database indexes for repository/run/target lookup.
- Preserve immutable canonical artifact records.

## Patch Set

Expected files:

```text
platform/backend/src/pharabius_platform/models/reviews.py
platform/backend/src/pharabius_platform/schemas/reviews.py
platform/backend/src/pharabius_platform/services/review_state.py
platform/backend/alembic/versions/*_add_review_tables.py
platform/backend/tests/test_review_models.py
platform/backend/tests/test_review_state_machine.py
```

Recommended tables:

```text
ReviewItem
ReviewComment
ReviewAuditEvent
ReviewSummarySnapshot
```

Recommended `ReviewItem` fields:

```text
id
repository_id
run_id nullable
target_type
target_id
target_display_id
status
reviewer
last_comment
created_at
updated_at
```

Recommended `ReviewComment` fields:

```text
id
review_item_id
author
body
created_at
```

Recommended `ReviewAuditEvent` fields:

```text
id
review_item_id
event_type
old_status
new_status
actor
comment_id nullable
metadata json
created_at
```

## State machine

Allowed transitions:

| From | To |
|---|---|
| unreviewed | accepted |
| unreviewed | needs_clarification |
| unreviewed | rejected |
| unreviewed | blocked |
| accepted | validated |
| accepted | needs_clarification |
| needs_clarification | accepted |
| needs_clarification | rejected |
| needs_clarification | blocked |
| blocked | needs_clarification |
| blocked | rejected |
| rejected | needs_clarification |
| validated | needs_clarification |

Forbidden transitions should return a clear validation error.

## Tests

Add tests for:

- Tables/models instantiate correctly.
- Review status enum validates allowed values.
- Review target type enum validates allowed values.
- Allowed transitions pass.
- Forbidden transitions fail.
- Creating a comment does not change status unless explicit.
- Creating a status transition creates audit event.
- ReviewItem references canonical target without mutating it.
- Migration includes required tables and indexes.

## Expected Behavior

The platform can store human review state independently from uploaded Pharabius artifact data.

## Acceptance Criteria

- Review tables exist.
- State machine exists and is tested.
- Audit events are required for status transitions.
- Review decisions do not mutate findings/claims/gaps/readiness canonical projections.
- No external writes are added.


## Guardrails

- Review state is hosted platform state, not canonical analyzer truth.
- Do not mutate uploaded `.ai-debt` bundles.
- Do not mutate local Pharabius artifacts.
- Do not change scoring semantics.
- Do not let review decisions change canonical finding severity, risk score, evidence, or claim content.
- Do not create tickets, issues, PR comments, or tracker items.
- Do not add OAuth/RBAC in this release.
- Use admin token / existing platform auth model only.
- Preserve audit history for review changes.
- Keep all sign-off language human-owned, not automated approval.


## Verification Commands

Run the standard gates plus platform/frontend checks:

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
