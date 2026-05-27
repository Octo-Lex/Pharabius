# Wave 49 — v1.10.1 RC Hardening & Field Validation

Goal: Validate v1.10.0 across representative repositories, fix documentation/validation gaps, and produce a field-validation evidence pack without adding new product capability.

Release target: `v1.10.1`  
Branch target: `roadmap/v1.10.1-rc-hardening`  
Boundary: Release-candidate hardening only. No new product capability, no new command surface, no external integrations, no remediation automation.

# W49-S02 — Artifact Contract Drift Checks

Risk: Medium  
Slice type: Contract validation / drift detection  
Artifact impact: Validation reports only

## Scope

Add checks that compare generated `.ai-debt/` artifacts against the documented v1 artifact contract and schema map from v1.10.0. The goal is to catch documentation drift, missing artifacts, undocumented artifacts, and schema-to-file mismatches.

This slice should not change artifact generation behavior except to expose clearer validation diagnostics.

## Goals

- Validate generated artifacts against `docs/ARTIFACT_CONTRACT.md` expectations.
- Validate schema-to-artifact mapping against `docs/SCHEMA_MAP.md` or a structured source of truth.
- Detect expected artifacts that are missing after golden-path execution.
- Detect generated artifacts not represented in the contract inventory.
- Detect schema references with no generated or documented artifact.
- Produce structured drift diagnostics.
- Keep checks deterministic and offline.

## Patch Set

Expected files/modules:

```text
src/pharabius/core/artifact_contract.py       # new or existing consolidation helper
scripts/check_artifact_contract_drift.py      # new
tests/test_artifact_contract_drift.py         # new
docs/ARTIFACT_CONTRACT.md                    # fixes only if drift found
docs/SCHEMA_MAP.md                           # fixes only if drift found
```

Recommended drift issue schema:

```python
class ArtifactContractDriftIssue(BaseModel):
    severity: Literal["error", "warning"]
    code: str
    artifact_path: str | None = None
    schema_name: str | None = None
    message: str
```

Recommended drift rules:

| Rule | Severity |
|---|---|
| Required artifact missing | Error |
| Required schema missing from schema map | Error |
| Generated artifact undocumented | Warning |
| Documented optional artifact not generated | Warning |
| Schema maps to nonexistent artifact | Error |
| Artifact listed with inconsistent category | Warning |

## Tests

Add tests for:

- Valid fixture has no drift errors.
- Missing required artifact produces error.
- Undocumented generated artifact produces warning.
- Schema map mismatch produces error.
- Optional artifact missing produces warning, not error.
- Drift output is deterministic.
- Script exits non-zero only on errors.
- Script exits zero when warnings only, if policy says warnings are non-blocking.

## Targeted Verification

```bash
pytest tests/test_artifact_contract_drift.py
python scripts/check_artifact_contract_drift.py --help
python scripts/check_artifact_contract_drift.py --ai-debt .ai-debt
```

## Expected Behavior

The drift checker reports whether generated output matches the documented v1 contract.

Example output:

```text
Artifact contract drift check complete
Errors: 0
Warnings: 2
Status: pass_with_warnings
```

## Acceptance Criteria

- Contract drift checks exist and are test-covered.
- Errors and warnings are distinguished.
- Drift checks use documented v1 contract expectations.
- Documentation fixes are limited to correcting drift.
- No artifact generation behavior is changed unless needed to restore contract consistency.
- No new product capability is introduced.
- All 7 local gates pass.
## Guardrails

- Do not add new product capability.
- Do not add new CLI commands unless required only for validation and explicitly scoped as internal/script tooling.
- Do not change risk scoring behavior.
- Do not mutate canonical artifacts during validation except by normal command execution in temporary validation workspaces.
- Do not modify production/source code in analyzed repositories.
- Do not call external APIs or remote repository services.
- Do not introduce dashboards, servers, schedulers, databases, queues, or background jobs.
- Do not create external issues, tickets, pull requests, assignments, milestones, or tracker updates.
- Do not weaken the v1 no-remediation boundary.
- Treat all outputs as repository-local validation and evidence artifacts.

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

