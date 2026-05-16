# Pharabius Engineering Policy

## Core Principles

### 1. Evidence Before Conclusion

Every technical debt finding must trace to repository evidence.

No finding should be emitted without an evidence ID once the scan/analyze pipeline exists.

### 2. Modular Monolith Boundaries

Pharabius must preserve clear internal boundaries between:

- CLI
- Core orchestration
- Profiling
- Scanning
- Analysis
- Reporting
- Planning
- Schemas
- Writers

### 3. No Production-Code Modification in v1

Pharabius v1 analyzes, reports, and plans.

It does not autonomously modify user repositories by default.

### 4. Deterministic First

Repository profiling, scanning, schema generation, and output writing should be deterministic where possible.

AI-assisted reasoning must be added behind explicit adapters and must preserve evidence links.

## Testing Policy

### Required Test Types

| Test Type | Purpose |
|---|---|
| Unit tests | Validate isolated functions and schemas |
| Contract tests | Validate `.ai-debt/` output shape |
| Golden-file tests | Validate generated reports remain stable |
| Architecture tests | Prevent forbidden imports |
| CLI smoke tests | Validate command behavior |

## CI Gates

The following checks must pass before merge:

```bash
ruff format --check .
ruff check .
mypy src
lint-imports
pytest
python -m build
ai-debt run
```

## Coverage Policy

Minimum coverage starts at 80%.

The threshold may increase over time but must not decrease without explicit engineering approval.

## Zero-Flakiness Policy

A flaky test is a failing test.

Any test that fails intermittently without code changes must be:

1. Fixed immediately, or
2. Quarantined with a linked issue, or
3. Removed if it does not provide meaningful confidence.

Retries must not be used to hide instability.

## Pull Request Size Policy

Pull requests should be small enough for meaningful review.

Recommended limits:

| PR Type                  |             Suggested Limit |
| ------------------------ | --------------------------: |
| Normal implementation PR |           400 changed lines |
| Refactor PR              |           600 changed lines |
| Generated/schema update  | Exempt, but must be labeled |

Oversized PRs should be split unless there is a documented reason.

## CI Feedback Policy

The default CI feedback loop should stay under 10 minutes.

If CI exceeds 10 minutes consistently, tests should be split, optimized, or parallelized.

## Metrics to Track

| Metric                  | Meaning                                  |
| ----------------------- | ---------------------------------------- |
| Architecture violations | Forbidden imports or layer bypasses      |
| Test flakiness rate     | Tests requiring reruns to pass           |
| Feedback loop duration  | Push-to-CI-completion time               |
| Core module churn       | Change frequency in foundational modules |
| Coverage trend          | Test coverage over time                  |
