# Wave 43 — v1.7.0 Export Bundle & External Tracker Preparation — Patch Set Index

## Purpose

Wave 43 prepares Pharabius for external tracker workflows by generating repository-local export bundles for Jira, Linear, GitHub Issues, and Azure DevOps.

This wave does **not** create issues or write to external systems. It only produces files that PET teams can review, copy, import, or adapt.

## Branch

`roadmap/v1.7.0-export-bundles`

## Version Target

`1.7.0`

## Operating Model

- **Wave** = planning and acceptance container.
- **Slice** = atomic implementation unit.
- **Gate** = objective safety checkpoint.

## Slices

| Slice | Title | Risk | Patch Set |
|---|---|---|---|
| W43-S01 | Export bundle artifact contract | Medium | `W43-S01-export-bundle-artifact-contract.md` |
| W43-S02 | Jira Markdown/CSV export bundle | Medium | `W43-S02-jira-markdown-csv-export-bundle.md` |
| W43-S03 | Linear Markdown/CSV export bundle | Medium | `W43-S03-linear-markdown-csv-export-bundle.md` |
| W43-S04 | GitHub Issues Markdown/YAML export bundle | Medium | `W43-S04-github-issues-markdown-yaml-export-bundle.md` |
| W43-S05 | Azure DevOps Markdown/CSV export bundle | Medium | `W43-S05-azure-devops-markdown-csv-export-bundle.md` |
| W43-S06 | Docs, examples, tests, changelog, release | Low | `W43-S06-docs-examples-tests-changelog-release.md` |

## Wave-Level Guardrails

- No external tracker API writes.
- No issue/work-item creation.
- No automatic assignment, sprint/cycle/milestone, area path, or iteration path handling.
- No mutation of `debt-register.json`, `work-packages/`, review sidecars, scoring artifacts, or source repositories under analysis.
- Export bundles are repository-local handoff artifacts only.
- PET teams remain responsible for review, import, assignment, and implementation.


## Expected Output

```text
.ai-debt/
  export-bundles/
    manifest.json
    jira/
      README.md
      jira-ticket-drafts.md
      jira-ticket-drafts.csv
    linear/
      README.md
      linear-ticket-drafts.md
      linear-ticket-drafts.csv
    github-issues/
      README.md
      github-issues-ticket-drafts.md
      issues/
        TICKET-001.yaml
    azure-devops/
      README.md
      azure-devops-ticket-drafts.md
      azure-devops-ticket-drafts.csv
```

## Full Gate Set

```bash
ruff format --check .
ruff check .
mypy src
lint-imports
pytest
python -m build
python scripts/validate_repo.py .
```


## Wave Acceptance Criteria

- All six slices completed.
- All 7 gates pass.
- Tracker bundles generate local files only.
- Manifest lists generated tracker bundle artifacts.
- Documentation clearly states no external writes.
- Default scoring behavior unchanged.
- Enhanced scoring behavior unchanged.
- Ticket draft generation backward compatible.
- No autonomous remediation boundary movement.
