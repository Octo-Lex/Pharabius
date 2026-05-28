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


# S04 — Finding and Work-Package Review UI

Risk: Medium-high  
Slice type: frontend review workflow  
Artifact impact: hosted platform UI and backend API use

## Scope

Add review controls to findings and work-package-related views. Users should be able to review high-priority findings and work packages, add comments, and sign off when validated.

Work packages may not yet be fully normalized in the hosted database. If work-package data is not available, this slice should support finding review fully and expose work-package review only when parsed data exists.

## Goals

- Add review controls to findings table/details.
- Add finding review drawer or panel.
- Add comment form.
- Add audit timeline.
- Add work-package review list if work-package projections exist.
- Add readiness sign-off affordance if readiness data exists.
- Keep canonical finding data immutable.

## Patch Set

Expected files:

```text
platform/frontend/src/pages/FindingsPage.tsx
platform/frontend/src/pages/WorkPackagesReviewPage.tsx
platform/frontend/src/components/FindingReviewPanel.tsx
platform/frontend/src/components/ReviewStatusBadge.tsx
platform/frontend/src/components/ReviewCommentForm.tsx
platform/frontend/src/components/ReviewAuditTimeline.tsx
platform/frontend/src/api/reviews.ts
platform/backend/src/pharabius_platform/api/reviews.py
platform/backend/src/pharabius_platform/services/reviews.py
```

Routes:

```text
/repositories/:id/findings
/review/work-packages
/review/readiness
```

If work packages are not normalized:

```text
/review/work-packages
→ show "Work-package review requires work-package artifacts to be uploaded and parsed."
```

## Tests

Add tests/static checks for:

- Findings page includes review action.
- Review panel renders selected finding.
- Status update calls review API.
- Comment submission calls review API.
- Audit timeline displays events.
- Work-package page handles unavailable data honestly.
- Readiness review handles unknown/unavailable state.
- Canonical finding fields are not changed by review updates.

## Expected Behavior

Users can review findings and, where available, work packages/readiness without changing canonical artifact facts.

## Acceptance Criteria

- Finding review is usable.
- Work-package review handles unavailable data honestly.
- Readiness review handles unknown/unavailable data honestly.
- Review comments and audit history work.
- No external tickets/issues are created.
- No remediation or source modification is introduced.


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
