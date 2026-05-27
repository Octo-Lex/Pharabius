# Quickstart

## Install

```bash
pip install pharabius
```

Or from source:

```bash
git clone https://github.com/Elephant-Rock-Lab/Pharabius.git
cd Pharabius/pharabius
pip install -e ".[dev]"
```

## First Run

```bash
# 1. Create workspace
ai-debt init

# 2. Run full pipeline
ai-debt run

# 3. Check results
ls .ai-debt/
```

## Step-by-Step Pipeline

For more control, run each stage individually:

```bash
ai-debt init          # Create .ai-debt/ workspace
ai-debt profile       # Detect repository structure
ai-debt scan          # Collect repository evidence
ai-debt map-units     # Map analysis units
ai-debt graph         # Build dependency graph (optional)
ai-debt analyze       # Generate findings
ai-debt report        # Generate Markdown reports
ai-debt plan          # Generate remediation plan
```

## Key Output Artifacts

| Artifact | Description |
|---|---|
| `.ai-debt/evidence.json` | Normalized repository evidence |
| `.ai-debt/debt-register.json` | Deterministic debt findings |
| `.ai-debt/project-profile.json` | Repository profile |
| `.ai-debt/reports/` | Markdown analysis reports |
| `.ai-debt/work-packages/` | Remediation work packages |

## Post-Analysis Workflows

These commands require earlier pipeline steps to have completed:

```bash
ai-debt status        # View workspace summary (needs init + scan)
ai-debt verify        # Cross-check findings (needs analyze)
ai-debt review --init # Initialize PET review sidecar (needs analyze)
ai-debt tickets       # Generate ticket drafts (needs plan)
ai-debt export        # Export to SARIF/CSV/JSONL (needs analyze)
ai-debt portfolio     # Multi-repo portfolio summary (needs analyze + plan)
```

## What Pharabius Does Not Do

- Does not modify source code
- Does not generate patches or PRs
- Does not call external APIs
- Does not perform autonomous remediation
- Does not claim factual precision for confidence metrics

## Next Steps

- [CLI Reference](CLI.md)
- [Artifact Contract](ARTIFACT_CONTRACT.md)
- [Adoption Guide](ADOPTION_GUIDE.md)
- [Operational Claims](OPERATIONAL_CLAIMS.md)
