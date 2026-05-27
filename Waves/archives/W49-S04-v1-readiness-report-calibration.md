# Wave 49 — v1.10.1 RC Hardening & Field Validation

Goal: Validate v1.10.0 across representative repositories, fix documentation/validation gaps, and produce a field-validation evidence pack without adding new product capability.

Release target: `v1.10.1`  
Branch target: `roadmap/v1.10.1-rc-hardening`  
Boundary: Release-candidate hardening only. No new product capability, no new command surface, no external integrations, no remediation automation.

# W49-S04 — v1 Readiness Report Calibration

Risk: Medium  
Slice type: Readiness logic calibration  
Artifact impact: Readiness report only

## Scope

Calibrate the v1 readiness report introduced in v1.10.0 using findings from multi-repo validation. This slice improves status classification, explanations, warnings, and recommended next steps without adding new product capability.

The readiness report must remain advisory and must not alter canonical artifacts.

## Goals

- Improve `ready`, `partial`, and `needs_review` classification accuracy.
- Add clearer reasons for readiness status.
- Distinguish blocking vs non-blocking readiness gaps.
- Include artifact contract drift results when available.
- Include golden-path validation status when available.
- Improve Markdown readability of readiness output.
- Keep readiness deterministic.

## Patch Set

Expected files/modules:

```text
src/pharabius/core/v1_readiness.py
tests/test_v1_readiness.py
tests/test_v1_readiness_calibration.py       # new, if useful
docs/ARTIFACT_CONTRACT.md                   # only if terminology needs sync
docs/QUICKSTART.md                          # only if readiness usage needs clarification
```

Recommended status rules:

| Condition | Status |
|---|---|
| Required artifacts present, schemas valid, golden path passes | ready |
| Required artifacts present but optional/adoption artifacts missing | partial |
| Required artifacts missing, malformed, or drift errors present | needs_review |
| Validation unavailable but core artifacts present | partial with warning |

Recommended readiness issue fields:

```python
class V1ReadinessIssue(BaseModel):
    severity: Literal["blocking", "non_blocking"]
    code: str
    artifact_path: str | None = None
    message: str
    recommended_action: str
```

## Tests

Add tests for:

- Ready status with complete artifact set.
- Partial status with optional artifacts missing.
- Needs-review status with required artifact missing.
- Drift error influences readiness as needs_review.
- Drift warning influences readiness as partial or warning only.
- Golden-path failure produces blocking readiness issue.
- Missing validation result produces non-blocking warning.
- Markdown includes reasons and recommended actions.
- Output is deterministic.

## Targeted Verification

```bash
pytest tests/test_v1_readiness.py tests/test_v1_readiness_calibration.py
python - <<'PY'
from pharabius.core.v1_readiness import *
print('v1 readiness import ok')
PY
```

## Expected Behavior

Readiness reports become more precise and actionable.

Example Markdown section:

```markdown
## Readiness Status: partial

### Blocking Issues
None.

### Non-Blocking Issues
| Code | Artifact | Recommended Action |
|---|---|---|
| optional_export_bundle_missing | .ai-debt/export-bundles/ | Run `ai-debt export-bundles` if tracker import preparation is needed. |
```

## Acceptance Criteria

- Readiness statuses are calibrated by validation evidence.
- Blocking and non-blocking issues are separated.
- Recommended actions are included.
- Readiness output remains advisory only.
- Canonical artifacts are not mutated.
- No scoring behavior changes.
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

