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


# S02 — Review APIs for Findings, Claims, Gaps, and Readiness

Risk: High  
Slice type: backend API workflow  
Artifact impact: hosted API endpoints and service layer

## Scope

Add backend APIs that allow hosted users to create, read, and update review state for supported targets.

This slice should expose review operations over findings, claims, gaps, readiness, and work-package references where data exists. It must not write to external trackers or mutate canonical artifact records.

## Goals

- Add review item create/read/update endpoints.
- Add target-specific review listing endpoints.
- Add status transition endpoint.
- Add comment endpoint.
- Add review summary endpoint.
- Enforce state machine from S01.
- Include audit events for all mutations.
- Return request IDs through error envelope.

## Patch Set

Expected files:

```text
platform/backend/src/pharabius_platform/api/reviews.py
platform/backend/src/pharabius_platform/services/reviews.py
platform/backend/src/pharabius_platform/schemas/reviews.py
platform/backend/tests/test_review_api.py
platform/backend/tests/test_review_target_api.py
```

Recommended endpoints:

```text
GET    /api/v1/reviews
POST   /api/v1/reviews
GET    /api/v1/reviews/{review_id}
PATCH  /api/v1/reviews/{review_id}/status
POST   /api/v1/reviews/{review_id}/comments
GET    /api/v1/reviews/{review_id}/audit
GET    /api/v1/repositories/{id}/reviews
GET    /api/v1/repositories/{id}/review-summary
```

Target-specific query filters:

```text
target_type=finding|claim|gap|readiness|work_package
status=unreviewed|accepted|needs_clarification|rejected|blocked|validated
run_id=...
```

Recommended status update body:

```json
{
  "status": "accepted",
  "actor": "platform-admin",
  "comment": "Confirmed by PET review."
}
```

## Tests

Add tests for:

- Create review item for finding.
- Create review item for claim.
- Create review item for gap.
- Create readiness review item.
- Invalid target type fails.
- Invalid target ID returns 404 or validation error.
- Allowed status transition succeeds.
- Forbidden status transition fails.
- Status transition creates audit event.
- Comment creates comment record and audit event.
- Repository review summary counts statuses correctly.
- Review APIs require admin token under current auth model.
- Review APIs do not call external services.

## Expected Behavior

The backend exposes review workflow APIs that the frontend can use to review technical debt artifacts.

## Acceptance Criteria

- Review APIs exist and are tested.
- Review APIs enforce state machine.
- Review APIs create audit events.
- Review summary endpoint exists.
- No canonical finding/claim/gap mutation occurs.
- No external writes occur.


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
