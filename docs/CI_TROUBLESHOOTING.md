# CI Troubleshooting Guide

Common issues when running Pharabius in CI and how to resolve them safely.

## Quality Gate Failed

**Symptom:** `ai-debt gate` exits with code 1.

**What it means:** Your repository has findings that exceed configured thresholds.

**How to diagnose:**

```bash
# See what the gate found
ai-debt gate --json

# Get detailed finding descriptions
ai-debt report

# Check workspace health
ai-debt doctor
```

**How to fix:**

1. Review the blocking violations in the gate output.
2. Run `ai-debt report` for detailed finding descriptions.
3. Run `ai-debt plan` for remediation work packages.
4. After addressing debt, re-run: `ai-debt run && ai-debt gate`.

**Do not:** Disable the gate, set thresholds to unlimited, or skip analysis. These weaken your quality feedback.

## Quality Gate Warned

**Symptom:** `ai-debt gate` exits with code 0 but shows warnings.

**What it means:** Thresholds are approaching limits. This is advisory only in `warn` or `advisory` mode.

**How to fix:** Same as above, but not blocking. Address findings before the next threshold breach.

## Missing Required Artifacts

**Symptom:** `FileNotFoundError: debt-register.json not found`.

**What it means:** The analysis pipeline has not been run.

**How to fix:**

```bash
# Initialize workspace
ai-debt init

# Run full analysis
ai-debt run

# Now the gate works
ai-debt gate
```

## Missing Optional Artifacts

**Symptom:** `ai-debt doctor` reports missing optional artifacts.

**What it means:** Some commands have not been run yet. This is normal for new workspaces.

**How to fix:** Run the commands recommended by `ai-debt doctor`.

```bash
ai-debt doctor  # Shows what's missing and what to run next
```

## SARIF File Not Found

**Symptom:** CI upload step cannot find the SARIF file.

**What it means:** SARIF was not generated, or the output path is wrong.

**How to fix:**

```bash
# Generate SARIF explicitly
ai-debt export --format sarif --output-dir sarif-output

# Verify it exists
ls sarif-output/findings.sarif
```

**Note:** SARIF upload to GitHub Code Scanning is a separate user-configured step. Pharabius does not upload SARIF by default.

## GitHub Action Failed

**Symptom:** The Pharabius GitHub Action step fails.

**Common causes:**

1. **Missing debt-register.json** — The action needs an existing analysis. Use `command: run+gate`.
2. **Python version** — Ensure `actions/setup-python@v6` is configured with Python 3.11+.
3. **Install failure** — Check that `pip install pharabius` succeeds.

**Debug:**

```yaml
- name: Debug Pharabius
  run: |
    ai-debt --version
    ai-debt doctor
    ls -la .ai-debt/
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Command succeeded / gate passed |
| 1 | Command failed / gate failed |
| 2 | Usage error (invalid arguments) |

## Safe Recovery Commands

These commands regenerate artifacts without modifying source code:

```bash
ai-debt doctor          # Diagnose workspace health
ai-debt init            # Initialize .ai-debt workspace
ai-debt profile         # Profile repository
ai-debt scan            # Scan for evidence
ai-debt map-units       # Map analysis units
ai-debt analyze --no-ai # Analyze findings (deterministic)
ai-debt report          # Generate reports
ai-debt plan            # Generate work packages
ai-debt run             # Full pipeline
ai-debt gate            # Quality gate check
```

## What Pharabius Will Not Do

- **Does not modify source code** — All outputs are analysis artifacts in `.ai-debt/`.
- **Does not upload SARIF by default** — Local generation only. Upload is your CI configuration.
- **Does not post PR comments** — No GitHub Checks API integration.
- **Does not create issues** — No tracker API writes.
- **Does not require credentials** — No tokens, keys, or secrets needed.
- **Does not perform autonomous remediation** — Analysis and planning only.

If a recovery command suggests modifying safety boundaries, that is a bug. Please report it.
