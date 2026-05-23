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


# W42-S01 — Add Ticket Draft Summary Report Improvements

## Slice metadata

| Field | Value |
|---|---|
| Slice | `W42-S01` |
| Title | Add ticket draft summary report improvements |
| Risk | Low |
| Type | Report polish / sidecar output |
| Primary artifact impact | `.ai-debt/reports/ticket-draft-summary.md` |
| Canonical mutation | None |
| Expected release | `v1.6.1` |

## Scope

Improve the human-readable ticket draft summary report produced by the ticket-draft generation workflow.

This slice is report-only. It should not change ticket draft selection semantics, ticket draft content semantics, scoring, work package generation, review decisions, or canonical artifacts.

## Goals

- Make `ticket-draft-summary.md` easier for Product Engineering Teams to review.
- Show included, skipped, and warning counts clearly.
- Summarize review-sidecar effects when review decisions are present.
- Surface validation issues without failing the whole command.
- Make the report usable as a PR review artifact.
- Preserve deterministic ordering.

## Non-goals

- Do not change the ticket draft schema.
- Do not change Markdown ticket draft body content.
- Do not change JSON index shape unless already supported by v1.6.0.
- Do not add CLI flags.
- Do not add external tracker integration.
- Do not mutate canonical artifacts.

## Patch set

### Files expected to change

| File | Change |
|---|---|
| `src/pharabius/core/tickets.py` | Improve summary Markdown rendering |
| `tests/test_tickets.py` or `tests/test_ticket_summary.py` | Add summary report tests |
| `docs/examples/ticket-draft-summary.md` | Optional updated example, if examples already exist |

### Implementation details

Add or update a summary renderer that emits this structure:

```markdown
# Ticket Draft Summary

## Generation Summary

| Metric | Count |
|---|---:|
| Work packages scanned | 0 |
| Ticket drafts generated | 0 |
| Work packages skipped | 0 |
| Validation warnings | 0 |
| Review decisions applied | 0 |

## Output Artifacts

| Artifact | Path |
|---|---|
| Ticket draft index | `.ai-debt/ticket-drafts/ticket-drafts.json` |
| Markdown drafts | `.ai-debt/ticket-drafts/*.md` |

## Review Decision Summary

| Decision | Count | Behavior |
|---|---:|---|
| Accepted | 0 | Drafted |
| Needs Review | 0 | Drafted with caution |
| Deferred | 0 | Skipped or marked deferred, depending existing v1.6.0 behavior |
| False Positive | 0 | Skipped |

## Drafts

| Ticket | Work Package | Priority | Review State | Status | Path |
|---|---|---|---|---|---|

## Skipped Items

| Work Package | Reason |
|---|---|

## Warnings and Limitations

- Warning text.
```

The exact labels may follow existing v1.6.0 naming, but the report must contain equivalent information.

### Determinism rules

- Sort drafts by ticket ID or work package ID.
- Sort skipped items by work package ID.
- Sort warnings by work package ID, then warning code.
- Avoid timestamps in deterministic sections unless already part of the existing ticket generation contract.

## Tests

Add tests for:

1. Summary contains generation counts.
2. Summary lists generated Markdown ticket paths.
3. Summary lists skipped work packages.
4. Summary includes review decision breakdown when review sidecar is present.
5. Summary remains valid when no tickets are generated.
6. Summary is deterministic across repeated runs with identical inputs.
7. Summary does not mutate `debt-register.json`.
8. Summary does not mutate `work-packages/`.

## Verification commands

```bash
ruff format --check .
ruff check .
mypy src
lint-imports
pytest tests/test_tickets.py
pytest
python -m build
python scripts/validate_repo.py .
```

Optional manual verification:

```bash
ai-debt tickets
cat .ai-debt/reports/ticket-draft-summary.md
git diff -- .ai-debt/debt-register.json .ai-debt/work-packages/
```

## Expected behavior

- `ai-debt tickets` still generates repository-local ticket artifacts only.
- The summary report is clearer and more reviewable.
- Skipped items and warnings are visible.
- No existing canonical artifacts change.
- Existing v1.6.0 valid workflows continue to pass.

## Acceptance criteria

- [ ] `ticket-draft-summary.md` includes generation counts.
- [ ] `ticket-draft-summary.md` includes output artifact paths.
- [ ] `ticket-draft-summary.md` includes draft table.
- [ ] `ticket-draft-summary.md` includes skipped items when present.
- [ ] `ticket-draft-summary.md` includes warning/limitation section.
- [ ] Output is deterministic.
- [ ] No scoring changes.
- [ ] No canonical artifact mutation.
- [ ] All local gates pass.
