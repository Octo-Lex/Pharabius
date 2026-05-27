# W53-S01 — Quality Gate Schema and Threshold Model

Risk: Medium  
Slice type: Schema + core logic

## Scope

Define the quality gate threshold schema and evaluation engine. The quality gate determines pass/fail based on configurable thresholds over analysis results.

## Goals

- Define `QualityGateThreshold` schema with configurable limits per category, severity, and count.
- Define `QualityGateResult` schema with pass/fail, triggered rules, and summary.
- Implement threshold evaluation logic in `core/quality_gate.py`.
- Thresholds stored in `config.yaml` under `quality_gate` key.
- CLI flags override config thresholds.
- Default thresholds are conservative (no findings of Critical severity, max 10 High findings).
- Quality gate reads debt-register.json — does not re-run analysis.

## Patch Set

```text
src/pharabius/schemas/quality_gate.py     # new
src/pharabius/core/quality_gate.py        # new
src/pharabius/schemas/config.py           # add QualityGateConfig
src/pharabius/core/config.py              # parse quality_gate section
tests/test_quality_gate_schema.py         # new
tests/test_quality_gate_evaluation.py     # new
```

## Threshold Model

```yaml
quality_gate:
  max_critical: 0          # fail if any Critical findings
  max_high: 10             # fail if more than 10 High findings
  max_total: 50            # fail if more than 50 total findings
  fail_on_categories: []   # fail if any finding in listed categories
  schema_version: "1.0"
```

## Evaluation Rules

| Rule | Condition | Result |
|---|---|---|
| Critical count | > max_critical | FAIL |
| High count | > max_high | FAIL |
| Total count | > max_total | FAIL |
| Category presence | any finding in fail_on_categories | FAIL |
| All checks pass | none of the above triggered | PASS |

## Tests

- Schema validates with valid thresholds.
- Schema rejects invalid threshold types (negative, non-integer).
- Evaluation returns PASS when all thresholds met.
- Evaluation returns FAIL when critical threshold exceeded.
- Evaluation returns FAIL when high threshold exceeded.
- Evaluation returns FAIL when total threshold exceeded.
- Evaluation returns FAIL on blocked categories.
- Evaluation reports which rules triggered.
- Default thresholds are used when config has no quality_gate section.
- CLI flags override config thresholds.

## Acceptance Criteria

- Quality gate schema exists with `schema_version: "1.0"`.
- Evaluation engine works on debt-register.json.
- Pass/fail is deterministic for given thresholds and findings.
- Config integration works.
- 7 gates pass.
