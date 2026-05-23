# W43-S06 — Docs, examples, tests, changelog, release

## Wave

Wave 43 — v1.7.0 Export Bundle & External Tracker Preparation

## Branch

`roadmap/v1.7.0-export-bundles`

## Version Target

`1.7.0`

## Risk

Low

## Purpose

Finalize Wave 43 for v1.7.0 by updating documentation, examples, changelog, roadmap, known limitations, version metadata, and release validation.

## Scope

- Bump version to 1.7.0.
- Add export bundle documentation.
- Add examples for all tracker bundle types.
- Update CHANGELOG, ROADMAP, and KNOWN_LIMITATIONS.
- Validate examples and release build.
- Prepare release notes.

## Out of Scope

- New exporter behavior.
- Scoring changes.
- Ticket draft schema changes.
- External API integrations.
- Remediation features.

## Guardrails

- No external tracker API writes.
- No issue/work-item creation.
- No automatic assignment, sprint/cycle/milestone, area path, or iteration path handling.
- No mutation of `debt-register.json`, `work-packages/`, review sidecars, scoring artifacts, or source repositories under analysis.
- Export bundles are repository-local handoff artifacts only.
- PET teams remain responsible for review, import, assignment, and implementation.


## Goals

- Preserve Pharabius as a repository-local PET handoff platform.
- Improve tracker preparation without adding live tracker integration.
- Keep every artifact deterministic, reviewable, and safe to commit.
- Preserve existing ticket draft and scoring behavior.

## Patch Set

### 1. Update version

Set package version to `1.7.0` and verify build emits `pharabius-1.7.0`.

### 2. Create `docs/EXPORT_BUNDLES.md`

Document what export bundles are, what they are not, supported trackers, generated artifacts, manual review workflow, safety boundaries, and limitations.

### 3. Add examples

Create examples under `docs/examples/export-bundles/` for Jira, Linear, GitHub Issues, Azure DevOps, and `manifest.json`.

### 4. Update release docs

Update `CHANGELOG.md`, `ROADMAP.md`, and `KNOWN_LIMITATIONS.md` with v1.7.0 status, safety boundaries, and tracker bundle limitations.

### 5. Validate examples

Ensure example CSV files parse, example YAML parses, and example manifest matches the schema.

## Tests

- Example manifest validates against `ExportBundleManifest`.
- Example GitHub YAML parses.
- Example CSV files parse with Python `csv`.
- Documentation links are coherent if doc-link checks exist.
- Build emits version 1.7.0.
- Full gate set passes.

## Targeted Verification Commands

```bash
python -m build
pytest tests/test_export_bundles_schema.py tests/test_export_bundles_jira.py tests/test_export_bundles_linear.py tests/test_export_bundles_github.py tests/test_export_bundles_azure.py
```

## Full Verification Commands

```bash
ruff format --check .
ruff check .
mypy src
lint-imports
pytest
python -m build
python scripts/validate_repo.py .
```


## Expected Behavior

- Version is 1.7.0.
- Export bundle documentation and examples are present.
- Changelog, roadmap, and known limitations reflect the release.
- No runtime behavior is added beyond finalization changes.

## Acceptance Criteria

- `docs/EXPORT_BUNDLES.md` exists.
- Examples exist for all four tracker bundle types.
- Build artifact is `pharabius-1.7.0`.
- Changelog, roadmap, and known limitations are updated.
- All 7 gates pass.

## Wave-Level Acceptance Criteria

- All six Wave 43 slices pass.
- All 7 gates pass.
- Export bundles generate local files only.
- Manifest lists generated tracker bundle artifacts.
- Documentation clearly states no external writes.
- Default scoring behavior is unchanged.
- Enhanced scoring behavior is unchanged.
- Ticket draft generation remains backward compatible.
- No autonomous remediation boundary movement.
