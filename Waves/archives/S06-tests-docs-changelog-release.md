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


# S06 — Tests, Docs, Changelog, Release

Risk: Low

## Scope

Finalize v2.4.0 release with tests, docs, changelog, roadmap updates, and release notes.

## Goals

- Bump version to `2.4.0`.
- Update changelog.
- Update roadmap.
- Update known limitations.
- Verify migrations.
- Verify parser tests.
- Verify API tests.
- Verify frontend build.
- Verify no external write/remediation scope was introduced.
- Prepare release notes.

## Patch Set

Expected files:

```text
CHANGELOG.md
docs/ROADMAP.md
KNOWN_LIMITATIONS.md
platform/docs/finding-detail.md
platform/docs/evidence-linking.md
platform/docs/evidence-sensitivity.md
platform/docs/README.md
platform/frontend/README.md
```

Recommended changelog entry:

```markdown
## v2.4.0

### Added
- Persisted richer finding details from uploaded Pharabius artifacts.
- Added description, location, evidence ID, and evidence reference support for hosted findings.
- Added finding detail API responses.
- Added evidence/context panel to the hosted review modal.
- Added evidence sensitivity and artifact-derived context documentation.

### Safety
- The platform displays artifact-derived evidence context but does not clone repositories or browse source code.
- Review decisions remain hosted workflow state and do not mutate canonical finding records.
- No tracker writes, PR comments, policy engine, claim/gap/readiness review, or remediation were added.
```

## Tests

Final verification:

```bash
pytest
pytest platform/backend/tests
npm --prefix platform/frontend run build
python -m build
python scripts/validate_repo.py .
```

Recommended runtime validation:

```bash
platform/scripts/smoke_docker_compose.sh
```

Recommended PostgreSQL integration validation:

```bash
PHARABIUS_RUN_PG_TESTS=1 pytest platform/backend/tests/integration
```

## Acceptance Criteria

- Version is `2.4.0`.
- Migration exists and is tested.
- Parser persists finding details.
- API returns finding details.
- Review modal displays evidence/context.
- Evidence sensitivity docs exist.
- Frontend build passes.
- Backend tests pass.
- CLI tests pass.
- Release notes do not overclaim source browsing or proof quality.

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
