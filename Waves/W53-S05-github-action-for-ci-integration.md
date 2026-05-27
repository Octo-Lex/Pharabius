# W53-S05 — GitHub Action for CI Integration

Risk: Low-medium  
Slice type: CI integration artifact

## Scope

Create a reusable GitHub Action that runs Pharabius analysis and quality gate in CI. The action wraps `ai-debt run` and `ai-debt gate` for pull request and push workflows.

## Goals

- Composite GitHub Action in `action.yml`.
- Supports quality gate pass/fail (exits 1 on gate failure, blocks merge).
- Supports SARIF upload for GitHub Code Scanning.
- Supports PR comment with quality gate summary (optional).
- Zero configuration mode: works with just `uses: ./.github/actions/pharabius` or external action.
- Does not require external API keys or network access beyond checkout.

## Patch Set

```text
action.yml                                # new — GitHub Action definition
.github/workflows/pharabius-example.yml   # new — example workflow
docs/GITHUB_ACTION.md                     # new — usage documentation
tests/test_github_action_config.py        # new — validate action.yml
```

## Action Interface

```yaml
- uses: Elephant-Rock-Lab/Pharabius@v2.0.0
  with:
    command: 'gate'              # 'run', 'gate', 'run+gate'
    max-critical: '0'
    max-high: '10'
    max-total: '50'
    sarif-output: 'pharabius-results.sarif'
    fail-on-gate: 'true'
```

## Example Workflow

```yaml
name: Pharabius Debt Analysis
on: [push, pull_request]
jobs:
  debt-analysis:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - uses: actions/setup-python@v6
        with:
          python-version: '3.11'
      - uses: Elephant-Rock-Lab/Pharabius@v2.0.0
        with:
          command: 'run+gate'
          max-critical: '0'
          sarif-output: 'pharabius.sarif'
      - uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: pharabius.sarif
```

## Tests

- `action.yml` is valid YAML with required fields.
- Action inputs are documented.
- Action outputs are defined.
- Example workflow is valid YAML.
- No hardcoded secrets or credentials.
- No network dependency in action definition.

## Acceptance Criteria

- `action.yml` exists and is valid.
- Example workflow exists and is documented.
- Usage documentation exists.
- No external network dependency.
- No secrets or credentials required.
- 7 gates pass.
