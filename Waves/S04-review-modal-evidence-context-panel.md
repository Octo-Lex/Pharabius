# v2.4.0 — Finding Detail & Evidence Linking

Goal: Persist and display richer finding detail from uploaded Pharabius artifacts, including descriptions, locations, and evidence references, so reviewers can make decisions with more context.

Release posture: feature release. This release expands the hosted platform’s persisted finding detail contract and review context surface. It is not a patch release.

Core boundaries:
- No claim review
- No gap closure tracking
- No readiness sign-off
- No policy engine
- No tracker writes
- No PR comments
- No repository source browsing or cloning
- No autonomous remediation
- No source-code modification
- No external integration writes

Trust boundary:
- The platform ingests uploaded Pharabius `.ai-debt` artifacts.
- Uploaded artifacts may contain source-derived file paths, line references, hashes, summaries, and evidence snippets.
- Evidence linking must display artifact-derived evidence context, not fetch or browse source repositories.


# S04 — Review Modal Evidence / Context Panel

Risk: Medium-high

## Scope

Update the hosted review modal to display richer finding context from the new detail API. Reviewers should see the relevant description, location, and evidence references before choosing a review decision.

## Goals

- Add finding context panel to review modal.
- Show description.
- Show locations.
- Show evidence IDs and references.
- Show evidence hash/content hash where available.
- Show source-derived evidence warning.
- Handle missing detail gracefully.
- Keep review decision update flow unchanged.

## Patch Set

Expected files:

```text
platform/frontend/src/components/FindingReviewModal.tsx
platform/frontend/src/components/FindingContextPanel.tsx
platform/frontend/src/components/EvidenceReferenceList.tsx
platform/frontend/src/components/LocationList.tsx
platform/frontend/src/api/findings.ts
platform/frontend/src/api/reviews.ts
platform/frontend/src/api/types.ts
platform/frontend/src/pages/FindingsPage.tsx
```

Required warning:

```text
This context comes from uploaded Pharabius artifacts and may include source-derived file paths, line references, hashes, or evidence snippets.
```

Recommended UI sections:

```text
Finding summary
Description
Locations
Evidence references
Review decision
Audit history
```

## Tests

Add frontend/build/static tests for:

- Review modal fetches finding detail.
- Description renders.
- Locations render.
- Evidence references render.
- Missing evidence renders empty state.
- Warning is visible when context panel is shown.
- Review status submission still works.
- Existing review badges still work.

## Expected Behavior

Reviewers can make evidence-informed finding decisions from the modal.

## Acceptance Criteria

- Review modal shows richer finding context.
- Evidence references are visible where available.
- Missing evidence is not treated as an error.
- Source-derived context warning is visible.
- Review decision workflow remains unchanged.
- No repository source browser is introduced.

## Guardrails

- Do not mutate uploaded `.ai-debt` bundles.
- Do not mutate canonical finding semantics: finding ID, severity, risk score, category, and evidence provenance remain analyzer-derived.
- Do not add repository cloning or source browsing.
- Do not add tracker writes, PR comments, webhooks, policy enforcement, or remediation.
- Keep evidence context clearly labeled as artifact-derived.
- Treat missing evidence as normal and show honest empty states.
- Preserve v2.3 review decision behavior and audit history.
- Ensure schema migration is backward-compatible for existing finding rows.


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

Recommended PostgreSQL validation:

```bash
PHARABIUS_RUN_PG_TESTS=1 pytest platform/backend/tests/integration
```
