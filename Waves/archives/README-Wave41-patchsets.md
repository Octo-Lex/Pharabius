# Wave 41 — v1.6.0 Ticket Draft Export — Patch Set Index

This folder contains standalone Markdown patch-set files for Wave 41.

## Operating model

```text
Wave = planning and acceptance container
Slice = atomic implementation unit
Gate = objective safety checkpoint
```

Wave 41 converts existing Pharabius work packages and reviewed debt findings into repository-local ticket drafts. It improves Product Engineering Team handoff without creating tickets in external systems.

## Release target

| Item | Value |
|---|---|
| Wave | Wave 41 |
| Release | v1.6.0 |
| Branch | `roadmap/v1.6.0-ticket-drafts` |
| Theme | PET actionability |
| External writes | None |
| Canonical mutation | None |

## Patch sets

| Slice | Title | Risk | File |
|---|---|---|---|
| W41-S01 | Ticket draft artifact contract and schema | Medium | `W41-S01-ticket-draft-artifact-contract-and-schema.md` |
| W41-S02 | Generate Markdown ticket drafts from work packages | Medium | `W41-S02-generate-markdown-ticket-drafts-from-work-packages.md` |
| W41-S03 | Generate JSON ticket draft index | Medium | `W41-S03-generate-json-ticket-draft-index.md` |
| W41-S04 | Respect PET review sidecar decisions | Medium | `W41-S04-respect-pet-review-sidecar-decisions.md` |
| W41-S05 | Add CLI command: `ai-debt tickets` | Medium | `W41-S05-add-cli-command-ai-debt-tickets.md` |
| W41-S06 | Docs, tests, changelog, release | Low | `W41-S06-docs-tests-changelog-release.md` |

## Recommended execution order

```text
W41-S01 → W41-S02 → W41-S03 → W41-S04 → W41-S05 → W41-S06
```

## Target artifacts

```text
.ai-debt/
  ticket-drafts/
    TICKET-WP-001.md
    TICKET-WP-002.md
    ticket-drafts.json
  reports/
    ticket-draft-summary.md
```

## Wave-level stop conditions

Stop the wave if any slice causes:

- default scoring behavior to change;
- enhanced scoring behavior to change outside opt-in paths;
- `.ai-debt/debt-register.json` mutation during ticket generation;
- `.ai-debt/work-packages/` mutation during ticket generation;
- review sidecar decisions to influence risk scores;
- external ticket creation, API writes, or network calls;
- false-positive findings to be drafted by default;
- any movement toward autonomous remediation or code modification.

## Wave-level release gate

```bash
ruff format --check .
ruff check .
mypy src
lint-imports
pytest
python -m build
python scripts/validate_repo.py .
```

## Boundary statement

Wave 41 produces local planning artifacts only. Product Engineering Teams remain responsible for creating, assigning, prioritizing, implementing, and verifying real tickets in their chosen systems.
