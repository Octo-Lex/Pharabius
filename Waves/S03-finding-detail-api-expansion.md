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


# S03 — Finding Detail API Expansion

Risk: Medium-high

## Scope

Expand hosted API responses so frontend review workflows can fetch richer finding context.

This may be done by expanding existing finding endpoints or adding a dedicated finding detail endpoint.

## Goals

- Return description, locations, evidence IDs, and evidence references.
- Preserve existing list response compatibility where possible.
- Avoid overly large list responses if evidence snippets are large.
- Add a dedicated detail endpoint if needed.
- Return clear empty states for missing details.
- Ensure review APIs can fetch associated finding context without mutating reviews.

## Patch Set

Expected files:

```text
platform/backend/src/pharabius_platform/api/findings.py
platform/backend/src/pharabius_platform/schemas/findings.py
platform/backend/tests/test_finding_detail_api.py
platform/backend/tests/test_finding_detail_api_backwards_compat.py
platform/frontend/src/api/types.ts
```

Recommended endpoints:

```text
GET /api/v1/repositories/{repo_id}/findings
GET /api/v1/repositories/{repo_id}/findings/{finding_id}
```

Recommended approach:

| Endpoint | Detail level |
|---|---|
| list findings | summary fields + maybe evidence count |
| finding detail | full description, locations, evidence references |

## Response shape

Recommended detail response:

```json
{
  "finding_id": "TD-DEP-001",
  "title": "...",
  "category": "TD-DEP",
  "severity": "high",
  "risk_score": 24,
  "description": "...",
  "locations": [],
  "evidence_ids": [],
  "evidence_references": [],
  "artifact_context": {}
}
```

## Tests

Add tests for:

- Detail endpoint returns description.
- Detail endpoint returns locations.
- Detail endpoint returns evidence IDs.
- Detail endpoint returns evidence references.
- Missing detail fields return empty/null safely.
- Unknown finding returns 404.
- List endpoint remains compatible with existing frontend.
- Detail endpoint does not require source repository access.

## Expected Behavior

Frontend can request detailed finding context for review without loading raw artifact bundles.

## Acceptance Criteria

- Finding detail API exists or list API is safely expanded.
- Missing details are represented safely.
- Backward compatibility is preserved.
- Tests cover populated and missing detail cases.
- No external source browsing is added.

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
