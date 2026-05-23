# Wave 42 — v1.6.1 Ticket Draft Polish & Adoption Pack

**Wave objective:** Improve the usability, validation, examples, and adoption documentation for repository-local ticket drafts without adding external tracker integrations, canonical artifact mutation, or autonomous remediation.

**Release target:** `v1.6.1`  
**Branch:** `roadmap/v1.6.1-ticket-draft-polish`  
**Base:** `v1.6.0`  
**Risk posture:** Patch release, adoption/polish only

## Wave guardrails

- Do not mutate `debt-register.json`.
- Do not mutate existing `work-packages/`.
- Do not change scoring behavior.
- Do not let the review sidecar influence scoring.
- Do not create tickets in Jira, Linear, GitHub Issues, Azure DevOps, or any external system.
- Do not add autonomous remediation, generated patches, dependency upgrades, code modification, or PR creation.
- Keep all new outputs repository-local under `.ai-debt/`.
- Preserve deterministic output at a fixed commit and fixed input artifact set.


# W42-S06 — Docs, Changelog, Release

## Slice metadata

| Field | Value |
|---|---|
| Slice | `W42-S06` |
| Title | Docs, changelog, release |
| Risk | Low |
| Type | Release finalization |
| Primary artifact impact | Version, changelog, roadmap, docs |
| Canonical mutation | None |
| Expected release | `v1.6.1` |

## Scope

Finalize the v1.6.1 release after W42-S01 through W42-S05 are complete.

This slice should not add new product behavior beyond documentation, versioning, release metadata, and final validation.

## Goals

- Bump version to `1.6.1`.
- Update changelog with all Wave 42 slices.
- Mark v1.6.1 in roadmap.
- Update known limitations if needed.
- Ensure docs link together coherently.
- Verify examples are present and accurate.
- Run full quality gates.
- Prepare release notes.

## Non-goals

- Do not add new ticket behavior.
- Do not tune scoring.
- Do not add tracker API integration.
- Do not alter canonical artifact contracts beyond documented optional metadata added in earlier slices.
- Do not expand scope into v1.7.0.

## Patch set

### Files expected to change

| File | Change |
|---|---|
| `pyproject.toml` | Version `1.6.1` |
| `CHANGELOG.md` | Add v1.6.1 entry |
| `ROADMAP.md` | Mark v1.6.1 completed/planned status |
| `KNOWN_LIMITATIONS.md` | Update ticket-draft limitations if needed |
| `docs/TICKET_DRAFTS.md` | Final links and wording |
| `docs/PET_TICKET_WORKFLOW.md` | Final polish if introduced in W42-S05 |

### Changelog entry

Recommended structure:

```markdown
## v1.6.1

### Added
- Improved ticket draft summary report with clearer counts, skipped items, and warnings.
- Added richer ticket draft examples.
- Added validation behavior for malformed or missing work packages.
- Added ticket draft completeness checks.
- Added Product Engineering Team ticket workflow adoption guide.

### Changed
- Improved ticket draft documentation and examples.

### Safety
- No changes to scoring behavior.
- No changes to canonical debt register behavior.
- No external ticketing API writes.
- No autonomous remediation.
```

### Known limitations update

Add or update:

```markdown
Ticket drafts are repository-local planning artifacts. Pharabius v1.6.x does not create, sync, assign, or update external tracker tickets. Product Engineering Teams must review and adapt drafts before implementation.
```

### Release notes headline

```text
Pharabius v1.6.1 improves ticket draft usability, validation, completeness checks, examples, and PET adoption documentation without adding external tracker integrations.
```

## Tests

Run the full gate set.

Expected test changes:

- W42-S01 to W42-S04 may add tests.
- W42-S05 and W42-S06 may add no tests if docs-only.
- Coverage must not meaningfully regress.

## Verification commands

```bash
ruff format --check .
ruff check .
mypy src
lint-imports
pytest
python -m build
python scripts/validate_repo.py .
```

Additional release checks:

```bash
python -m build
ls dist/*1.6.1*
grep -n "v1.6.1" CHANGELOG.md
grep -n "1.6.1" pyproject.toml
grep -n "Ticket drafts" KNOWN_LIMITATIONS.md
```

## Expected behavior

- Package builds as `pharabius-1.6.1`.
- All tests pass.
- Docs are consistent.
- Ticket draft workflow remains repository-local.
- No canonical artifacts are mutated by ticket generation.
- No scoring behavior changes.

## Acceptance criteria

- [ ] Version is `1.6.1`.
- [ ] Changelog includes v1.6.1.
- [ ] Roadmap reflects v1.6.1.
- [ ] Known limitations reflect ticket draft boundaries.
- [ ] Docs are linked and coherent.
- [ ] Build artifact uses `1.6.1`.
- [ ] All 7 local gates pass.
- [ ] CI passes before merge.
- [ ] Release notes are prepared.
