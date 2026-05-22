# Ticket Draft Export

## Purpose

Pharabius generates repository-local ticket drafts from work packages and linked debt findings. These drafts are designed for Product Engineering Teams to review before manually creating tickets in their chosen issue tracker.

## Safety model

- **Local files only** — all output stays under `.ai-debt/`
- **No external tickets created** — zero API calls to Jira, Linear, GitHub Issues, or Azure DevOps
- **No assignment or sprint planning** — teams own prioritization
- **No remediation or code modification** — analysis only

## Command

```bash
ai-debt tickets              # Generate drafts (excludes deferred/rejected by default)
ai-debt tickets --include-deferred  # Include deferred work packages
ai-debt tickets --force      # Overwrite existing generated drafts
```

## Prerequisites

```bash
ai-debt init                 # Initialize workspace
ai-debt run                  # Run analysis pipeline
ai-debt plan                 # Generate work packages (required)
ai-debt review --init        # Optional: initialize review sidecar for filtering
```

## Output files

| File | Purpose |
|---|---|
| `.ai-debt/ticket-drafts/TICKET-WP-001.md` | Human-readable ticket draft per work package |
| `.ai-debt/ticket-drafts/ticket-drafts.json` | Machine-readable index with metadata |
| `.ai-debt/reports/ticket-draft-summary.md` | Summary report for reviewers |

## PET review sidecar behavior

Ticket drafts respect review sidecar decisions:

| Review decision | Default behavior |
|---|---|
| `accepted` | Included |
| `needs-investigation` | Included |
| `not_reviewed` / no sidecar | Included |
| `deferred` | Excluded (use `--include-deferred`) |
| `rejected` | Excluded |
| `duplicate` | Excluded |
| `already-fixed` | Excluded |
| `risk-accepted` | Excluded |

Review decisions affect ticket draft inclusion only, **not** risk scores or canonical findings.

## Deferred work

Deferred-only work packages are excluded by default because they represent intentionally postponed work. Use `--include-deferred` to include them in the output.

## Copy-paste workflow

1. Run `ai-debt tickets`
2. Review generated `.md` files in `.ai-debt/ticket-drafts/`
3. Copy relevant content into your team's issue tracker
4. Adjust priority, assignee, sprint, and labels as needed

## Known limitations

- Ticket drafts are local files only — no external tracker writes
- Markdown work package parsing is conservative — missing sections use placeholders
- Content should be reviewed by PETs before creating real tickets
- `finding` source type is reserved for future use — v1.6.0 generates from work packages only
