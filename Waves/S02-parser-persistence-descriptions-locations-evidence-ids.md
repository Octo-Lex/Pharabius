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


# S02 — Parser Persistence for Descriptions, Locations, and Evidence IDs

Risk: High

## Scope

Update the artifact upload parser so it persists richer finding details already present in uploaded Pharabius artifacts.

The parser must not invent evidence. It should persist only what is present in uploaded artifacts and clearly handle missing data.

## Goals

- Persist finding descriptions where available.
- Persist locations where available.
- Persist evidence IDs where available.
- Persist evidence references where available.
- Preserve empty/missing states when details are absent.
- Avoid storing full source files.
- Avoid source repository access.
- Keep parser tolerant of older artifact shapes.

## Patch Set

Expected files:

```text
platform/backend/src/pharabius_platform/services/parser.py
platform/backend/src/pharabius_platform/services/upload.py
platform/backend/src/pharabius_platform/schemas/findings.py
platform/backend/tests/test_parser_finding_details.py
platform/backend/tests/fixtures/finding-detail-bundle/
```

Recommended extraction priority:

```text
Finding.description
Finding.locations
Finding.evidence_ids
Evidence register entries matching evidence_ids
Finding.evidence / supporting_evidence if schema uses alternate names
```

## Parser behavior

| Scenario | Behavior |
|---|---|
| Description present | Persist as text |
| Locations present | Persist normalized JSON |
| Evidence IDs present | Persist list |
| Evidence register present | Persist matching references |
| Evidence missing | Persist empty list/null and warning if useful |
| Older artifact format | Parse core finding fields and leave details empty |
| Malformed location | Skip item with warning, do not fail upload unless severe |

## Tests

Add tests for:

- Parser persists description.
- Parser persists locations.
- Parser persists evidence IDs.
- Parser joins evidence references from evidence register.
- Parser handles no evidence register.
- Parser handles old artifacts without details.
- Parser does not fail on one malformed location.
- Parser does not store source files.
- Upload response reports detail counts where useful.

## Expected Behavior

After upload, finding records include enough context to support evidence-aware review.

## Acceptance Criteria

- Parser persists detail fields from uploaded artifacts.
- Missing details are handled honestly.
- Parser remains backward-compatible.
- Existing upload tests continue passing.
- No source repository access occurs.

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
