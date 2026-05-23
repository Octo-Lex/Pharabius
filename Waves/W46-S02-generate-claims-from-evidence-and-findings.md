# Wave 46 — v1.9.0 Operational Claims & Gap Registry

Goal: Add first-class operational claims, gap registry, confidence reporting, and traceability matrices derived from existing Pharabius evidence, findings, work packages, and reports.

Release target: `v1.9.0`  
Branch target: `roadmap/v1.9.0-operational-claims`  
Boundary: Repository-local specification and traceability artifacts only. No code modification, no autonomous remediation, no external API writes.

# W46-S02 — Generate Claims from Evidence and Findings

Risk: Medium  
Slice type: Deterministic generation / sidecar artifact  
Artifact impact: New `.ai-debt/claims/operational-claims.*` artifacts

## Scope

Implement deterministic operational claim generation from existing Pharabius evidence and debt findings. This slice should generate claims only from available repository evidence, `debt-register.json`, and optionally work-package links. It must not invent undocumented behavior or use AI-generated speculation as confirmed fact.

## Goals

- Generate `.ai-debt/claims/operational-claims.json`.
- Generate `.ai-debt/claims/operational-claims.md`.
- Convert debt findings into operational claims.
- Preserve evidence IDs and finding IDs.
- Mark claims as `confirmed`, `inferred`, or `gap`.
- Require direct evidence for `confirmed`.
- Use conservative status defaults.
- Keep deterministic ordering.

## Patch Set

Expected files/modules:

```text
src/pharabius/core/claims.py
src/pharabius/schemas/claims.py
src/pharabius/core/analyzer.py                 # only if wiring during analyze is chosen
src/pharabius/core/reporter.py                 # only if report generation is chosen
tests/test_claim_generation.py
```

Recommended generation strategy:

| Source | Claim status |
|---|---|
| Finding with evidence IDs and concrete location | `confirmed` |
| Finding with evidence IDs but inferred impact | `inferred` |
| Missing evidence, missing location, or unresolved uncertainty | `gap` |
| Work package precondition requiring validation | `gap` or `inferred` |
| Business impact basis marked inferred | `inferred` |

Recommended claim type mapping:

| Finding category | Claim type |
|---|---|
| `TD-ARCH` | `architecture` |
| `TD-DEP` | `dependency` |
| `TD-TEST` | `test` |
| `TD-SEC` | `security` |
| `TD-COMP` | `compliance` |
| `TD-OPS`, `TD-BUILD`, `TD-OBS` | `operational` |
| `TD-DATA` | `data` |
| `TD-DOC` | `documentation` |
| `TD-CODE`, `TD-PERF`, `TD-CONFIG`, `TD-PROCESS` | `behavior` or nearest fit |

Recommended deterministic ordering:

```text
status order: confirmed, inferred, gap
then claim_type asc
then linked finding ID asc
then claim_id asc
```

Recommended claim IDs:

```text
CLM-000001
CLM-000002
CLM-000003
```

## Tests

Add tests for:

- Finding with direct evidence generates confirmed claim.
- Finding with inferred business impact generates inferred claim.
- Finding without evidence generates gap claim.
- Claims preserve evidence IDs.
- Claims preserve linked finding IDs.
- Work-package links are included when available.
- Claim IDs are stable.
- Claim ordering is deterministic.
- Markdown output includes status and confidence.
- No mutation of `debt-register.json` or `evidence.json`.

## Targeted Verification

```bash
pytest tests/test_claim_generation.py
python -m pharabius.cli analyze --help
python -m pharabius.cli report --help
```

## Expected Behavior

After running the relevant command, Pharabius can emit operational claims:

```text
.ai-debt/claims/
  operational-claims.json
  operational-claims.md
```

Markdown example:

```markdown
## CLM-000001 — Architecture

- Status: confirmed
- Confidence: High
- Statement: Authentication-related logic is distributed across middleware and route handlers.
- Evidence: EVD-000012, EVD-000018
- Linked findings: TD-ARCH-001
- Human validation required: no
```

## Acceptance Criteria

- Claims are generated from existing artifacts only.
- Confirmed claims require evidence IDs.
- Inferred claims are labeled as inferred.
- Gaps are explicit and validation-oriented.
- Outputs are deterministic.
- Canonical artifacts are not mutated.
- No scoring behavior changes.
- All 7 local gates pass.

## Guardrails

- Do not modify production/source code.
- Do not generate remediation patches.
- Do not create pull requests or external issues.
- Do not call Jira, Linear, GitHub Issues, Azure DevOps, GitHub, GitLab, or other external APIs.
- Do not mutate `debt-register.json`, `evidence.json`, work packages, ticket drafts, export bundles, or portfolio outputs.
- Do not change risk scoring behavior.
- Do not let review sidecar decisions influence risk scores.
- Do not convert inferred claims into confirmed claims without direct evidence.
- Do not hide gaps inside generic limitations; gaps must remain explicit.
- Treat operational claims as handoff/specification artifacts, not implementation authority.


## Verification Commands

Run the full local gate suite:

```bash
ruff format --check .
ruff check .
mypy src
lint-imports
pytest
python -m build
python scripts/validate_repo.py .
```

Additional targeted checks for this slice are listed below.
