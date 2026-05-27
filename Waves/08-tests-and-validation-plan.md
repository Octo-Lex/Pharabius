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

## Unit tests

Recommended files:

```text
tests/test_quality_gate_schema.py
tests/test_quality_gate_engine.py
tests/test_quality_gate_reports.py
tests/test_cli_quality_gate.py
tests/test_quality_gate_config.py
```

## Required schema tests

- Valid report serializes to JSON.
- Invalid result is rejected.
- Invalid mode is rejected.
- Violations preserve rule ID and severity.
- Summary fields default safely.

## Required engine tests

- Pass when thresholds are satisfied.
- Warn when warning-only rules are violated.
- Fail when max critical exceeded.
- Fail when max high exceeded.
- Fail when blocking gaps exceeded.
- Fail when required artifact missing.
- Fail when contract drift error exists.
- Fail when readiness is `needs_review`.
- Partial readiness warns by default.
- Missing optional artifacts warn by default.
- Inferred claims warn only when configured.

## Required mutation tests

Record hashes before/after gate execution for canonical inputs and assert unchanged.

## Fixture scenarios

```text
tests/fixtures/quality_gate/pass/
tests/fixtures/quality_gate/warn/
tests/fixtures/quality_gate/fail-critical/
tests/fixtures/quality_gate/fail-blocking-gaps/
tests/fixtures/quality_gate/fail-contract-drift/
tests/fixtures/quality_gate/missing-required/
tests/fixtures/quality_gate/partial-readiness/
```

## Field validation

Run against at least Pharabius self-analysis, validation-empty, validation-java, one medium repository, and one repository with claims/gaps enabled.

Capture result, exit code, violations, warnings, runtime, generated reports, and canonical hash comparison.

## Acceptance criteria

- All gate result paths are tested.
- All mode/exit-code combinations are tested.
- Canonical artifact immutability is tested.
- CI examples are validated at least syntactically.
- Full 7 local gates pass.
