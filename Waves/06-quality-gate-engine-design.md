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

## Engine responsibility

The quality gate engine evaluates existing Pharabius outputs against configured rules.

It must not perform analysis, scoring, remediation, export, tracker writes, or dashboard generation.

## Recommended modules

```text
src/pharabius/schemas/quality_gate.py
src/pharabius/core/quality_gate.py
tests/test_quality_gate.py
tests/test_cli_quality_gate.py
```

## Core functions

```python
load_quality_gate_config(path: Path) -> QualityGateConfig
collect_quality_gate_inputs(repo_root: Path) -> QualityGateContext
evaluate_quality_gate(context: QualityGateContext, config: QualityGateConfig) -> QualityGateReport
render_quality_gate_markdown(report: QualityGateReport) -> str
write_quality_gate_reports(report: QualityGateReport, output_dir: Path) -> list[Path]
```

## Input collectors

| Collector | Artifact |
|---|---|
| Debt register collector | `.ai-debt/debt-register.json` |
| Claims collector | `.ai-debt/claims/operational-claims.json` |
| Gap collector | `.ai-debt/claims/gaps.md` or structured claims |
| Readiness collector | v1 readiness output or direct evaluation |
| Contract drift collector | artifact contract check |
| Metadata collector | branch, commit, project name |

## Determinism rules

- Sort rule results by rule ID.
- Sort violations by severity, rule ID, artifact path.
- Sort recommended actions by rule ID.
- Use stable priority ordering: Critical, High, Medium, Low.
- Do not include nondeterministic paths beyond repo-relative paths.
- Generated timestamps are allowed but should be isolated to metadata fields.

## Mutation rules

The gate may write only:

```text
.ai-debt/reports/quality-gate.json
.ai-debt/reports/quality-gate.md
```

The gate must not modify canonical Pharabius inputs such as `debt-register.json`, `evidence.json`, claims, work packages, ticket drafts, export bundles, or portfolio outputs.

## Acceptance criteria

- Engine is deterministic.
- Engine is local-only.
- Engine is read-only except report outputs.
- Engine composes existing v1 readiness and artifact contract logic where possible.
- Tests prove no canonical input mutation.
