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
      - uses: Elephant-Rock-Lab/Pharabius@v2.0.1
        with:
          command: run+gate
          max-critical: "0"
```

## Inputs

| Input | Default | Description |
|-------|---------|-------------|
| `command` | `gate` | Command to run: `gate`, `run`, or `run+gate` |
| `mode` | `strict` | Gate mode: `strict`, `warn`, or `advisory` |
| `max-critical` | `0` | Max allowed Critical findings |
| `max-high` | `10` | Max allowed High findings |
| `max-total` | `50` | Max allowed total findings |
| `fail-on-gate` | `true` | Fail workflow if gate fails (strict mode) |
| `generate-sarif` | `false` | Generate local SARIF artifact file |
| `output-dir` | `.ai-debt/reports` | Directory for generated reports |

## Gate Modes

### Strict (default)
Fails the workflow when thresholds are exceeded. Use for merge-blocking quality gates.

```yaml
- uses: Elephant-Rock-Lab/Pharabius@v2.0.1
  with:
    command: run+gate
    mode: strict
    max-critical: "0"
```

### Warn
Annotates the workflow run but does not fail. Use for non-blocking visibility.

```yaml
- uses: Elephant-Rock-Lab/Pharabius@v2.0.1
  with:
    command: run+gate
    mode: warn
    max-critical: "0"
```

### Advisory
Reports results only. No workflow annotations. Use for informational runs.

```yaml
- uses: Elephant-Rock-Lab/Pharabius@v2.0.1
  with:
    command: run+gate
    mode: advisory
```

## SARIF Generation

The action can generate a local SARIF file. **This does not upload anywhere.**

```yaml
- uses: Elephant-Rock-Lab/Pharabius@v2.0.1
  with:
    command: run+gate
    generate-sarif: "true"
```

To upload SARIF to GitHub Code Scanning, add your own upload step:

```yaml
- uses: Elephant-Rock-Lab/Pharabius@v2.0.1
  with:
    command: run+gate
    generate-sarif: "true"

- uses: actions/upload-artifact@v4
  with:
    name: pharabius-sarif
    path: .ai-debt/reports/findings.sarif

# Optional: upload to GitHub Code Scanning (requires security-events: write permission)
# - uses: github/codeql-action/upload-sarif@v3
#   with:
#     sarif_file: .ai-debt/reports/findings.sarif
```

## Safety

This action is **local-only by design**:

- No GitHub token required
- No external network calls beyond package installation
- No PR comments or issue creation
- No SARIF upload by default
- No tracker API writes
- No autonomous remediation
- No source code modification

SARIF upload to GitHub Code Scanning is a separate user-owned step, not part of this action.
