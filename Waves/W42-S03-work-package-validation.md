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


# W42-S03 — Add Validation for Malformed or Missing Work Packages

## Slice metadata

| Field | Value |
|---|---|
| Slice | `W42-S03` |
| Title | Add validation for malformed or missing work packages |
| Risk | Medium |
| Type | Tooling behavior / validation |
| Primary artifact impact | Ticket draft sidecars and summary warnings |
| Canonical mutation | None |
| Expected release | `v1.6.1` |

## Scope

Improve ticket-draft generation resilience when work packages are missing, malformed, partially populated, or unreadable.

This slice may change ticket generation behavior only for invalid or incomplete inputs. It must not change behavior for valid v1.6.0 work packages except to add clearer warnings.

## Goals

- Avoid hard failures when individual work packages are malformed.
- Skip invalid work packages with clear warning reasons.
- Continue generating drafts for valid work packages.
- Include validation issues in `ticket-drafts.json` and/or `ticket-draft-summary.md`, following existing artifact contracts where possible.
- Return a successful exit for recoverable validation issues unless the command cannot run at all.
- Return a non-zero exit only for unrecoverable command-level failures if that is consistent with existing CLI conventions.

## Non-goals

- Do not rewrite or repair malformed work package files.
- Do not mutate existing work packages.
- Do not invent missing debt evidence.
- Do not change scoring.
- Do not add external tracker integration.
- Do not make the AI layer repair ticket drafts.

## Patch set

### Files expected to change

| File | Change |
|---|---|
| `src/pharabius/core/tickets.py` | Add validation and skip/warning behavior |
| `src/pharabius/schemas/tickets.py` | Add validation issue type only if needed |
| `tests/test_tickets.py` or `tests/test_ticket_validation.py` | Add malformed work package tests |
| `docs/TICKET_DRAFTS.md` | Briefly document validation behavior |

### Validation issue model

Prefer a small structured issue object:

```python
@dataclass(frozen=True)
class TicketDraftValidationIssue:
    source_path: str
    work_package_id: str | None
    code: str
    severity: Literal["warning", "error"]
    message: str
```

Potential codes:

| Code | Severity | Behavior |
|---|---|---|
| `missing_work_packages_directory` | warning | Generate zero drafts, report warning |
| `empty_work_packages_directory` | warning | Generate zero drafts, report warning |
| `invalid_work_package_json` | warning | Skip file |
| `missing_work_package_id` | warning | Skip file |
| `missing_title` | warning | Draft with fallback title only if existing schema permits; otherwise skip |
| `missing_linked_debt_items` | warning | Draft with warning if allowed |
| `unreadable_work_package` | warning/error | Skip file |

Use existing repository conventions for dataclasses/Pydantic models.

### Behavior rules

- Valid work packages should still produce drafts.
- Invalid files should not block valid files.
- Every skipped invalid work package should have a reason.
- Missing directory should not crash.
- Empty directory should not crash.
- Output should be deterministic.

## Tests

Add tests for:

1. Missing `work-packages/` directory.
2. Empty `work-packages/` directory.
3. Malformed JSON work package.
4. Missing required ID.
5. Missing title.
6. Mixed valid and invalid work packages.
7. Validation warnings appear in summary report.
8. Validation warnings appear in JSON index if supported.
9. No mutation of malformed source files.
10. Exit behavior is consistent with CLI conventions.

## Verification commands

```bash
ruff format --check .
ruff check .
mypy src
lint-imports
pytest tests/test_tickets.py
pytest tests/test_ticket_validation.py
pytest
python -m build
python scripts/validate_repo.py .
```

Manual smoke test:

```bash
mkdir -p /tmp/pharabius-ticket-validation/.ai-debt/work-packages
printf '{ invalid json' > /tmp/pharabius-ticket-validation/.ai-debt/work-packages/WP-BAD.json
ai-debt tickets --repo /tmp/pharabius-ticket-validation || true
cat /tmp/pharabius-ticket-validation/.ai-debt/reports/ticket-draft-summary.md
```

Adjust command options to match actual CLI syntax.

## Expected behavior

- Ticket generation is resilient to bad input.
- Users receive clear warnings instead of stack traces.
- Valid work packages still generate ticket drafts.
- Invalid work packages are skipped or degraded according to documented rules.
- No canonical artifacts are changed.

## Acceptance criteria

- [ ] Missing work package directory is handled gracefully.
- [ ] Empty work package directory is handled gracefully.
- [ ] Malformed work package files do not crash the whole command.
- [ ] Mixed valid/invalid inputs generate drafts for valid items.
- [ ] Every skipped invalid item has an explanatory reason.
- [ ] Warnings are visible in summary report.
- [ ] No work packages are modified.
- [ ] No debt register mutation.
- [ ] All local gates pass.
