# Quality Gate

The `ai-debt gate` command evaluates your technical debt against configurable thresholds and produces a pass/fail result suitable for CI pipelines.

## Usage

```bash
# Basic gate check (uses default thresholds)
ai-debt gate

# Custom thresholds
ai-debt gate --max-critical 0 --max-high 5 --max-total 30

# JSON output for machine processing
ai-debt gate --json
```

## Thresholds

| Threshold | Default | Description |
|-----------|---------|-------------|
| `max-critical` | 0 | Maximum allowed Critical findings |
| `max-high` | 10 | Maximum allowed High findings |
| `max-total` | 50 | Maximum allowed total findings |

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Quality gate passed |
| 1 | Quality gate failed |

## Gate Rules

1. **max_critical**: Number of Critical findings must not exceed threshold.
2. **max_high**: Number of High findings must not exceed threshold.
3. **max_total**: Total findings must not exceed threshold.
4. **fail_on_categories**: No findings in blocked categories (configurable).

## CI Integration

The gate is designed for CI pipelines. Exit code 0/1 determines pass/fail.

```yaml
# GitHub Actions
- run: ai-debt gate --max-critical 0 --max-high 10
```

See [CI Examples](ci/github-actions.md) for full pipeline configurations.

## Report

The quality gate produces a Markdown report at `.ai-debt/reports/quality-gate.md` when run as part of `ai-debt run`.

## Safety

- Read-only: does not modify any files.
- Local-only: no network access, no API calls.
- Deterministic: same input always produces same result.
