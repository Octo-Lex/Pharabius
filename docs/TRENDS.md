# Temporal Trends

Track whether technical debt is improving, stable, or worsening over time using local run history.

## Purpose

`ai-debt trend` answers the question: **"Is our technical debt getting better or worse?"**

It analyzes historical run data from `.ai-debt/runs/` and produces trend reports without requiring any infrastructure.

## Safety boundary

- Local-only: no network access, no external APIs
- Read-only with respect to `.ai-debt/runs/` (never mutates run history)
- Writes only to `.ai-debt/trends/`
- No dashboard, database, scheduler, or server

## Inputs

| Source | Path | Required |
|--------|------|----------|
| Run metadata | `.ai-debt/runs/RUN-*.json` | Yes (at least 2 for trajectory) |

## Outputs

| Artifact | Path |
|----------|------|
| Trend summary (JSON) | `.ai-debt/trends/trend-summary.json` |
| Trend summary (Markdown) | `.ai-debt/trends/trend-summary.md` |
| Risk trends | `.ai-debt/trends/risk-trends.md` |
| Category trends | `.ai-debt/trends/category-trends.md` |
| Gate trends | `.ai-debt/trends/gate-trends.md` |

## Command usage

```bash
# Basic trend analysis
ai-debt trend

# Limit to last 5 runs
ai-debt trend --last 5

# JSON output only
ai-debt trend --format json

# Markdown output only
ai-debt trend --format markdown
```

## Trend metrics

| Metric | Meaning |
|--------|---------|
| **Trajectory** | improving / stable / worsening / insufficient_data |
| **Severity deltas** | Change in critical/high/medium/low counts |
| **Gate result movement** | pass/fail pattern over time |
| **Category deltas** | Only when historical category data is available |

## Trajectory interpretation

| Trajectory | Meaning |
|------------|---------|
| `improving` | Critical+High findings decreased from baseline |
| `worsening` | Critical+High findings increased from baseline |
| `stable` | Critical+High findings unchanged |
| `insufficient_data` | Fewer than 2 valid runs available |

**Important:** Trajectory classification is heuristic, not a scientific measure of engineering quality. It reflects what Pharabius artifacts show, not the full picture of your codebase health.

## Known limitations

1. **Gate results are approximated.** Run metadata stores severity counts but not the gate result or thresholds used. Pharabius infers pass/fail from default thresholds. If you used custom thresholds, the trend may not reflect the actual gate result.

2. **Category trends require historical data.** Run metadata does not store per-run category breakdowns. Category trends show "insufficient_data" unless historical debt-register snapshots are independently archived.

3. **Readiness trends are unavailable.** Readiness status is a CLI diagnostic, not a persisted artifact. All historical readiness points show "unknown".

4. **Claims confidence trends are unavailable.** Claims are a single current snapshot, not per-run.

5. **No per-run debt-register snapshots.** Severity deltas are accurate, but detailed category breakdowns for historical runs are not available.

## CI usage

```yaml
# GitHub Actions
- run: ai-debt trend
- uses: actions/upload-artifact@v4
  with:
    name: pharabius-trends
    path: .ai-debt/trends/
```
