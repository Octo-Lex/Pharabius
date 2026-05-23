# Portfolio Summary

## Purpose

Pharabius can consolidate technical debt data from one or more analyzed repositories into a single portfolio view. Portfolio summaries are **repository-local file-based artifacts** — no server, dashboard, or database is involved.

## Safety Boundary

> Portfolio summaries are read-only rollups over existing `.ai-debt/` artifacts.
> No external APIs are called. No remote repositories are crawled.
> No debt registers or work packages are mutated.

## Artifact Layout

```text
.ai-debt/portfolio/
  portfolio-summary.json    # Full portfolio data
  portfolio-summary.md      # Human-readable summary
  repository-index.json     # Lightweight repo index
  validation-rollup.md      # Readiness and validation report
```

## Generating a Portfolio Summary

```bash
# Single repository (default: current directory)
ai-debt portfolio

# Multiple repositories
ai-debt portfolio --repo ../service-a --repo ../service-b

# Custom output directory
ai-debt portfolio --repo ../service-a --output ./my-portfolio
```

## Single-Repository Mode

When run without `--repo`, Pharabius uses the current directory. The portfolio summarizes the local `.ai-debt/` outputs.

## Multi-Repository Mode

Pass multiple `--repo` paths to aggregate across repositories:

```bash
ai-debt portfolio --repo ../backend --repo ../frontend --repo ../infra
```

Each repository must have a valid `.ai-debt/debt-register.json`. Repositories without `.ai-debt/` are skipped with a warning.

## Reading Portfolio Risk Rollups

The `portfolio-summary.json` contains:

| Field | Description |
|---|---|
| `risk_rollup.priority_counts` | Aggregate priority counts (Critical, High, Medium, Low) |
| `risk_rollup.highest_priority` | Highest priority with findings |
| `category_rollup.category_counts` | Aggregate TD category counts |
| `category_rollup.top_categories` | Categories sorted by frequency |

## Reading Readiness Rollups

The `validation-rollup.md` shows:

| Field | Description |
|---|---|
| `total_repositories` | Number of repos in portfolio |
| `with_ticket_drafts` | Repos with ticket draft artifacts |
| `with_export_bundles` | Repos with export bundle artifacts |
| `status_counts` | Validation status distribution |
| `repositories_needing_review` | Repos with needs_review or unknown status |

## Known Limitations

- Portfolio summaries are point-in-time snapshots. Re-run after new analysis.
- Category counts are derived from `top_categories` in each repository entry.
- No remote repository crawling or GitHub/GitLab organization scanning.
- No automatic scheduling or CI integration for portfolio generation.
- Portfolio does not recalculate risk scores.

## What Pharabius Intentionally Does Not Do

- Does not add a web dashboard or server
- Does not crawl remote repositories or organizations
- Does not call GitHub, GitLab, Bitbucket, or other external APIs
- Does not modify source debt registers or work packages
- Does not change risk scoring behavior
- Does not generate autonomous remediation or code patches

## Related Documentation

- [Tracker Export Workflow](TRACKER_EXPORT_WORKFLOW.md)
- [Ticket Drafts](TICKET_DRAFTS.md)
- [Export Bundles](EXPORT_BUNDLES.md)
