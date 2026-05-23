# W43-S02 — Jira Markdown/CSV export bundle

## Wave

Wave 43 — v1.7.0 Export Bundle & External Tracker Preparation

## Branch

`roadmap/v1.7.0-export-bundles`

## Version Target

`1.7.0`

## Risk

Medium

## Purpose

Generate Jira-ready repository-local Markdown and CSV export artifacts from existing ticket drafts.

## Scope

- Generate Jira-flavored Markdown.
- Generate Jira-compatible CSV.
- Create Jira bundle README.
- Register Jira artifacts in `manifest.json`.
- Add Jira exporter tests.

## Out of Scope

- Jira REST API calls.
- Jira authentication.
- Jira issue creation.
- Project lookup, sprint assignment, assignee handling, or custom-field discovery.

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

### 1. Create `src/pharabius/core/export_bundles_jira.py`

Implement `generate_jira_export_bundle(ticket_drafts_dir, output_dir, *, product_version) -> ExportBundleSummary`.

### 2. Generate Markdown

Write `.ai-debt/export-bundles/jira/jira-ticket-drafts.md` with summary, generated/skipped counts, issue sections, linked findings, work package IDs, review decisions, completeness, and ticket body.

### 3. Generate CSV

Write `.ai-debt/export-bundles/jira/jira-ticket-drafts.csv` with columns: `Summary,Issue Type,Description,Priority,Labels,Linked Findings,Work Package,Source Ticket Draft,Review Decision,Completeness`. Use Python `csv` escaping.

### 4. Generate README

Write `.ai-debt/export-bundles/jira/README.md` stating this is local-only and does not create Jira issues.

### 5. Update manifest

Append a Jira `ExportBundleSummary` with Markdown and CSV artifacts.

## Tests

- Generates Jira Markdown from one ticket draft.
- Generates Jira CSV from one ticket draft.
- CSV includes required columns.
- CSV escapes commas, quotes, and newlines.
- Markdown includes linked findings and work package ID.
- Missing optional fields degrade gracefully.
- README states no API calls and no issue creation.
- Manifest includes Jira artifact records.
- Empty ticket draft directory produces zero generated count and a warning.
- Canonical artifacts are not mutated.

## Targeted Verification Commands

```bash
pytest tests/test_export_bundles_jira.py
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

- Jira bundle files are generated under `.ai-debt/export-bundles/jira/`.
- Artifacts are suitable for manual copy/paste or CSV import preparation.
- No Jira API is called.

## Acceptance Criteria

- Jira Markdown, CSV, and README artifacts exist.
- Manifest records Jira artifacts.
- CSV uses safe escaping.
- Empty/malformed inputs degrade gracefully.
- All Jira-specific tests and all 7 gates pass.

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
