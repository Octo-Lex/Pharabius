# W43-S05 — Azure DevOps Markdown/CSV export bundle

## Wave

Wave 43 — v1.7.0 Export Bundle & External Tracker Preparation

## Branch

`roadmap/v1.7.0-export-bundles`

## Version Target

`1.7.0`

## Risk

Medium

## Purpose

Generate Azure DevOps-ready repository-local Markdown and CSV export artifacts from existing ticket drafts.

## Scope

- Generate Azure DevOps-flavored Markdown.
- Generate Azure Boards-oriented CSV.
- Create Azure DevOps bundle README.
- Register Azure DevOps artifacts in `manifest.json`.
- Add Azure exporter tests.

## Out of Scope

- Azure DevOps REST API calls.
- Personal access token handling.
- Work item creation.
- Area path or iteration path lookup.
- Assignment or state transitions.

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

### 1. Create `src/pharabius/core/export_bundles_azure.py`

Implement `generate_azure_devops_export_bundle(ticket_drafts_dir, output_dir, *, product_version) -> ExportBundleSummary`.

### 2. Generate Markdown

Write `.ai-debt/export-bundles/azure-devops/azure-devops-ticket-drafts.md` with summary, work item sections, work item type, priority, tags, linked findings, work package, review decision, completeness, and description.

### 3. Generate CSV

Write `.ai-debt/export-bundles/azure-devops/azure-devops-ticket-drafts.csv` with columns: `Title,Work Item Type,Description,Priority,Tags,Linked Findings,Work Package,Source Ticket Draft,Review Decision,Completeness`.

### 4. Safe defaults

Default `Work Item Type` to `User Story`. Use semicolon-separated tags. Do not emit `Assigned To`, `Area Path`, or `Iteration Path` by default.

### 5. Generate README and manifest entry

README must state no Azure DevOps API calls and no work item creation. Manifest must record Azure artifacts.

## Tests

- Generates Azure DevOps Markdown from one ticket draft.
- Generates Azure DevOps CSV from one ticket draft.
- CSV includes required columns.
- Tags use semicolon-separated values.
- Work Item Type defaults to User Story.
- No Assigned To is emitted by default.
- No Area Path is emitted by default.
- No Iteration Path is emitted by default.
- README states no API calls and no work item creation.
- Manifest includes Azure DevOps artifact records.
- Canonical artifacts are not mutated.

## Targeted Verification Commands

```bash
pytest tests/test_export_bundles_azure.py
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

- Azure DevOps bundle files are generated under `.ai-debt/export-bundles/azure-devops/`.
- Artifacts support manual work item creation or CSV preparation.
- No Azure DevOps API is called.

## Acceptance Criteria

- Azure DevOps Markdown, CSV, and README artifacts exist.
- Manifest records Azure DevOps artifacts.
- Assignment, Area Path, and Iteration Path are omitted by default.
- Empty/malformed inputs degrade gracefully.
- All Azure-specific tests and all 7 gates pass.

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
