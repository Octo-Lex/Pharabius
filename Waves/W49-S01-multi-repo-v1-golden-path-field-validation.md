# Wave 49 — v1.10.1 RC Hardening & Field Validation

Goal: Validate v1.10.0 across representative repositories, fix documentation/validation gaps, and produce a field-validation evidence pack without adding new product capability.

Release target: `v1.10.1`  
Branch target: `roadmap/v1.10.1-rc-hardening`  
Boundary: Release-candidate hardening only. No new product capability, no new command surface, no external integrations, no remediation automation.

# W49-S01 — Multi-Repo v1 Golden-Path Field Validation

Risk: Medium  
Slice type: Field validation / release-candidate hardening  
Artifact impact: Validation evidence only

## Scope

Validate the v1.10.0 golden path across a representative set of repositories and record results in a deterministic field-validation report. This slice should exercise the complete local command path without adding product behavior.

The purpose is to prove that the consolidated v1 contract works beyond the Pharabius repository itself.

## Goals

- Run the v1 golden path across representative repositories.
- Capture command success/failure, runtime, artifact presence, and readiness status.
- Confirm artifact generation matches the v1 contract inventory.
- Confirm existing commands remain stable.
- Record warnings and limitations per repository.
- Keep validation offline and local-only.
- Produce a reusable validation evidence structure for W49-S05.

## Representative Repository Set

Recommended minimum set:

| Repository | Purpose |
|---|---|
| Pharabius | Self-analysis, Python package, full artifact coverage |
| validation-java | Java/Maven cross-ecosystem validation |
| validation-empty | Empty/minimal edge case |
| Ghostwire | Large Node.js/TypeScript-style repository |
| Symbiot | Multi-language / mixed-stack validation |

If any repository is unavailable, substitute with a local fixture and document the substitution.

## Patch Set

Expected files/modules:

```text
scripts/validate_v1_golden_path.py           # new or enhancement of validate_golden_path.py
tests/test_v1_field_validation.py            # new
validation/field/v1.10.1/README.md           # optional generated evidence, if committed
validation/field/v1.10.1/results.json        # optional generated evidence, if committed
```

Recommended validation sequence per repo:

```bash
ai-debt init
ai-debt profile
ai-debt scan
ai-debt analyze --no-ai
ai-debt graph
ai-debt review --summary
ai-debt plan
ai-debt tickets
ai-debt export-bundles
ai-debt portfolio --repo .
python scripts/validate_repo.py .
python scripts/validate_golden_path.py .
```

If some commands require pre-existing artifacts, document preconditions and skip reasons explicitly.

Recommended result schema:

```json
{
  "schema_version": "1.0",
  "release_target": "1.10.1",
  "repositories": [
    {
      "name": "Pharabius",
      "path": "...",
      "commands_run": [],
      "commands_passed": 0,
      "commands_failed": 0,
      "artifacts_expected": 0,
      "artifacts_found": 0,
      "readiness_status": "ready | partial | needs_review",
      "warnings": [],
      "limitations": []
    }
  ]
}
```

## Tests

Add tests for:

- Validation result schema is deterministic.
- Command results are captured correctly.
- Missing repository is reported gracefully.
- Missing command artifact produces a warning, not an unhandled exception.
- Validation script supports at least one fixture repository.
- Result ordering is stable.
- No external API calls are attempted.

## Targeted Verification

```bash
pytest tests/test_v1_field_validation.py
python scripts/validate_v1_golden_path.py --help
python scripts/validate_v1_golden_path.py --repo . --output /tmp/pharabius-v1-field-validation
```

## Expected Behavior

A local validation run produces a structured result showing which repositories passed the v1 golden path and which artifacts were present or missing.

Example summary:

```text
V1 golden-path validation complete
Repositories: 5
Ready: 4
Partial: 1
Needs review: 0
Output: validation/field/v1.10.1/results.json
```

## Acceptance Criteria

- Multi-repo validation script or fixture-backed validation exists.
- Results are deterministic and machine-readable.
- Missing repositories/artifacts are handled gracefully.
- No new product capability is introduced.
- No external APIs are called.
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

