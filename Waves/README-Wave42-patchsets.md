# Wave 42 Patch Sets — v1.6.1 Ticket Draft Polish & Adoption Pack

This directory contains standalone Markdown patch-set files for Wave 42.

## Wave objective

Improve ticket draft usability, validation, completeness reporting, examples, and Product Engineering Team adoption documentation without adding external tracker integrations or changing canonical analysis behavior.

## Release target

| Field | Value |
|---|---|
| Version | `1.6.1` |
| Branch | `roadmap/v1.6.1-ticket-draft-polish` |
| Base | `v1.6.0` |
| Release type | Patch |
| Product theme | Ticket draft polish and PET adoption |

## Slices

| Slice | Title | Risk | File |
|---|---|---|---|
| W42-S01 | Add ticket draft summary report improvements | Low | `W42-S01-ticket-draft-summary-report-improvements.md` |
| W42-S02 | Add richer ticket draft examples | Low | `W42-S02-richer-ticket-draft-examples.md` |
| W42-S03 | Add validation for malformed or missing work packages | Medium | `W42-S03-work-package-validation.md` |
| W42-S04 | Add ticket draft field completeness checks | Medium | `W42-S04-ticket-draft-field-completeness-checks.md` |
| W42-S05 | Add adoption guide for PET ticket workflow | Low | `W42-S05-pet-ticket-workflow-adoption-guide.md` |
| W42-S06 | Docs, changelog, release | Low | `W42-S06-docs-changelog-release.md` |

## Wave stop conditions

Stop or re-plan the wave if any slice causes:

- Default scoring behavior changes.
- Enhanced scoring behavior changes.
- `debt-register.json` mutation from ticket generation.
- Existing `work-packages/` mutation from ticket generation.
- Review sidecar decisions to influence scoring.
- External ticket creation, sync, assignment, or update.
- Autonomous remediation or generated code patches.
- Non-deterministic ticket output at a fixed commit.

## Standard gate set

```bash
ruff format --check .
ruff check .
mypy src
lint-imports
pytest
python -m build
python scripts/validate_repo.py .
```

## Recommended release headline

Pharabius v1.6.1 improves ticket draft usability, validation, completeness checks, examples, and Product Engineering Team adoption documentation without adding external tracker integrations.
