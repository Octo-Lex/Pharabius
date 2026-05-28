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


# S01 — Review Filters and Undecided/Decided Views

Risk: Medium

## Scope

Improve the hosted findings review experience by adding review-specific filters and views. Users should be able to quickly distinguish undecided findings from findings that already have review decisions.

## Goals

- Add review status filters to the findings table.
- Add decided vs. undecided view toggles.
- Add review status counts to the findings page.
- Preserve existing severity/category filters.
- Allow combined filters: severity + category + review status.
- Keep API changes backward-compatible.
- Avoid adding new review domains beyond findings.

## Patch Set

Expected files:

```text
platform/frontend/src/pages/FindingsPage.tsx
platform/frontend/src/components/FindingsTable.tsx
platform/frontend/src/components/FilterBar.tsx
platform/frontend/src/components/ReviewStatusBadge.tsx
platform/frontend/src/components/ReviewProgressSummary.tsx
platform/frontend/src/api/reviews.ts
platform/frontend/src/api/types.ts
platform/backend/src/pharabius_platform/api/reviews.py
platform/backend/tests/test_review_filters.py
```

Recommended filter values:

```text
all
undecided
decided
accepted
rejected
deferred
needs-investigation
duplicate
already-fixed
risk-accepted
```

## Tests

- Findings page renders review status filter.
- Undecided filter shows findings without decisions.
- Decided filter shows findings with decisions.
- Specific status filter shows matching decisions.
- Severity/category filters still work.
- Combined filters behave deterministically.
- Empty filter result renders useful empty state.

## Expected Behavior

Reviewers can prioritize work by viewing only undecided findings or specific review statuses.

## Acceptance Criteria

- Review filter UI exists.
- Undecided and decided views exist.
- Counts are visible.
- Existing severity/category filters continue working.
- No claim/gap/readiness review is added.

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
