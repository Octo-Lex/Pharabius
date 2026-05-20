# Sample Output — Pharabius v1.0.0

This page shows curated snippets from Pharabius v1.0.0 analyzing its own repository.
Output is illustrative — your repository will produce different findings.

> **Note:** These examples are based on Pharabius v1.0.0 self-analysis. Actual output
> depends on repository structure, languages, and evidence collected.

---

## Quick Start

```bash
# Install
pip install pharabius

# Full workflow on a repository
cd /path/to/your/repo
ai-debt init
ai-debt profile
ai-debt scan
ai-debt analyze --no-ai
ai-debt report
ai-debt plan
```

---

## Debt Register (Markdown)

`ai-debt analyze` produces `.ai-debt/debt-register.md`:

```markdown
# Technical Debt Register

## Summary

| Severity | Count |
|---|---:|
| Critical | 0 |
| High | 0 |
| Medium | 1 |
| Low | 1 |

Total findings: **2**

## Findings

### TD-DEP-001: Python dependency manifest detected without lockfile evidence

- Category: `TD-DEP`
- Severity: Medium
- Confidence: High
- Risk score: 15
- Priority: Medium
- Locations: `pyproject.toml`
- Evidence: `EVD-000104`
- Technical impact: Missing lockfile evidence may reduce dependency
  reproducibility across local, CI, and deployment environments.
- Business impact: Release and environment reproducibility risk is inferred
  from dependency manifest evidence.
- Business impact basis: Inferred from repository evidence. Validate with
  Product Engineering Team.
- Recommended action: Adopt the Python-appropriate lockfile strategy and
  document whether applications or libraries are expected to commit lockfiles.
```

### How to Read This

- **Finding ID** (`TD-DEP-001`): Stable identifier for tracking. Use in discussions and tickets.
- **Category** (`TD-DEP`): Debt taxonomy category. 14 categories in v1.
- **Severity**: Critical/High/Medium/Low — based on risk score.
- **Confidence**: High/Medium/Low — how certain the analyzer is.
- **Risk score** (0–36): Higher = more urgent. Factors include technical severity,
  dependency risk, operational exposure, and more.
- **Evidence IDs** (`EVD-000104`): Links to raw evidence in `evidence.json`.
  Every finding traces to repository evidence.
- **Business impact basis**: Always states whether impact is inferred or confirmed.
  Inferred impact should be validated with the team.

---

## Debt Register (JSON)

`ai-debt analyze` also produces `.ai-debt/debt-register.json`:

```json
{
  "id": "TD-DEP-001",
  "category": "TD-DEP",
  "title": "Python dependency manifest detected without lockfile evidence",
  "severity": "Medium",
  "confidence": "High",
  "risk_score": 15,
  "priority": "Medium",
  "locations": ["pyproject.toml"],
  "evidence_ids": ["EVD-000104"],
  "analysis_unit_ids": ["AU-PACKAGE-035BB588"],
  "technical_impact": "Missing lockfile evidence may reduce dependency reproducibility...",
  "business_impact": "Release and environment reproducibility risk...",
  "business_impact_basis": "Inferred from repository evidence. Validate with Product Engineering Team.",
  "risk_breakdown": {
    "technical_severity": 3,
    "architecture_centrality": 1,
    "blast_radius": 1,
    "change_frequency": 1,
    "test_gap": 0,
    "security_exposure": 0,
    "compliance_exposure": 0,
    "dependency_risk": 5,
    "operational_exposure": 3,
    "business_critical_proxy": 3,
    "remediation_simplicity": -2,
    "confidence_modifier": 0
  },
  "remediation_effort": "Small",
  "recommended_action": "Adopt the Python-appropriate lockfile strategy...",
  "verification_recommendations": [
    "Generate or confirm the appropriate lockfile for Python.",
    "Run dependency installation in a clean environment."
  ],
  "risks_and_cautions": [
    "Some library repositories intentionally avoid committed lockfiles."
  ],
  "suggested_owner_area": "Product Engineering / Platform"
}
```

---

## Handoff Summary

`ai-debt plan` produces `.ai-debt/handoff-summary.md` — the primary
Product Engineering Team handoff document:

