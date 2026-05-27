# Wave 51 — v1.11.0 Final v1 Stabilization & Declaration

Goal: Declare the v1 product line stable by freezing the v1 artifact contract, command surface, safety boundaries, and compatibility commitments, while adding only final validation, documentation, and release-declaration artifacts.

Release target: `v1.11.0`  
Branch target: `roadmap/v1.11.0-final-v1-stabilization`  
Boundary: Stabilization and declaration only. No new product capability.

# W51-S02 — Final Artifact Contract Freeze Checks

Risk: Medium  
Slice type: Validation / contract hardening  
Artifact impact: Validation scripts/checks only

## Scope

Add or harden final checks that verify the v1 artifact contract remains aligned with the documented artifact inventory and schema map.

This slice should detect drift between implementation, generated artifacts, documentation, and schema mapping. It should not introduce new artifact types unless needed only for validation reports.

## Goals

- Freeze the documented v1 artifact inventory.
- Verify required, optional, and conditional artifact semantics.
- Verify documented artifact paths still match generated paths.
- Verify schema-to-artifact mappings are complete.
- Detect undocumented generated artifacts.
- Detect documented artifacts that are no longer generated when expected.
- Support CI/local validation.

## Patch Set

Expected files/modules:

```text
src/pharabius/core/artifact_contract.py       # enhance existing if present
scripts/validate_artifact_contract.py         # new or enhance existing validation script
tests/test_artifact_contract_freeze.py        # new
docs/ARTIFACT_CONTRACT.md                     # minor updates if needed
docs/SCHEMA_MAP.md                            # minor updates if needed
```

Recommended checks:

| Check | Behavior |
|---|---|
| Required artifact missing | Error |
| Conditional artifact missing when condition is met | Error or warning depending on condition |
| Optional artifact missing | No failure |
| Generated artifact undocumented | Warning |
| Schema mapped to no artifact | Warning |
| Artifact documented with no schema where schema expected | Warning |
| Artifact path mismatch | Error |
| Duplicate artifact path | Error |

Recommended command:

```bash
python scripts/validate_artifact_contract.py
```

Optional output:

```text
Artifact contract validation: PASS
Required artifacts: 7/7
Optional artifacts checked: 17
Conditional artifacts checked: 16
Warnings: 0
```

## Tests

Add tests for:

- Required artifact missing produces error.
- Optional artifact missing does not fail.
- Conditional artifact behavior is respected.
- Undocumented artifact produces warning.
- Schema-without-artifact warning.
- Duplicate artifact path error.
- Valid fixture passes.
- Script exits 0 on valid fixture.
- Script exits non-zero on contract error.

## Targeted Verification

```bash
pytest tests/test_artifact_contract_freeze.py
python scripts/validate_artifact_contract.py
```

## Expected Behavior

The artifact contract freeze checks provide a stable regression guard for v1.x maintenance.

## Acceptance Criteria

- Artifact contract freeze checks exist.
- Checks distinguish errors from warnings.
- Required/optional/conditional semantics are test-covered.
- Documentation and implementation remain aligned.
- CI/local validation can run the check.
- No generated artifact paths are changed without explicit approval.
- No runtime product capability is added.
- All 7 local gates pass.
## Guardrails

- Do not add new product capabilities.
- Do not add new CLI commands unless strictly diagnostic and explicitly approved; this wave should prefer scripts/docs/checks over command expansion.
- Do not change the v1 artifact contract except to document and freeze it.
- Do not break existing artifact paths, schema names, or command behavior.
- Do not mutate canonical artifacts outside normal command behavior.
- Do not change risk scoring behavior.
- Do not introduce dashboard, server, scheduler, database, remote crawling, or external APIs.
- Do not create external tracker issues or write to external systems.
- Do not authorize autonomous remediation or code modification.
- Treat this wave as a stability declaration and compatibility-hardening wave.

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

