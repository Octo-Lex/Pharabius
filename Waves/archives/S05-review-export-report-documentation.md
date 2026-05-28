# v2.3.1 — Review Workflow Polish & Evidence Linking

Goal: Improve finding-review usability by surfacing review filters, audit details, evidence links, decision completeness, and review summary clarity without expanding into claims/gaps/readiness review.

Release posture: patch release for the hosted finding-review workflow.

Core boundaries:
- No claim review, gap closure tracking, readiness sign-off, or work-package review expansion
- No OAuth / RBAC
- No policy engine
- No tracker writes, PR comments, notifications, or webhooks
- No autonomous remediation or source-code modification
- Review decisions remain hosted workflow state, not canonical analyzer truth

Guardrails:
- Do not mutate uploaded `.ai-debt` bundles.
- Do not mutate canonical finding records.
- Do not change finding severity, risk score, evidence, category, or source content.
- Preserve soft-delete and audit history from v2.3.0.
- Keep the scope limited to finding-review usability.


# S05 — Review Export / Report Documentation

Risk: Low-medium

## Scope

Document how teams can use hosted review decisions and optionally add a simple read-only review summary export if it fits naturally.

This is not tracker integration. The export is local/platform-generated documentation only.

## Goals

- Document review workflow for PET teams.
- Document review statuses and when to use each.
- Document audit history semantics.
- Document review summary interpretation.
- Document how review state differs from canonical Pharabius artifacts.
- Optionally add Markdown/JSON review summary export from hosted platform.
- Do not add external writes or tracker export.

## Patch Set

Expected files:

```text
platform/docs/review-workflow.md
platform/docs/review-statuses.md
platform/docs/review-summary.md
platform/docs/audit-history.md
platform/backend/src/pharabius_platform/services/review_report.py
platform/backend/src/pharabius_platform/api/reviews.py
platform/backend/tests/test_review_report.py
```

Optional endpoints:

```text
GET /api/v1/repositories/{id}/reviews/report.md
GET /api/v1/repositories/{id}/reviews/report.json
```

Only add export endpoints if they are simple. Documentation is the primary deliverable.

## Required documentation statements

```text
Review decisions are hosted workflow state.
Review decisions do not alter canonical findings, risk scores, evidence, or claims.
Review reports are for human coordination and audit support.
Review reports do not create tickets or external tracker items.
Reviewer identity is free text unless/until auth/RBAC is added.
```

## Tests

If export endpoint is added:

- Markdown report renders.
- JSON report serializes.
- Report includes review status counts.
- Report includes undecided count.
- Report excludes external write instructions.
- Report does not mutate data.

## Acceptance Criteria

- Review workflow docs exist.
- Review status guidance exists.
- Audit semantics are documented.
- No tracker write/export integration is added.
- Optional report, if added, is read-only.

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
