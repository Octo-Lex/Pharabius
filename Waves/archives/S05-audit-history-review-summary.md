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


# S05 — Audit History and Review Summary

Risk: High  
Slice type: auditability / review reporting  
Artifact impact: backend APIs, frontend summary page, docs

## Scope

Add audit-history views and review summary reporting across repositories. This slice makes the human validation workflow auditable and manager-readable.

## Goals

- Add audit history API.
- Add review summary API.
- Add review dashboard page.
- Add repository-level review summary.
- Add platform-level review summary.
- Add exportable Markdown review summary if simple.
- Ensure every status transition has an audit event.
- Ensure comments are included in audit history.

## Patch Set

Expected files:

```text
platform/backend/src/pharabius_platform/api/reviews.py
platform/backend/src/pharabius_platform/services/review_summary.py
platform/frontend/src/pages/ReviewDashboardPage.tsx
platform/frontend/src/components/ReviewSummaryCards.tsx
platform/frontend/src/components/ReviewAuditTimeline.tsx
platform/frontend/src/components/ReviewSummaryTable.tsx
platform/backend/tests/test_review_summary.py
platform/backend/tests/test_review_audit_history.py
```

Recommended endpoints:

```text
GET /api/v1/review-summary
GET /api/v1/repositories/{id}/review-summary
GET /api/v1/reviews/{review_id}/audit
GET /api/v1/review-audit?repository_id=&target_type=&status=
```

Review summary metrics:

```text
total_review_items
unreviewed
accepted
needs_clarification
rejected
blocked
validated
comments_count
last_reviewed_at
```

Optional Markdown report:

```text
platform/reports/review-summary.md
```

Only add this if it fits naturally. The hosted API/UI summary is the priority.

## Tests

Add tests for:

- Summary counts by status.
- Summary counts by repository.
- Summary counts by target type.
- Audit history sorted by created_at.
- Audit history includes status transitions.
- Audit history includes comments.
- Review dashboard renders empty state.
- Review dashboard renders summary cards.
- No audit event can be missing for a status transition.

## Expected Behavior

Users can see what has been reviewed, what remains unreviewed, and who changed review state.

## Acceptance Criteria

- Review summary API exists.
- Audit history API exists.
- Review dashboard exists.
- Status transitions create audit events.
- Comments appear in audit history.
- Review state remains separate from canonical artifact data.
- No external write actions are added.


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
