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


# S04 — Review Completeness and Summary Metrics

Risk: Medium

## Scope

Improve review summary clarity by adding completeness metrics and clearer progress calculations for repository finding review.

Completeness describes review coverage, not correctness.

## Goals

- Add decided vs. undecided count.
- Add review completion percentage.
- Add counts by CLI `DecisionStatus`.
- Add high/critical undecided count.
- Add stale review indicator if feasible.
- Add review summary cards to repository dashboard or review page.
- Keep metrics scoped to finding review only.

## Patch Set

Expected files:

```text
platform/backend/src/pharabius_platform/services/review_summary.py
platform/backend/src/pharabius_platform/api/reviews.py
platform/backend/tests/test_review_completeness.py
platform/frontend/src/components/ReviewProgressSummary.tsx
platform/frontend/src/pages/RepositoryPage.tsx
platform/frontend/src/pages/FindingsPage.tsx
platform/frontend/src/pages/ReviewSummaryPage.tsx
platform/frontend/src/api/types.ts
```

Recommended metrics:

```text
total_findings
reviewed_findings
undecided_findings
review_completion_percent
accepted
rejected
deferred
needs_investigation
duplicate
already_fixed
risk_accepted
critical_unreviewed
high_unreviewed
stale_review_count
```

## Tests

- Completion percent is 0 when no decisions.
- Completion percent is 100 when all findings have decisions.
- Counts by status are correct.
- Undecided count is total findings minus reviewed findings.
- High/critical undecided count is correct.
- Empty repository summary is safe.
- Stale review count works or is explicitly deferred.

## Expected Behavior

Reviewers can understand review progress at a glance.

## Acceptance Criteria

- Review completeness summary exists.
- Counts are deterministic.
- Metrics are scoped to finding review.
- Metrics do not imply correctness of decisions.
- Summary UI is visible from findings or repository dashboard.

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
