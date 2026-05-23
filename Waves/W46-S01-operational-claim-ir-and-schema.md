# Wave 46 — v1.9.0 Operational Claims & Gap Registry

Goal: Add first-class operational claims, gap registry, confidence reporting, and traceability matrices derived from existing Pharabius evidence, findings, work packages, and reports.

Release target: `v1.9.0`  
Branch target: `roadmap/v1.9.0-operational-claims`  
Boundary: Repository-local specification and traceability artifacts only. No code modification, no autonomous remediation, no external API writes.

# W46-S01 — Operational Claim IR and Schema

Risk: Medium  
Slice type: Schema / artifact contract  
Artifact impact: New sidecar specification artifacts only

## Scope

Introduce a first-class Operational Claim intermediate representation for Pharabius. This slice defines the schema, artifact layout, and validation rules for claims, but should not yet implement full claim extraction.

Operational claims convert existing evidence-backed findings into explicit statements about behavior, architecture, dependencies, testing, security, compliance, operations, or business rules. Each claim must carry status, confidence, traceability, and validation requirements.

## Goals

- Add `OperationalClaim` schema.
- Add `OperationalClaimsRegister` schema.
- Define supported claim types.
- Define claim status: `confirmed`, `inferred`, `gap`.
- Define confidence: `High`, `Medium`, `Low`.
- Define human-validation fields.
- Define stable artifact paths under `.ai-debt/claims/`.
- Keep claims read-only relative to existing canonical artifacts.

## Patch Set

Expected files/modules:

```text
src/pharabius/schemas/claims.py              # new
src/pharabius/core/claims.py                 # new minimal helpers/renderers
tests/test_claims_schema.py                  # new
docs/OPERATIONAL_CLAIMS.md                   # optional stub or defer to S06
```

Recommended artifact layout:

```text
.ai-debt/claims/
  operational-claims.json
  operational-claims.md
  confidence-report.md
  gaps.md
  questions.md

.ai-debt/traceability/
  evidence-finding-matrix.md
  finding-claim-matrix.md
  claim-workpackage-matrix.md
```

Recommended schema shape:

```python
class OperationalClaim(BaseModel):
    claim_id: str
    claim_type: Literal[
        "behavior", "architecture", "dependency", "test",
        "security", "compliance", "operational", "business_rule",
        "data", "documentation",
    ]
    statement: str
    status: Literal["confirmed", "inferred", "gap"]
    confidence: Literal["High", "Medium", "Low"]
    evidence_ids: list[str] = []
    linked_findings: list[str] = []
    linked_work_packages: list[str] = []
    requires_human_validation: bool = False
    validation_question: str | None = None
    source: Literal["evidence", "finding", "work_package", "report", "derived"]
    limitations: list[str] = []
```

Recommended register:

```python
class OperationalClaimsRegister(BaseModel):
    schema_version: str = "1.0"
    generated_at: str
    project_name: str | None = None
    repository: str | None = None
    branch: str | None = None
    commit: str | None = None
    claims: list[OperationalClaim]
    summary: dict[str, int]
    warnings: list[str] = []
```

Validation rules:

| Rule | Expected behavior |
|---|---|
| `confirmed` claim without evidence IDs | Reject or downgrade to `inferred` in later generator |
| `gap` claim without validation question | Reject |
| `requires_human_validation=true` without question | Reject |
| Empty statement | Reject |
| Duplicate claim IDs | Reject |
| Unsupported claim type/status | Reject |

## Tests

Add tests for:

- Valid confirmed claim with evidence IDs.
- Valid inferred claim with evidence and limitations.
- Valid gap claim with validation question.
- Confirmed claim without evidence IDs is invalid.
- Gap without validation question is invalid.
- Duplicate claim IDs rejected at register level.
- Register is JSON-serializable.
- Markdown renderer is deterministic if implemented.
- Schema uses `schema_version: "1.0"`.

## Targeted Verification

```bash
pytest tests/test_claims_schema.py
```

## Expected Behavior

After this slice, Pharabius has a stable contract for operational claims but does not yet need to generate a full claims register from repository evidence.

Example conceptual claim:

```json
{
  "claim_id": "CLM-0001",
  "claim_type": "architecture",
  "statement": "Authentication-related logic is distributed across middleware and route handlers.",
  "status": "confirmed",
  "confidence": "High",
  "evidence_ids": ["EVD-000012", "EVD-000018"],
  "linked_findings": ["TD-ARCH-001"],
  "linked_work_packages": ["WP-001"],
  "requires_human_validation": false,
  "source": "finding",
  "limitations": []
}
```

## Acceptance Criteria

- Operational claim schemas exist and are tested.
- Claim status and confidence semantics are explicit.
- Invalid claim states are rejected.
- Artifact layout is defined.
- No existing canonical artifacts are mutated.
- No scoring behavior changes.
- No external API behavior added.
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
