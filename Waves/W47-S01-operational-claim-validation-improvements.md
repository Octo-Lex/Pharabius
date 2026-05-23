# Wave 47 — v1.9.1 Operational Claims Polish & Agent-Handoff Pack

Goal: Improve operational claims usability, examples, validation, and agent-handoff readiness while preserving the no-remediation boundary.

Release target: `v1.9.1`  
Branch target: `roadmap/v1.9.1-operational-claims-polish`  
Boundary: Repository-local specification, validation, documentation, and handoff artifacts only. No code modification, no autonomous remediation, no external API writes.

# W47-S01 — Operational Claim Validation Improvements

Risk: Medium  
Slice type: Validation hardening  
Artifact impact: Claims sidecar validation only

## Scope

Strengthen validation for operational claims and claim registers introduced in v1.9.0. This slice should detect malformed claims, weak traceability, invalid status/confidence combinations, duplicate IDs, and unsafe claim semantics.

This is a polish and hardening slice. It should not change the core meaning of claims or introduce new claim-generation behavior beyond validation corrections.

## Goals

- Add structured validation result objects for claim registers.
- Detect invalid claim status/confidence combinations.
- Detect confirmed claims without evidence.
- Detect gap claims without validation questions.
- Detect inferred claims missing limitations or basis text when applicable.
- Detect duplicate claim IDs.
- Detect claim references to missing findings, evidence IDs, or work packages when source artifacts are available.
- Distinguish validation errors from warnings.
- Keep generation graceful: warnings should not crash safe artifact generation.

## Patch Set

Expected files/modules:

```text
src/pharabius/schemas/claims.py
src/pharabius/core/claims.py
src/pharabius/core/claim_validation.py          # new, if useful
tests/test_claim_validation.py                 # new
```

Recommended schema additions:

```python
class ClaimValidationIssue(BaseModel):
    severity: Literal["error", "warning"]
    code: str
    message: str
    claim_id: str | None = None
    referenced_id: str | None = None
    field: str | None = None

class ClaimValidationResult(BaseModel):
    valid: bool
    errors: list[ClaimValidationIssue] = []
    warnings: list[ClaimValidationIssue] = []
```

Recommended validation rules:

| Rule | Severity |
|---|---|
| Duplicate claim ID | Error |
| Empty claim statement | Error |
| Unsupported claim type/status/confidence | Error |
| `confirmed` claim without evidence IDs | Error |
| `gap` claim without validation question | Error |
| `requires_human_validation=true` without validation question | Error |
| Linked finding ID missing from debt register | Warning |
| Evidence ID missing from evidence store | Warning |
| Work package ID missing from work-package directory | Warning |
| Inferred claim without limitation/basis | Warning |
| High-priority finding linked only to inferred/gap claims | Warning |

## Tests

Add tests for:

- Valid claim register passes validation.
- Duplicate claim IDs fail validation.
- Confirmed claim without evidence fails validation.
- Gap claim without validation question fails validation.
- Human-validation claim without question fails validation.
- Missing linked finding produces warning.
- Missing evidence ID produces warning.
- Missing work-package ID produces warning.
- Inferred claim without limitation produces warning.
- Validation result is deterministic.
- No canonical artifact mutation occurs.

## Targeted Verification

```bash
pytest tests/test_claim_validation.py
```

## Expected Behavior

Claim validation produces a structured result that can be rendered in reports and used by later slices.

Example conceptual output:

```json
{
  "valid": false,
  "errors": [
    {
      "severity": "error",
      "code": "confirmed_claim_missing_evidence",
      "message": "Confirmed claims must include at least one evidence ID.",
      "claim_id": "CLM-0007",
      "field": "evidence_ids"
    }
  ],
  "warnings": []
}
```

## Acceptance Criteria

- Claim validation exists and is covered by tests.
- Errors and warnings are separated.
- Confirmed/inferred/gap semantics are protected.
- Validation is deterministic.
- No canonical artifacts are mutated.
- No scoring behavior changes.
- No external API behavior is introduced.
- All 7 local gates pass.
## Guardrails

- Do not modify production/source code.
- Do not generate remediation patches.
- Do not create pull requests or external issues.
- Do not call Jira, Linear, GitHub Issues, Azure DevOps, GitHub, GitLab, or other external APIs.
- Do not mutate `debt-register.json`, `evidence.json`, work packages, ticket drafts, export bundles, portfolio outputs, or existing claim registers except when explicitly regenerating claims artifacts.
- Do not change risk scoring behavior.
- Do not let review sidecar decisions influence risk scores.
- Do not convert inferred claims into confirmed claims without direct evidence.
- Do not let the agent-handoff contract authorize code modification.
- Treat the agent-handoff contract as a safety and review artifact, not an execution mandate.

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

