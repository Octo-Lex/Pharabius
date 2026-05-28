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


# S05 — Evidence Sensitivity and Limitations Documentation

Risk: Medium

## Scope

Document the sensitivity and limitations of persisted finding details and evidence references.

This is important because the platform now stores more source-derived context than before.

## Goals

- Document what finding detail fields may contain.
- Document that evidence context is artifact-derived.
- Document that the platform does not clone or browse repositories.
- Document that evidence snippets may contain sensitive source-derived information.
- Document retention/backup considerations.
- Document recommended deployment caution.
- Document missing evidence behavior.
- Document that evidence context is not proof of correctness.

## Patch Set

Expected files:

```text
platform/docs/finding-detail.md
platform/docs/evidence-linking.md
platform/docs/evidence-sensitivity.md
platform/docs/uploaded-artifact-sensitivity.md
platform/docs/README.md
KNOWN_LIMITATIONS.md
```

Required statements:

```text
Uploaded `.ai-debt` artifacts may contain source-derived file paths, line references, hashes, snippets, analysis summaries, and metadata.
The platform stores artifact-derived context for review convenience.
The platform does not clone repositories or browse source code.
Evidence context can be incomplete if older artifacts did not include detail fields.
Reviewers remain responsible for validating decisions.
```

## Tests

Documentation checks:

- Docs mention source-derived evidence.
- Docs state no repository cloning.
- Docs state missing evidence is expected for older artifacts.
- Docs state review decisions do not mutate canonical finding data.
- Docs are linked from platform README.

## Expected Behavior

Users understand the data-sensitivity impact of enabling finding detail persistence.

## Acceptance Criteria

- Evidence sensitivity docs exist.
- Platform docs link to them.
- Known limitations updated.
- No misleading “no source-derived data” claim remains.
- Docs clearly distinguish artifact-derived evidence from repository browsing.

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
