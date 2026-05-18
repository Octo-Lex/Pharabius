# Pharabius Architecture

## Architecture Style

Pharabius v1 uses a modular monolith architecture.

The system runs as a local CLI and repository analysis engine. It produces `.ai-debt/` artifacts and does not modify production code by default.

## Current Layers

```text
CLI
 ↓
Core Runtime
 ↓
Schemas / Writers
 ↓
Repository-local Output Contract
```

## Allowed Dependencies

| Layer               | May Import                                      |
| ------------------- | ----------------------------------------------- |
| `pharabius.cli`     | `pharabius.core`                                |
| `pharabius.core`    | `pharabius.schemas`, future `pharabius.writers` |
| `pharabius.writers` | `pharabius.schemas`                             |
| `pharabius.schemas` | Standard library, Pydantic                      |

## Forbidden Dependencies

| Source              | Forbidden Target |
| ------------------- | ---------------- |
| `pharabius.schemas` | `pharabius.cli`  |
| `pharabius.schemas` | `pharabius.core` |
| `pharabius.core`    | `pharabius.cli`  |
| `pharabius.writers` | `pharabius.cli`  |
| `pharabius.writers` | `pharabius.core` |

## Architectural Rule

Lower-level modules must not depend on higher-level orchestration modules.

Schemas are the most stable layer and must remain free of runtime orchestration logic.

## Drift Prevention

Architecture compliance is enforced by:

```bash
lint-imports
```

The CI pipeline must fail if forbidden imports are introduced.

---

## Analysis Unit IR

**Layer:** Between Evidence IR and Finding IR.

**Schema:** `schemas/analysis_unit.py`
**Engine:** `core/mapper.py`
**Output:** `.ai-debt/analysis-units.json`
**Command:** `ai-debt map`

Analysis Units group raw evidence into engineering-meaningful areas:
packages, services, test suites, CI workflows, infrastructure, config surfaces,
documentation areas, and security-sensitive areas.

Each unit has a stable deterministic ID (`AU-{TYPE}-{HEX8}`) enabling cross-run comparison.

### Package vs Service distinction

A directory under `services/api` with `pyproject.toml` may create both:
- **package unit** — represents the dependency/build boundary (has a manifest)
- **service unit** — represents the deployable/operational/domain boundary (lives in a service directory)

These are intentionally separate concerns:
- package = "what dependencies does this code declare?"
- service = "what deployable component does this code belong to?"

### Evidence attachment specificity

Each unit type only claims evidence matching its type allowlist:

| Unit type | Allowed evidence types |
|---|---|
| package | manifest_detected, package_script_detected |
| service | manifest_detected, package_script_detected |
| cli | package_script_detected |
| test_suite | test_file_detected |
| documentation_area | documentation_file_detected |
| config_surface | configuration_file_detected |
| security_sensitive_area | risk_sensitive_path_detected, risk_sensitive_keyword_detected |
| ci_workflow | deployment_file_detected (CI paths) |
| infra_area | infrastructure_file_detected, deployment_file_detected |

### Security-sensitive area grouping

Security evidence is grouped by the nearest meaningful parent directory:
1. Package root (directory with a manifest)
2. Service root (directory under apps/, services/, etc.)
3. Top-level source directory (src/, lib/, cmd/, etc.)
4. Root (fallback)

Risk evidence under docs/, tests/, or cache directories is excluded from
security-sensitive unit creation.

### Zero-evidence filtering

Units with zero evidence IDs are removed from output after evidence attachment.

### Verifier module

`core/verifier.py` provides `ai-debt verify`:

1. Loads existing `debt-register.json` (source findings)
2. Loads current `evidence.json`
3. Optionally loads `analysis-units.json`
4. Runs `analyze_evidence()` in memory (no disk write)
5. Matches original findings to current findings using multi-criteria matching
6. Checks evidence, unit, and location existence
7. Assigns one of 6 verification statuses
8. Verifies work package linkage
9. Writes `verification-report.json` and `verification-report.md`

Matching priority: category + evidence overlap \u2192 category + locations \u2192 category + title \u2192 finding ID (weak)

Does NOT modify `debt-register.json` or any existing artifact.

### Status reader

`core/status_reader.py` provides `ai-debt status`:

- Read-only summary of `.ai-debt/` workspace state
- Does NOT run scan/analyze/verify
- Does NOT modify files
- Tolerates missing and corrupted artifacts

### Finding lifecycle

**Artifact roles:**

- `debt-register.json` = immutable snapshot of deterministic analyzer output
- `verification-report.json` = revalidation result against current repository state
- Work packages may become stale as findings evolve

### Export layer

`core/exporter.py` provides `ai-debt export`:

- Reads `debt-register.json` (required) and optional verification/units artifacts
- Writes SARIF v2.1.0, CSV, and JSONL to `.ai-debt/exports/`
- Does not create new findings or modify source artifacts
- Enriches exports with verification status and work package linkage when available

### Architecture graph layer

`core/grapher.py` provides `ai-debt graph`:

- Reads `evidence.json` (required) and optional analysis-units, project-profile, policy
- Builds package/module and analysis-unit dependency graph
- Detects cycles via Tarjan SCC (no new dependencies)
- Checks boundary violations against optional `architecture-policy.yaml`
- Computes coupling metrics (fan-in, fan-out, instability)
- Writes `.ai-debt/architecture-graph.json`
- Does not create TD-ARCH findings, modify `debt-register.json`, or modify source artifacts
- Not part of `ai-debt run` pipeline (standalone command)
- Not exported by `ai-debt export`
- Does not parse `.importlinter`

**Finding states (current):**

- `Detected` (in `debt-register.json`)

**Verification statuses (in `verification-report.json`):**

| Status | Meaning |
|---|---|
| `still_detected` | Current analyzer confirms with supporting evidence |
| `likely_remediated` | No match, evidence gone, locations gone |
| `evidence_missing` | Evidence gone, cannot confirm remediation |
| `partially_supported` | Some evidence remains, support incomplete |
| `stale` | Structural mismatch (units, locations, or links drifted) |
| `uncertain` | Insufficient inputs for defensible result |

**Future concepts (NOT implemented):** `confirmed`, `accepted_risk`, `deferred`, `planned`, `false_positive`

**Key invariants:**

- `verify` does NOT mutate `debt-register.json`
- `verify` is NOT part of `ai-debt run`
- Verification is evidence-based, not proof of remediation

### Import contract

```
mapper imports from: schemas.analysis_unit, schemas.evidence, schemas.repository
mapper does NOT import from: analyzer, reporter, planner
```

### Pipeline order

```
init → profile → scan → map → analyze → report → plan
```
