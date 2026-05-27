# Pharabius GitHub Action

Use Pharabius in your CI/CD pipeline to run technical debt analysis and enforce quality gates.

## Quick Start

```yaml
jobs:
  debt-analysis:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - uses: actions/setup-python@v6
        with:
          python-version: "3.11"
      - uses: Elephant-Rock-Lab/Pharabius@v2.0.0
        with:
          command: run+gate
          max-critical: "0"
```

## Inputs

| Input | Default | Description |
|-------|---------|-------------|
| `command` | `gate` | Command to run: `gate`, `run`, or `run+gate` |
| `max-critical` | `0` | Max allowed Critical findings |
| `max-high` | `10` | Max allowed High findings |
| `max-total` | `50` | Max allowed total findings |
| `fail-on-gate` | `true` | Fail workflow if gate fails |
| `sarif-output` | `pharabius.sarif` | SARIF output path (empty disables) |

## Commands

### `gate` (default)
Runs the quality gate against an existing `.ai-debt/debt-register.json`. Use when analysis was run in a previous step.

### `run`
Runs the full analysis pipeline: `init → profile → scan → map-units → analyze → report → plan`.

### `run+gate`
Runs analysis followed by quality gate. Most common for CI pipelines.

## GitHub Code Scanning

Upload SARIF results to GitHub Security tab:

```yaml
- uses: Elephant-Rock-Lab/Pharabius@v2.0.0
  with:
    command: run+gate
    sarif-output: pharabius.sarif

- uses: github/codeql-action/upload-sarif@v3
  if: always()
  with:
    sarif_file: pharabius.sarif
```

Requires `permissions: security-events: write`.

## No External Dependencies

The action requires no API keys, credentials, or external network access. All analysis is local and deterministic.
