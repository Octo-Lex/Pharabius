# PET Ticket Workflow Guide

## Purpose

This guide explains how Product Engineering Teams (PETs) should use Pharabius ticket
drafts in their technical debt planning workflow. It covers the recommended end-to-end
process from analysis through to implementation.

## Where Ticket Drafts Fit

Pharabius produces ticket drafts as the final step in a deterministic analysis pipeline:

```
Repository → Evidence → Findings → Risk Scores → Review Decisions → Work Packages → Ticket Drafts → PET Planning
```

Each step builds on the previous one. Ticket drafts are generated from work packages
that have been filtered through the optional PET review sidecar.

## Recommended Workflow

### Step 1: Run Analysis

```bash
ai-debt init --repo /path/to/repo
ai-debt scan --repo /path/to/repo
ai-debt analyze --repo /path/to/repo --no-ai
ai-debt report --repo /path/to/repo
ai-debt plan --repo /path/to/repo
```

Or use the combined command:

```bash
ai-debt run --repo /path/to/repo --no-ai
```

### Step 2: Review Findings and Make Decisions

```bash
# Initialize the review sidecar
ai-debt review --init --repo /path/to/repo

# Review findings and record decisions in .ai-debt/review/decisions.json
# Statuses: accepted, rejected, deferred, needs-investigation, duplicate,
#           already-fixed, risk-accepted
```

### Step 3: Generate Ticket Drafts

```bash
ai-debt tickets --repo /path/to/repo
```

### Step 4: Inspect Summary Report

Read `.ai-debt/reports/ticket-draft-summary.md` for:

- **Generation Summary**: How many work packages were scanned, drafted, and skipped.
- **Review Decision Summary**: How PET review decisions affected drafting.
- **Draft Completeness**: How many drafts are complete, partial, or need review.
- **Field Completeness Warnings**: Which drafts have missing or weak fields.
- **Validation Issues**: Any malformed work packages that were skipped.

### Step 5: Check Completeness Warnings

For drafts marked `partial` or `needs_review`, enrich the content before copying
to a tracker:

- **Missing title or objective**: Revisit the source work package.
- **Missing linked debt items**: Verify the debt register is complete.
- **Missing approach or verification**: Add engineering-specific context.

### Step 6: Copy Selected Drafts into Tracker

Open individual ticket drafts from `.ai-debt/ticket-drafts/` and copy the
relevant sections into your team's issue tracker (Jira, Linear, GitHub Issues,
Azure DevOps, or any other system).

### Step 7: Assign Owner and Sprint

Pharabius does not assign owners, sprints, or labels in external systems.
The PET owns:

- Prioritization and scheduling
- Owner assignment
- Sprint/milestone planning
- Implementation decisions

### Step 8: Verify Implementation

After implementation, use Pharabius verification:

```bash
ai-debt verify --repo /path/to/repo
```

## Review Decision Behavior

The PET review sidecar (`.ai-debt/review/decisions.json`) affects ticket drafting:

| Decision | Effect on Ticket Drafts |
|---|---|
| `accepted` | Draft is generated |
| `needs-investigation` | Draft is generated |
| `not_reviewed` | Draft is generated (no review decision yet) |
| `rejected` | Draft is **skipped** |
| `duplicate` | Draft is **skipped** |
| `already-fixed` | Draft is **skipped** |
| `risk-accepted` | Draft is **skipped** |
| `deferred` | Draft is **skipped by default**; use `--include-deferred` to include |

To include deferred items:

```bash
ai-debt tickets --repo /path/to/repo --include-deferred
```

## Completeness Statuses

Each ticket draft is evaluated for field completeness:

| Status | Meaning | Action Required |
|---|---|---|
| `complete` | All required and recommended fields present | Ready for PET review |
| `partial` | Missing recommended fields (e.g., verification, definition of done) | Enrich before copying to tracker |
| `needs_review` | Missing required fields (e.g., title, objective) | Requires significant manual enrichment |

## Validation Warnings

The ticket generation process may produce validation warnings:

| Code | Meaning |
|---|---|
| `missing_work_packages_directory` | No `work-packages/` directory found |
| `empty_work_packages_directory` | No Markdown work package files found |
| `unreadable_work_package` | File could not be parsed |
| `missing_work_package_id` | File does not follow `WP-NNN-slug.md` naming |

Validation warnings appear in:

- The summary report under "Validation Issues"
- The JSON index under `validation_issues`

## Safe Copy-Paste Guidance

When copying ticket drafts to external trackers:

1. **Review before copy**: Read the full draft. Pharabius generates content from
   deterministic evidence — it does not understand your team's context.

2. **Check completeness**: Drafts marked `partial` or `needs_review` need manual
   enrichment before they are actionable.

3. **Preserve evidence links**: Keep the "Linked Debt Items" and "Evidence" references
   for traceability.

4. **Add team context**: Add sprint, owner, story points, and any team-specific fields
   that Pharabius does not generate.

5. **Do not auto-file**: Pharabius does not create tickets in external systems.
   Manual filing ensures PET ownership.

## What Pharabius Does Not Do

> Pharabius ticket drafts are repository-local planning artifacts. In v1.6.x,
> Pharabius does not create, assign, sync, or update tickets in external systems.

Specifically:

- Does not modify production code
- Does not generate patches or dependency upgrades
- Does not create PRs
- Does not call Jira, Linear, GitHub Issues, or Azure DevOps APIs
- Does not autonomously remediate findings
- Does not store credentials for external systems

## Recommended Team Policy

- **No ticket should be implemented without PET owner review.**
- **Security-sensitive tickets require security team review.**
- **Architecture-sensitive tickets require architect/principal review.**
- **False positives should be recorded in the review sidecar**, not deleted silently.
- **Deferred items should include a reason** in the review sidecar.

## FAQ

### Can I customize ticket draft format?

Yes. Use governance presets (`startup-lean`, `platform-engineering`,
`security-sensitive`, `compliance-sensitive`) to tailor work package templates,
which flow into ticket drafts. See `docs/PRESET_REFERENCE.md`.

### Can I regenerate tickets after changing review decisions?

Yes. Update `.ai-debt/review/decisions.json` and re-run `ai-debt tickets`.
Use `--force` to overwrite existing drafts.

### What happens if I skip the review step?

Without a review sidecar, all work packages default to `not_reviewed` and all
drafts are generated. The review sidecar is optional but recommended for
filtering false positives.

### How do I see what was filtered?

Check `.ai-debt/reports/ticket-draft-summary.md` under "Skipped Items" and
"Review Decision Summary".

### Where are ticket drafts stored?

All drafts are in `.ai-debt/ticket-drafts/` within the repository. They are
intended to be local artifacts and should not be committed to version control.

## Related Documentation

- [Ticket Drafts Reference](TICKET_DRAFTS.md)
- [Review Workflow](REVIEW_WORKFLOW.md)
- [Governance Presets](PRESET_REFERENCE.md)
- [Governance System](GOVERNANCE.md)
