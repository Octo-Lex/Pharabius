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


# W42-S04 — Add Ticket Draft Field Completeness Checks

## Slice metadata

| Field | Value |
|---|---|
| Slice | `W42-S04` |
| Title | Add ticket draft field completeness checks |
| Risk | Medium |
| Type | Quality validation / sidecar reporting |
| Primary artifact impact | Ticket draft summary and JSON index quality metadata |
| Canonical mutation | None |
| Expected release | `v1.6.1` |

## Scope

Add completeness checks for generated ticket drafts so Product Engineering Teams can see whether a draft is ready to copy into a tracker or needs manual enrichment.

This slice should not block draft generation for minor omissions unless the existing ticket schema requires the field. It should report completeness status as metadata.

## Goals

- Mark each generated ticket draft as `complete`, `partial`, or `needs_review`.
- Identify missing or weak fields in generated drafts.
- Include completeness counts in the summary report.
- Include field-level warnings in the JSON index if the schema supports it or can be safely extended.
- Preserve draft generation for partial but usable tickets.
- Improve PET confidence in ticket draft quality.

## Non-goals

- Do not change source work packages.
- Do not infer missing business facts beyond existing Pharabius evidence.
- Do not call AI to enrich missing fields.
- Do not create tracker-specific required-field mappings.
- Do not block all draft generation because of optional missing fields.
- Do not change scoring.

## Patch set

### Files expected to change

| File | Change |
|---|---|
| `src/pharabius/core/tickets.py` | Add completeness evaluator |
| `src/pharabius/schemas/tickets.py` | Add completeness metadata if needed |
| `tests/test_tickets.py` or `tests/test_ticket_completeness.py` | Add completeness tests |
| `docs/TICKET_DRAFTS.md` | Document completeness statuses |

### Suggested completeness model

```python
@dataclass(frozen=True)
class TicketDraftCompleteness:
    status: Literal["complete", "partial", "needs_review"]
    missing_fields: list[str]
    weak_fields: list[str]
    notes: list[str]
```

### Recommended field checks

| Field | Requirement | If missing |
|---|---|---|
| Ticket title / summary | Required | `needs_review` |
| Source work package ID | Required | `needs_review` |
| Linked debt items | Strongly recommended | `partial` |
| Objective | Required | `needs_review` |
| Recommended approach | Strongly recommended | `partial` |
| Verification recommendations | Strongly recommended | `partial` |
| Definition of done | Strongly recommended | `partial` |
| Risks and cautions | Recommended | `partial` |
| Priority/risk rationale | Recommended | `partial` |

Use existing schema names.

### Summary report additions

Add a section:

```markdown
## Draft Completeness

| Status | Count |
|---|---:|
| Complete | 0 |
| Partial | 0 |
| Needs Review | 0 |

## Field Completeness Warnings

| Ticket | Field | Issue |
|---|---|---|
```

### JSON index additions

If safe and backward-compatible, add:

```json
"completeness": {
  "status": "partial",
  "missing_fields": [],
  "weak_fields": ["verification_recommendations"],
  "notes": []
}
```

If adding this would break current consumers, place it under an optional `metadata` object.

## Tests

Add tests for:

1. Complete draft receives `complete`.
2. Missing title receives `needs_review`.
3. Missing verification recommendations receives `partial`.
4. Missing definition of done receives `partial`.
5. Completeness appears in summary report.
6. Completeness appears in JSON index if implemented there.
7. Completeness checks are deterministic.
8. Completeness checks do not mutate source artifacts.
9. Review false positives remain skipped by default.
10. Draft generation continues for partial tickets.

## Verification commands

```bash
ruff format --check .
ruff check .
mypy src
lint-imports
pytest tests/test_tickets.py
pytest tests/test_ticket_completeness.py
pytest
python -m build
python scripts/validate_repo.py .
```

Manual smoke test:

```bash
ai-debt tickets
grep -n "Draft Completeness" .ai-debt/reports/ticket-draft-summary.md
python -m json.tool .ai-debt/ticket-drafts/ticket-drafts.json >/dev/null
```

## Expected behavior

- Ticket drafts gain quality/completeness visibility.
- Partial drafts remain usable but are clearly marked.
- PET reviewers can prioritize which drafts need manual enrichment.
- No runtime behavior changes for scoring, review scoring, or canonical artifacts.

## Acceptance criteria

- [ ] Completeness statuses are generated.
- [ ] Missing required fields produce `needs_review`.
- [ ] Missing recommended fields produce `partial`.
- [ ] Complete drafts are marked `complete`.
- [ ] Summary report includes completeness counts.
- [ ] JSON index includes completeness metadata if safe.
- [ ] No source artifact mutation.
- [ ] No external API writes.
- [ ] All local gates pass.
