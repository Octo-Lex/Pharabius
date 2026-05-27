# Pharabius v2.0 — Local CI Quality Gate

Product thesis: Pharabius v2.0 enters developer workflow through a local, deterministic CI quality gate without becoming infrastructure.

Core boundary:
- No server
- No database requirement
- No dashboard service
- No remote repository crawling
- No external API writes
- No issue creation
- No autonomous remediation
- No production code modification

Primary command target:

```bash
ai-debt gate
```

Primary outputs:

```text
.ai-debt/reports/quality-gate.json
.ai-debt/reports/quality-gate.md
```

## Command

```bash
ai-debt gate
```

## Purpose

Evaluate existing Pharabius artifacts against local quality-gate rules and return a CI-compatible pass/warn/fail result.

## Recommended help text

```text
Evaluate Pharabius outputs against local quality-gate rules.

This command is local-only and read-only with respect to canonical analysis inputs.
It does not call external services, create issues, modify production code, or perform remediation.
```

## Options

```bash
ai-debt gate   --config .ai-debt/config.yaml   --output .ai-debt/reports   --mode strict   --max-critical 0   --max-high 5   --max-blocking-gaps 0   --fail-on-contract-drift   --fail-on-readiness-needs-review   --json   --markdown
```

Recommended options: `--config`, `--output`, `--mode`, `--max-critical`, `--max-high`, `--max-blocking-gaps`, `--fail-on-contract-drift`, `--no-fail-on-contract-drift`, `--fail-on-readiness-needs-review`, `--json/--no-json`, `--markdown/--no-markdown`.

## Console output

Pass:

```text
Pharabius quality gate: PASS
Critical: 0 | High: 2 | Blocking gaps: 0 | Readiness: ready
Reports written to .ai-debt/reports/
```

Fail:

```text
Pharabius quality gate: FAIL
Violations: 2
- max_critical_findings: Critical findings 1 > allowed 0
- max_blocking_gaps: Blocking gaps 2 > allowed 0
Reports written to .ai-debt/reports/
```

## Tests

- Help text includes safety boundary.
- Pass result exits 0.
- Warn result exits 0.
- Fail result exits 1 in strict mode.
- Fail result exits 0 in warn/advisory mode.
- Internal error exits 2.
- CLI overrides config.
- Output files are written.
- Canonical artifacts are not mutated.
- No external APIs are called.

## Acceptance criteria

- `ai-debt gate` is CI-ready.
- Exit codes are deterministic.
- Console output is concise and useful.
- Safety boundary is visible in help or docs.
- Reports are generated in expected locations.
