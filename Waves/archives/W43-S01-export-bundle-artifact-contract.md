# W43-S01 — Export bundle artifact contract

## Wave

Wave 43 — v1.7.0 Export Bundle & External Tracker Preparation

## Branch

`roadmap/v1.7.0-export-bundles`

## Version Target

`1.7.0`

## Risk

Medium

## Purpose

Define the repository-local export bundle artifact contract before implementing tracker-specific outputs.

## Scope

- Add export bundle schema models.
- Define `.ai-debt/export-bundles/` layout.
- Define tracker enum values for Jira, Linear, GitHub Issues, and Azure DevOps.
- Define export bundle manifest structure.
- Add deterministic path and manifest-writing helpers.
- Add schema and serialization tests.

## Out of Scope

- Tracker-specific export generation.
- CLI command changes.
- External API integration.
- Ticket draft behavior changes.

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

### 1. Create `src/pharabius/schemas/export_bundles.py`

Define `TrackerKind`, `ExportBundleFormat`, `ExportBundleArtifact`, `ExportBundleSummary`, and `ExportBundleManifest` with `schema_version: "1.0"`.

### 2. Create `src/pharabius/core/export_bundles.py`

Add output-path helpers for `.ai-debt/export-bundles/`, tracker slug normalization, manifest serialization, and deterministic artifact path handling.

### 3. Add manifest writer

Implement `write_export_bundle_manifest(output_dir: Path, manifest: ExportBundleManifest) -> Path`. It must create directories and write stable, pretty JSON.

## Tests

- Manifest defaults to `schema_version == "1.0"`.
- Tracker enum includes Jira, Linear, GitHub Issues, Azure DevOps.
- Format enum includes Markdown, CSV, YAML, JSON.
- Manifest serializes with zero bundles.
- Manifest writer creates `.ai-debt/export-bundles/manifest.json`.
- Relative artifact paths are preserved.
- No canonical artifacts are mutated.

## Targeted Verification Commands

```bash
pytest tests/test_export_bundles_schema.py
python -m build
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

- A typed export bundle contract exists.
- No tracker-specific files are generated yet.
- No CLI behavior changes.
- Later slices can build on the manifest contract without reworking the schema.

## Acceptance Criteria

- `src/pharabius/schemas/export_bundles.py` exists.
- Export bundle root is `.ai-debt/export-bundles/`.
- Manifest is versioned, deterministic, and JSON-serializable.
- All schema tests pass.
- No external API integration is introduced.

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
