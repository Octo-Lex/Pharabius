# Coverage Ingestion

Pharabius reads existing coverage report artifacts. It does not run test suites.

## Supported formats

| Format             | File patterns                                                   | Metrics                                | Notes                                           |
|--------------------|-----------------------------------------------------------------|----------------------------------------|-------------------------------------------------|
| Istanbul JSON      | `coverage/coverage-summary.json`                                | lines, branches, functions, statements | Node.js / Jest default                          |
| Python coverage.py | `coverage.json`                                                 | lines                                  | `coverage json` command output                  |
| LCOV               | `lcov.info`, `coverage/lcov.info`                               | lines, functions                       | Multi-language; LF/LH + FNF/FNH counters       |
| Cobertura XML      | `coverage.xml`, `coverage/cobertura.xml`, `coverage/cobertura-coverage.xml`, `target/site/cobertura/coverage.xml` | lines, branches | report-level only; rates are decimals (0.82=82%) |
| JaCoCo XML         | `target/site/jacoco/jacoco.xml`, `build/reports/jacoco/test/jacocoTestReport.xml`, `jacoco.xml`, `coverage/jacoco.xml` | lines, branches, methods | report-level preferred; package-level fallback |

## Deferred formats

| Format                          | Status   | Notes                     |
|---------------------------------|----------|---------------------------|
| Cobertura package/class metrics | Deferred | Not v3.4.0                |
| JaCoCo deep class counters      | Deferred | Not v3.4.0                |
| Running test suites             | Non-goal | Pharabius reads artifacts |

## Detection

Coverage files are detected before directory exclusion filtering. This means
coverage reports in excluded directories (e.g., `coverage/`) are still found
and parsed.

Path matching uses POSIX-normalized paths (forward slashes) via `path_utils.py`.
Patterns with directory components require directory-respecting suffix matching.

## Format-specific details

### Istanbul JSON

Reads the `total` object from `coverage-summary.json`. Extracts `lines`,
`statements`, `functions`, and `branches` percentages.

### Python coverage.py

Reads `coverage.json` (output of `coverage json`). Extracts `percent_covered`
from the `totals` object. Falls back to computing `covered_lines / num_statements`
if `percent_covered` is absent.

### LCOV

Reads `LF`/`LH` counters for line coverage and `FNF`/`FNH` counters for
function coverage. Computes `LH / LF * 100` and `FNH / FNF * 100`.

### Cobertura XML

Reads `line-rate` and `branch-rate` attributes from the root `<coverage>`
element. Rates are decimals: `0.82` = 82%. Report-level only; per-package
and per-class metrics are deferred.

### JaCoCo XML

Reads `<counter>` elements with `missed` and `covered` attributes.
Formula: `covered / (covered + missed) * 100`.

**No-double-counting policy:** JaCoCo reports may contain counters at both
report level and package level. Pharabius prefers report-level counters
when present. Package-level counters are only aggregated when no report-level
counters exist. The two levels are never summed together.

## Low-coverage analyzer

When any `coverage_metric_detected` evidence has `percent` below the threshold
(default 60%), the `_analyze_coverage_gaps` analyzer produces a TD-TEST finding
with `confidence: "Medium"`.

Missing coverage reports do **not** produce findings. Only present-but-low
coverage triggers analysis.

## Malformed reports

If a coverage file cannot be parsed (invalid XML, invalid JSON, etc.),
Pharabius emits `coverage_gap_detected` evidence with `reason: malformed_report`.
This is a limitation signal, not a debt finding. The scan continues without crash.

## Configuration

| Setting                       | Default | Location        |
|-------------------------------|---------|-----------------|
| Low-coverage threshold        | 60.0%   | `constants.py`  |
| Coverage pattern registry     | 12 patterns | `constants.py` |
| Per-format parsers            | 5       | `coverage_parsers.py` |

## Non-goals

- Pharabius does not run tests
- Pharabius does not generate coverage reports
- Pharabius does not recommend specific coverage improvements
