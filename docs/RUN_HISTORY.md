# Run History Intelligence

## What run history is

Run History Intelligence (v3.5.0) turns repeated Pharabius audit runs into temporal engineering intelligence. Instead of each run being an isolated snapshot, Pharabius now tracks how findings, risk, evidence coverage, work-package readiness, and traceability quality change over time.

## Where artifacts live

```
.ai-debt/runs/RUN-YYYYMMDD-HHMMSS.json                    Run metadata (existing)
.ai-debt/runs/RUN-YYYYMMDD-HHMMSS-history-snapshot.json    Enriched per-run snapshot (NEW)
.ai-debt/runs/run-history-index.json                        Queryable index (NEW)
.ai-debt/reports/run-history-summary.json                   Trend summary (NEW)
.ai-debt/reports/run-history-summary.md                     Reviewer-facing report (NEW)
```

## How enriched snapshots work

Each run now writes a **history snapshot** alongside its metadata. This snapshot captures the full analytical state at run time:

- Finding counts by category (TD-CODE, TD-DEP, TD-TEST, etc.)
- Risk scores by category (total, average, max)
- Evidence type counts and observation strength breakdown
- Work-package readiness metrics
- Traceability quality grade
- Claim counts and owner area distribution

**Why this matters:** `debt-register.json` and `evidence.json` are overwritten each run. Without snapshots, historical trend analysis would be permanently limited to basic counts. Snapshots preserve the detail needed for meaningful historical comparison.

## How trend status is determined

Every trend section has a `status` field:

| Status | Meaning |
|--------|---------|
| `complete` | Both compared runs have enriched snapshots. Full category/risk breakdown available. |
| `partial` | Only the latest run has enriched data. Total deltas shown, but category/risk breakdown is unavailable. |
| `insufficient_data` | Fewer than 2 runs exist. No comparison possible. |

## How to interpret trend outputs

### Overall trajectory

The overall trajectory is conservative and heuristic (not a scientific measure):

- **worsening** if broken references increased, total risk increased ≥ 5 points, or evidence-with-findings percentage dropped ≥ 5pp
- **improving** if total risk decreased ≥ 5 points, broken references did not increase, and evidence-with-findings percentage is stable or better
- **stable** if no meaningful movement
- **insufficient_data** if fewer than 2 enriched runs

### Confidence level

| Level | Meaning |
|-------|---------|
| `complete` | At least 2 enriched snapshots available |
| `partial` | At least 2 runs but fewer than 2 enriched snapshots |
| `insufficient` | Fewer than 2 runs total |

When confidence is `partial`, the Markdown report prefixes the trajectory with "Preliminary:".

### Finding trend vs risk trend

Finding count alone is a weak signal. A run with fewer but more severe findings may be worse. The risk trend addresses this by tracking `total_risk_score`, `average_risk_score`, and `max_risk_score`.

### Limitation evidence trends

Limitation evidence (`observation_strength: "limitation"`) indicates scanner constraints, not necessarily repository problems. A rise in limitation evidence may mean:

1. The scanner is more honest (detecting more constraints)
2. New coverage parsers or dependency parsers were added
3. The repository genuinely has more unparseable artifacts

**Do not treat rising limitation evidence as automatically negative.** Correlate with coverage metric trends and source-file skipped counts.

## How finding trends differ from risk trends

- **Finding trend** counts how many findings exist per category
- **Risk trend** sums `risk_score` per category and tracks severity-weighted movement

A category can have the same finding count but a different total risk if individual finding severities changed.

## Known limitations

1. **Pre-v3.5.0 runs have no enriched snapshots** — trend comparisons involving these runs will be `partial`. This is permanent for historical data.
2. **Trend accuracy improves over time** — the more enriched snapshots accumulate, the more reliable trends become.
3. **Overall trajectory is heuristic** — it uses fixed thresholds (5 points for risk, 5pp for evidence percentage) which may not suit all repositories.
4. **Owner areas depend on finding quality** — empty `suggested_owner_area` fields produce empty owner area lists.
5. **Work-package readiness is heuristic** — WP metrics are parsed from Markdown files and may be approximate.
