# W43-S04 — GitHub Issues Markdown/YAML export bundle

## Wave

Wave 43 — v1.7.0 Export Bundle & External Tracker Preparation

## Branch

`roadmap/v1.7.0-export-bundles`

## Version Target

`1.7.0`

## Risk

Medium

## Purpose

Generate GitHub Issues-ready repository-local Markdown and YAML issue draft artifacts from existing ticket drafts.

## Scope

- Generate GitHub Issues-flavored Markdown.
- Generate one YAML draft per ticket.
- Create GitHub Issues bundle README.
- Register GitHub Issues artifacts in `manifest.json`.
- Add GitHub exporter tests.

## Out of Scope

- GitHub REST or GraphQL API calls.
- Issue creation.
- Assignee handling.
- Milestone or project board updates.
- GitHub Actions workflow generation.

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

### 1. Create `src/pharabius/core/export_bundles_github.py`

Implement `generate_github_issues_export_bundle(ticket_drafts_dir, output_dir, *, product_version) -> ExportBundleSummary`.

### 2. Generate Markdown

Write `.ai-debt/export-bundles/github-issues/github-issues-ticket-drafts.md` with summary, issue sections, labels, linked findings, work package, review decision, completeness, and body.

### 3. Generate YAML issue drafts

Write `.ai-debt/export-bundles/github-issues/issues/TICKET-001.yaml` per draft with `schema_version`, `source_ticket`, `title`, `labels`, `linked_findings`, `work_package`, `review_decision`, `completeness`, and `body`.

### 4. Safe defaults

Do not emit assignees, milestones, projects, or repository-specific permission fields by default.

### 5. Generate README and manifest entry

README must state no GitHub API calls and no issue creation. Manifest must record Markdown and YAML artifact locations.

## Tests

- Generates GitHub Issues Markdown from one ticket draft.
- Generates one YAML file per ticket draft.
- YAML includes schema version, title, labels, linked findings, and body.
- Labels include priority and category labels.
- No assignee is emitted by default.
- No milestone is emitted by default.
- YAML handles colons, quotes, and multiline descriptions.
- README states no API calls and no issue creation.
- Manifest includes GitHub Issues artifact records.
- Canonical artifacts are not mutated.

## Targeted Verification Commands

```bash
pytest tests/test_export_bundles_github.py
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

- GitHub Issues bundle files are generated under `.ai-debt/export-bundles/github-issues/`.
- YAML files can be reviewed by humans or used by future automation outside v1.7.0.
- No GitHub API is called.

## Acceptance Criteria

- GitHub Issues Markdown, YAML, and README artifacts exist.
- Manifest records GitHub Issues artifacts.
- YAML omits assignees and milestones by default.
- Empty/malformed inputs degrade gracefully.
- All GitHub-specific tests and all 7 gates pass.

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
