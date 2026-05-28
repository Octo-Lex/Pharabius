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


# S03 — Claims and Gaps Review UI

Risk: Medium-high  
Slice type: frontend review workflow  
Artifact impact: hosted platform UI

## Scope

Add UI screens for reviewing operational claims and gaps. Users should be able to view claims/gaps, inspect status/confidence/severity, apply review states, add comments, and see basic audit history.

## Goals

- Add claims review page.
- Add gaps review page.
- Add review status controls.
- Add reviewer comment form.
- Add status badges.
- Add filtering by status and confidence/severity.
- Show audit history for selected item.
- Keep UI simple and desktop-oriented.

## Patch Set

Expected files:

```text
platform/frontend/src/pages/ClaimsReviewPage.tsx
platform/frontend/src/pages/GapsReviewPage.tsx
platform/frontend/src/components/ReviewStatusBadge.tsx
platform/frontend/src/components/ReviewStatusSelect.tsx
platform/frontend/src/components/ReviewCommentForm.tsx
platform/frontend/src/components/ReviewAuditTimeline.tsx
platform/frontend/src/components/ClaimsTable.tsx
platform/frontend/src/components/GapsTable.tsx
platform/frontend/src/api/reviews.ts
platform/frontend/src/api/types.ts
```

Routes:

```text
/review/claims
/review/gaps
```

## UI Requirements

Claims table columns:

```text
Claim ID
Type
Status
Confidence
Description
Review Status
Last Reviewed
```

Gaps table columns:

```text
Gap ID
Severity
Description
Review Status
Last Reviewed
```

Review actions:

```text
Accept
Needs clarification
Reject
Block
Validate
Add comment
```

## Tests

Add build/static checks for:

- Claims review route exists.
- Gaps review route exists.
- Review status controls render.
- Comment form exists.
- API client calls review endpoints.
- Audit timeline handles empty history.
- Empty states render when no claims/gaps exist.
- Errors surface request ID when provided.

## Expected Behavior

Users can review claims and gaps in the hosted UI without leaving the platform.

## Acceptance Criteria

- Claims and gaps review UI exists.
- Review state can be changed from UI.
- Comments can be submitted from UI.
- Audit history is visible.
- Empty/error states are present.
- No external integration is added.


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
