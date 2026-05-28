# GitHub Actions

Run Pharabius quality gate in GitHub Actions CI.

## Minimal Example

```yaml
name: Debt Analysis
on: [push, pull_request]

jobs:
  quality-gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - uses: actions/setup-python@v6
        with:
          python-version: "3.11"
      - run: pip install pharabius
      - run: |
          if [ ! -d .ai-debt ]; then ai-debt init; fi
          ai-debt run
      - run: ai-debt gate --max-critical 0 --max-high 10 --max-total 50
```

## Full Pipeline with SARIF

Generate SARIF for local inspection. Upload to GitHub Code Scanning is **opt-in** — add the upload step only if you want it.

```yaml
name: Debt Analysis
on: [push, pull_request]

jobs:
  quality-gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - uses: actions/setup-python@v6
        with:
          python-version: "3.11"
      - run: pip install pharabius
      - run: |
          if [ ! -d .ai-debt ]; then ai-debt init; fi
          ai-debt run
      - run: ai-debt gate --max-critical 0 --max-high 10
      - run: ai-debt export --format sarif --output-dir sarif-output
        if: always()
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: pharabius-sarif
          path: sarif-output/

      # Optional: Uncomment to upload to GitHub Code Scanning
      # - uses: github/codeql-action/upload-sarif@v3
      #   if: always()
      #   with:
      #     sarif_file: sarif-output/findings.sarif
```

## Safety Notes

- No tokens or credentials required.
- All analysis is local and deterministic.
- SARIF upload to GitHub Code Scanning is commented out by default.
- Quality gate exit code (0/1) determines job pass/fail.
