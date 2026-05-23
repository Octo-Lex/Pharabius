# Wave 47 — v1.9.1 Operational Claims Polish & Agent-Handoff Pack

Goal: Improve operational claims usability, examples, validation, and agent-handoff readiness while preserving the no-remediation boundary.

Release target: `v1.9.1`  
Branch target: `roadmap/v1.9.1-operational-claims-polish`  
Boundary: Repository-local specification, validation, documentation, and handoff artifacts only. No code modification, no autonomous remediation, no external API writes.

# W47-S02 — Claim Quality/Completeness Checks

Risk: Medium  
Slice type: Quality scoring / completeness reporting  
Artifact impact: Claims sidecar/report only

## Scope

Add quality and completeness checks for operational claims. This slice should classify each claim and the overall claim register as `complete`, `partial`, or `needs_review` based on traceability, evidence, linkage, validation questions, and implementation-readiness constraints.

This is not risk scoring and must not modify `risk_score`, `priority`, or any canonical debt finding.

## Goals

- Add claim completeness assessment.
- Add register-level completeness summary.
- Classify claims as `complete`, `partial`, or `needs_review`.
- Identify claims that are weakly supported.
- Identify high-priority findings without confirmed claims.
- Identify work packages linked to unresolved blocking gaps.
- Include quality/completeness output in claim reports.
- Preserve explicit uncertainty.

## Patch Set

Expected files/modules:

```text
src/pharabius/schemas/claims.py
src/pharabius/core/claims.py
src/pharabius/core/claim_validation.py
tests/test_claim_completeness.py
```

Recommended schema additions:

```python
class ClaimCompleteness(BaseModel):
    claim_id: str
    status: Literal["complete", "partial", "needs_review"]
    evidence_linked: bool
    finding_linked: bool
    work_package_linked: bool
    has_validation_question: bool
    blocking_gap: bool = False
    warnings: list[str] = []

class ClaimRegisterCompleteness(BaseModel):
    total_claims: int
    complete: int
    partial: int
    needs_review: int
    claims: list[ClaimCompleteness]
    warnings: list[str] = []
```

Recommended classification:

| Condition | Status |
|---|---|
| Confirmed claim with evidence and finding linkage | `complete` |
| Inferred claim with evidence and clear limitation | `partial` |
| Gap claim with validation question | `needs_review` |
| Claim missing required linkage | `needs_review` or `partial` depending severity |
| Claim linked to blocking gap | `needs_review` |

## Tests

Add tests for:

- Confirmed evidence-linked claim is complete.
- Inferred claim with limitation is partial.
- Gap claim with question is needs_review.
- Claim with missing evidence is needs_review.
- High-priority finding without confirmed claim produces warning.
- Work package linked to blocking gap produces needs_review warning.
- Register completeness counts are correct.
- Output ordering is deterministic.
- No risk score or priority fields are modified.

## Targeted Verification

```bash
pytest tests/test_claim_completeness.py
```

## Expected Behavior

Claim outputs include a clear completeness status per claim and a summary that tells PET teams where human review is required.

Example conceptual result:

```json
{
  "claim_id": "CLM-0009",
  "status": "needs_review",
  "evidence_linked": false,
  "finding_linked": true,
  "work_package_linked": true,
  "has_validation_question": true,
  "blocking_gap": true,
  "warnings": ["Work package should not proceed until authorization behavior is validated."]
}
```

## Acceptance Criteria

- Claim completeness checks are implemented and tested.
- `complete`, `partial`, and `needs_review` semantics are clear.
- Completeness checks do not alter risk scoring.
- Blocking gaps are visible in completeness output.
- No canonical artifacts are mutated.
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

