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


# S03 — Review Audit Timeline Readability

Risk: Medium

## Scope

Improve audit-history readability so reviewers and managers can understand who changed what, when, and why.

## Goals

- Add readable audit event labels.
- Show old status → new status.
- Show actor/reviewer.
- Show timestamp in readable format.
- Show comment/rationale association where available.
- Distinguish create/update/delete/restore/status-change events.
- Preserve soft-delete audit visibility.
- Keep audit trail immutable.

## Patch Set

Expected files:

```text
platform/frontend/src/components/ReviewAuditTimeline.tsx
platform/frontend/src/components/AuditEventItem.tsx
platform/frontend/src/api/reviews.ts
platform/frontend/src/api/types.ts
platform/backend/src/pharabius_platform/api/reviews.py
platform/backend/src/pharabius_platform/services/reviews.py
platform/backend/tests/test_review_audit_readability.py
```

Recommended event labels:

```text
Decision created
Status changed
Rationale updated
Decision soft-deleted
Decision restored
Comment added
```

## Tests

- Audit timeline renders empty state.
- Audit event shows old/new status.
- Audit event shows actor.
- Audit event shows timestamp.
- Soft-delete event appears in audit.
- Comment event appears in audit.
- Audit events sorted consistently.
- Backend response includes fields for readable UI.

## Expected Behavior

Audit history is understandable without inspecting raw JSON.

## Acceptance Criteria

- Audit timeline is readable.
- Soft-delete history remains visible.
- Status changes show previous and new status.
- Comments/rationale are connected to events where available.
- Audit history remains immutable.

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
