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


# W42-S02 — Add Richer Ticket Draft Examples

## Slice metadata

| Field | Value |
|---|---|
| Slice | `W42-S02` |
| Title | Add richer ticket draft examples |
| Risk | Low |
| Type | Documentation / examples |
| Primary artifact impact | `docs/examples/` |
| Canonical mutation | None |
| Expected release | `v1.6.1` |

## Scope

Add richer examples that demonstrate the v1.6.0 ticket-draft workflow and the v1.6.1 summary improvements.

This slice should be documentation and example artifacts only. It should not change runtime behavior.

## Goals

- Provide realistic example ticket drafts for Product Engineering Team review.
- Show Markdown and JSON ticket draft examples.
- Show how review sidecar decisions affect ticket drafting.
- Show skipped false-positive behavior.
- Show warning/validation behavior using static examples.
- Make adoption easier for users evaluating Pharabius output without running the CLI.

## Non-goals

- Do not change ticket generation code.
- Do not change schemas.
- Do not change tests unless snapshot/example validation tests are already part of the examples convention.
- Do not add external tracker-specific templates.
- Do not imply that Pharabius creates external tickets.

## Patch set

### Files expected to change

| File | Change |
|---|---|
| `docs/examples/ticket-draft.md` | Expand single Markdown example |
| `docs/examples/ticket-drafts.json` | Expand JSON index example |
| `docs/examples/ticket-draft-summary.md` | Add improved summary example |
| `docs/examples/ticket-draft-review-sidecar-example.json` | Optional example review sidecar |
| `docs/TICKET_DRAFTS.md` | Link to examples if needed |

### Recommended example set

Add examples for:

1. Accepted architecture remediation work package.
2. Needs-review security-sensitive work package.
3. Deferred operational work package.
4. False-positive finding skipped by default.
5. Work package with validation warning.

### Example constraints

Examples must make the boundary explicit:

```text
This is a repository-local draft. Pharabius does not create, assign, or sync external tracker tickets in v1.6.x.
```

### Example fields to show

For Markdown ticket drafts:

```markdown
# Ticket Draft: TICKET-001

## Summary

## Source Work Package

## Linked Debt Items

## Priority and Risk Rationale

## Review State

## Objective

## Recommended Engineering Approach

## Verification Recommendations

## Risks and Cautions

## Definition of Done

## Notes for Product Engineering Team
```

For JSON index:

```json
{
  "schema_version": "1.0",
  "generated_by": "pharabius",
  "drafts": [
    {
      "ticket_id": "TICKET-001",
      "source_work_package_id": "WP-001",
      "status": "drafted",
      "review_state": "accepted",
      "path": ".ai-debt/ticket-drafts/TICKET-001.md"
    }
  ],
  "skipped": []
}
```

Use the actual v1.6.0 schema names where they differ.

## Tests

This slice may be docs-only. If the project already validates examples, add tests for:

1. JSON examples parse successfully.
2. Example `schema_version` matches ticket schema.
3. Example paths are repository-local.
4. Examples do not mention external ticket creation as an active behavior.
5. Example Markdown contains required sections.

## Verification commands

```bash
ruff format --check .
ruff check .
mypy src
pytest
python -m build
python scripts/validate_repo.py .
```

Optional example validation:

```bash
python -m json.tool docs/examples/ticket-drafts.json >/dev/null
grep -R "Jira API\|Linear API\|GitHub Issues API" docs/examples docs/TICKET_DRAFTS.md
```

## Expected behavior

- No runtime behavior changes.
- Users can inspect representative ticket draft outputs.
- Examples clarify included, skipped, and review-aware behavior.
- External tracker integration remains explicitly out of scope.

## Acceptance criteria

- [ ] At least one Markdown ticket draft example is present.
- [ ] At least one JSON ticket draft index example is present.
- [ ] Example summary report reflects W42-S01 format.
- [ ] Examples demonstrate review-aware behavior.
- [ ] Examples demonstrate skipped false-positive behavior.
- [ ] Examples state that no external tickets are created.
- [ ] All local gates pass.
