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


# S02 — Evidence and Finding Context in Review Modal

Risk: Medium

## Scope

Improve the review modal so reviewers have enough context to make decisions without switching back to raw reports. The modal should show the finding title, category, severity, risk score, rationale fields, and evidence references where available.

## Goals

- Show finding title and stable finding ID.
- Show priority/severity/category/risk score.
- Show confidence if available.
- Show file path and line references if available.
- Show evidence IDs linked to evidence references if parsed.
- Show evidence hash/content hash when available.
- Keep source-derived content display limited and clearly labeled.

## Patch Set

Expected files:

```text
platform/frontend/src/components/FindingReviewModal.tsx
platform/frontend/src/components/FindingContextPanel.tsx
platform/frontend/src/components/EvidenceReferenceList.tsx
platform/frontend/src/components/ReviewCommentForm.tsx
platform/frontend/src/api/types.ts
platform/backend/src/pharabius_platform/api/findings.py
platform/backend/src/pharabius_platform/api/reviews.py
platform/backend/tests/test_finding_context_api.py
```

Required warning when source-derived evidence is displayed:

```text
This context comes from uploaded Pharabius artifacts and may include source-derived file paths, line references, hashes, or evidence snippets.
```

## Tests

- Review modal renders finding title and ID.
- Review modal renders category/severity/risk score.
- Evidence reference list handles missing evidence gracefully.
- Evidence reference list renders IDs when available.
- Source-derived context warning is visible.
- Review decision updates do not mutate finding/evidence records.

## Expected Behavior

Reviewers can make better decisions because the modal includes finding and evidence context.

## Acceptance Criteria

- Review modal includes finding context.
- Evidence references appear where available.
- Missing evidence shows a clear empty state.
- Source-derived evidence warning is visible.
- No source repository browsing or cloning is introduced.

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
