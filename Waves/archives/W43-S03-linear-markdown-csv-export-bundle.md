# W43-S03 — Linear Markdown/CSV export bundle

## Wave

Wave 43 — v1.7.0 Export Bundle & External Tracker Preparation

## Branch

`roadmap/v1.7.0-export-bundles`

## Version Target

`1.7.0`

## Risk

Medium

## Purpose

Generate Linear-ready repository-local Markdown and CSV export artifacts from existing ticket drafts.

## Scope

- Generate Linear-flavored Markdown.
- Generate Linear-oriented CSV.
- Create Linear bundle README.
- Register Linear artifacts in `manifest.json`.
- Add Linear exporter tests.

## Out of Scope

- Linear GraphQL API calls.
- Linear authentication.
- Linear issue creation.
- Team/project/cycle lookup or assignment.
- User assignment.

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

### 1. Create `src/pharabius/core/export_bundles_linear.py`

Implement `generate_linear_export_bundle(ticket_drafts_dir, output_dir, *, product_version) -> ExportBundleSummary`.

### 2. Generate Markdown

Write `.ai-debt/export-bundles/linear/linear-ticket-drafts.md` with summary, issue sections, priority, labels, linked findings, work package, review decision, completeness, and body.

### 3. Generate CSV

Write `.ai-debt/export-bundles/linear/linear-ticket-drafts.csv` with columns: `Title,Description,Priority,Labels,Linked Findings,Work Package,Source Ticket Draft,Review Decision,Completeness`.

### 4. Priority mapping

Map Pharabius priorities conservatively: Critical→Urgent, High→High, Medium→Medium, Low→Low. Document that these are suggestions.

### 5. Generate README and manifest entry

README must state no Linear API calls and no issue creation. Manifest must record Linear artifacts.

## Tests

- Generates Linear Markdown from one ticket draft.
- Generates Linear CSV from one ticket draft.
- CSV includes required columns.
- Priority mapping is deterministic.
- Labels include Pharabius and debt category labels.
- Completeness and review decision are preserved.
- README states no API calls and no issue creation.
- Manifest includes Linear artifact records.
- Empty ticket draft directory produces zero generated count and a warning.
- Canonical artifacts are not mutated.

## Targeted Verification Commands

```bash
pytest tests/test_export_bundles_linear.py
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

- Linear bundle files are generated under `.ai-debt/export-bundles/linear/`.
- Artifacts are useful for manual Linear issue creation or CSV transformation.
- No Linear API is called.

## Acceptance Criteria

- Linear Markdown, CSV, and README artifacts exist.
- Manifest records Linear artifacts.
- Priority mapping is deterministic and documented.
- Empty/malformed inputs degrade gracefully.
- All Linear-specific tests and all 7 gates pass.

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