```markdown
# AI Technical Debt Handoff Summary

## Executive Summary

Pharabius generated 2 deterministic technical debt finding(s) and 2 work package(s).
The top finding is TD-DEP-001 with priority Medium and risk score 15.

## Top Risks

| Priority | Debt ID | Title | Category | Score | Effort |
|---|---|---|---:|---|---|
| Medium | TD-DEP-001 | Python dependency manifest detected... | TD-DEP | 15 | Small |
| Low | TD-PROCESS-001 | Missing repository process artifacts | TD-PROCESS | 3 | Small |

## Recommended First Actions

1. Review WP-001 — Python dependency manifest detected without lockfile evidence.
```

---

## Work Package

`ai-debt plan` produces one work package per finding group in `.ai-debt/work-packages/`:

```markdown
# Work Package: WP-001 Python dependency manifest detected without lockfile evidence

## Status

Ready for Product Engineering review

## Linked Debt Items

- TD-DEP-001

## Objective

Reduce risk from TD-DEP-001 by addressing the supported technical debt without
changing production behavior beyond the approved remediation scope.

## Evidence

- EVD-000104

## Current Risk

Missing lockfile evidence may reduce dependency reproducibility across local,
CI, and deployment environments.

## Recommended Engineering Approach

1. Confirm the intended dependency-management policy for this repository.

## Verification Recommendations

- Generate or confirm the appropriate lockfile for Python.
- Run dependency installation in a clean environment.

## Risks and Cautions

- Some library repositories intentionally avoid committed lockfiles;
  validate project policy.
```

---

## Exports

### SARIF (for GitHub Code Scanning)

```json
{
  "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/main/sarif-2.1/schema/sarif-schema-2.1.0.json",
  "version": "2.1.0",
  "runs": [{
    "tool": {
      "driver": {
        "name": "Pharabius",
        "version": "1.0.0",
        "rules": [{
          "id": "TD-DEP",
          "name": "Dependency Debt"
        }]
      }
    }
  }]
}
```

Upload to GitHub: `gh code-scanning upload sarif findings.sarif`

### CSV (for spreadsheet triage)

```csv
debt_id,title,category,severity,score,confidence,locations,recommended_action
TD-DEP-001,Python dependency manifest detected...,TD-DEP,Medium,15,High,pyproject.toml,Adopt the Python-appropriate lockfile strategy...
```

### JSONL (for CI/CD gates)

```json
{"debt_id":"TD-DEP-001","category":"TD-DEP","severity":"Medium","risk_score":15,"confidence":"High","locations":["pyproject.toml"]}
```

---

## AI Sidecar (Optional)

AI enrichment is **disabled by default** and produces **sidecar output only** —
it never modifies canonical artifacts.

```bash
# Optional: enrich with mock provider (no real AI call)
ai-debt enrich --provider mock

# Optional: use a real provider (requires explicit consent)
ai-debt enrich --provider openai-compatible --allow-external-provider --model gpt-4
```

AI sidecar files are written to `.ai-debt/ai/` and include:
- `enrichment-report.json` — structured enrichment data
- `enrichment-report.md` — human-readable summary with review checklist
- `finding-enrichments.json` — per-finding enrichment records

The debt register, reports, and work packages are **never modified** by AI enrichment.

---

## 14 Taxonomy Categories

| Category | Description |
|---|---|
| TD-ARCH | Architecture dependency issues (cycles, boundary violations) |
| TD-DEP | Dependency management (missing lockfiles, version drift) |
| TD-TEST | Test coverage gaps |
| TD-SEC | Security-sensitive code without safeguards |
| TD-DOC | Missing or insufficient documentation |
| TD-BUILD | Missing or misconfigured CI/CD |
| TD-CONFIG | Configuration anti-patterns |
| TD-CODE | Code-level debt (large files, debt markers) |
| TD-COMP | Compliance keyword exposure |
| TD-OPS | Operational readiness gaps |
| TD-DATA | Data management debt (migrations, schemas) |
| TD-PERF | Performance anti-patterns |
| TD-OBS | Missing observability |
| TD-PROCESS | Missing process artifacts (CODEOWNERS, CONTRIBUTING, PR templates) |

---

## Uncertainty and Confidence Language

Pharabius uses explicit confidence and uncertainty language:

- **Confidence: High** — Directly observed in repository evidence
- **Confidence: Medium** — Inferred from indirect evidence
- **Confidence: Low** — Weak or circumstantial evidence

Business impact is always marked as "inferred" unless confirmed by the team.
Findings with Low confidence should be reviewed before acting.
