# W53-S02 — `ai-debt gate` Command

Risk: Medium  
Slice type: CLI command

## Scope

Add the `ai-debt gate` command that evaluates quality gate thresholds and exits with code 0 (pass) or 1 (fail). This is the primary CI integration point.

## Goals

- `ai-debt gate` reads debt-register.json and evaluates thresholds.
- Exits 0 on PASS, 1 on FAIL.
- Prints human-readable summary to stdout.
- Supports `--max-critical`, `--max-high`, `--max-total` CLI overrides.
- Supports `--json` for machine-readable output.
- Supports `--config` to read thresholds from config.yaml.
- Works without network access.
- Does not modify any files.

## Patch Set

```text
src/pharabius/cli.py                       # add gate command
src/pharabius/core/quality_gate.py         # evaluation logic (from S01)
tests/test_cli_gate.py                     # new
```

## CLI Interface

```bash
ai-debt gate                              # use config or defaults
ai-debt gate --max-critical 0 --max-high 5
ai-debt gate --json                       # machine-readable output
ai-debt gate --config config.yaml         # explicit config
```

## Output Examples

PASS:
```
Quality Gate: PASS
Critical: 0 (max 0) ✓
High: 3 (max 10) ✓
Total: 12 (max 50) ✓
Categories: all clear ✓
```

FAIL:
```
Quality Gate: FAIL
Critical: 2 (max 0) ✗ ← exceeded by 2
High: 8 (max 10) ✓
Total: 31 (max 50) ✓
Categories: all clear ✓
Failed rules: max_critical
```

JSON:
```json
{
  "schema_version": "1.0",
  "result": "FAIL",
  "exit_code": 1,
  "thresholds": {"max_critical": 0, "max_high": 10, "max_total": 50},
  "actual": {"critical": 2, "high": 8, "total": 31},
  "failed_rules": ["max_critical"],
  "categories": {}
}
```

## Tests

- Gate passes with zero findings.
- Gate passes with findings within thresholds.
- Gate fails when critical threshold exceeded.
- Gate fails when high threshold exceeded.
- Gate fails when total threshold exceeded.
- Exit code is 0 on pass.
- Exit code is 1 on fail.
- JSON output is valid JSON with expected fields.
- CLI flags override config thresholds.
- Missing debt-register.json produces clear error (not crash).
- Gate does not modify any files.

## Acceptance Criteria

- `ai-debt gate` command exists.
- Exit codes 0/1 work correctly.
- Human-readable and JSON output formats work.
- CLI flags override config.
- Read-only (no file mutations).
- 7 gates pass.
