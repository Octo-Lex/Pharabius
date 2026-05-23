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


# W42-S05 — Add Adoption Guide for PET Ticket Workflow

## Slice metadata

| Field | Value |
|---|---|
| Slice | `W42-S05` |
| Title | Add adoption guide for PET ticket workflow |
| Risk | Low |
| Type | Documentation / adoption |
| Primary artifact impact | `docs/` |
| Canonical mutation | None |
| Expected release | `v1.6.1` |

## Scope

Create an adoption guide that explains how Product Engineering Teams should use Pharabius ticket drafts in their planning workflow.

This is a documentation-only slice unless minor links are added to existing docs.

## Goals

- Explain where ticket drafts fit in the Pharabius workflow.
- Show the recommended PET review process.
- Explain review sidecar interactions.
- Explain completeness and validation warnings.
- Provide safe copy-paste guidance for external trackers.
- Clarify that v1.6.x does not create external tickets.
- Clarify ownership: PET reviews, edits, approves, and implements.

## Non-goals

- Do not add runtime behavior.
- Do not add CLI flags.
- Do not add tracker APIs.
- Do not prescribe a specific issue tracker.
- Do not claim tickets are implementation-ready without PET review.
- Do not weaken the no-remediation boundary.

## Patch set

### Files expected to change

| File | Change |
|---|---|
| `docs/PET_TICKET_WORKFLOW.md` | New adoption guide |
| `docs/TICKET_DRAFTS.md` | Link to adoption guide |
| `README.md` or `docs/README.md` | Optional link |
| `ROADMAP.md` | Optional mention if docs convention requires |

### Recommended document structure

```markdown
# PET Ticket Workflow Guide

## Purpose

## Where Ticket Drafts Fit

Repository → Evidence → Findings → Scores → Review → Work Packages → Ticket Drafts → PET Planning

## Recommended Workflow

1. Run analysis/report/plan.
2. Review findings and decisions.
3. Generate ticket drafts.
4. Inspect summary report.
5. Check completeness warnings.
6. Copy selected drafts into tracker.
7. Assign owner and sprint manually.
8. Verify implementation with PET-owned tests/checks.

## Review Decision Behavior

## Completeness Statuses

## Validation Warnings

## Safe Copy-Paste Guidance

## What Pharabius Does Not Do

## Recommended Team Policy

## FAQ
```

### Required boundary statement

Include a clear statement:

```text
Pharabius ticket drafts are repository-local planning artifacts. In v1.6.x, Pharabius does not create, assign, sync, or update tickets in external systems.
```

### Recommended PET policy

Document recommended team rules:

- No ticket should be implemented without PET owner review.
- Security-sensitive tickets require security review.
- Architecture-sensitive tickets require architect/principal review.
- False positives should be recorded in the review sidecar, not deleted silently.
- Deferred items should include a reason.

## Tests

Docs-only. If the project has documentation checks, run them. Optional lightweight tests:

1. Adoption guide exists.
2. Guide contains no claim of external ticket creation.
3. Guide links to `docs/TICKET_DRAFTS.md`.
4. Guide mentions manual PET review.
5. Guide mentions no autonomous remediation.

## Verification commands

```bash
ruff format --check .
ruff check .
mypy src
pytest
python -m build
python scripts/validate_repo.py .
```

Optional text checks:

```bash
grep -n "repository-local planning artifacts" docs/PET_TICKET_WORKFLOW.md
grep -n "does not create" docs/PET_TICKET_WORKFLOW.md
grep -n "Product Engineering Team" docs/PET_TICKET_WORKFLOW.md
```

## Expected behavior

- Users understand how to adopt ticket drafts safely.
- The v1.6.x boundary is clear.
- PET ownership remains explicit.
- No runtime behavior changes.

## Acceptance criteria

- [ ] `docs/PET_TICKET_WORKFLOW.md` exists.
- [ ] Guide explains the end-to-end PET workflow.
- [ ] Guide explains review decision behavior.
- [ ] Guide explains completeness and validation warnings.
- [ ] Guide states that external tickets are not created.
- [ ] Guide states that PET owns approval and implementation.
- [ ] Relevant docs link to the guide.
- [ ] All local gates pass.
