# Wave 46 — v1.9.0 Operational Claims & Gap Registry

Goal: Add first-class operational claims, gap registry, confidence reporting, and traceability matrices derived from existing Pharabius evidence, findings, work packages, and reports.

Release target: `v1.9.0`  
Branch target: `roadmap/v1.9.0-operational-claims`  
Boundary: Repository-local specification and traceability artifacts only. No code modification, no autonomous remediation, no external API writes.

# W46-S04 — Confidence Report and Claim Distribution Metrics

Risk: Medium  
Slice type: Metrics / confidence reporting  
Artifact impact: New `.ai-debt/claims/confidence-report.md`

## Scope

Add confidence reporting and claim distribution metrics for operational claims. This slice provides a quantitative and human-readable summary of confirmed, inferred, and gap claims.

The report must not imply that confidence distribution equals factual precision. It should explicitly state that human validation is still required where claims are inferred or gaps exist.

## Goals

- Generate `.ai-debt/claims/confidence-report.md`.
- Count claims by status.
- Count claims by confidence.
- Count claims by type.
- Count blocking and non-blocking gaps.
- Count claims requiring human validation.
- Count evidence-linked vs evidence-missing claims.
- Provide traceability density metrics.
- Warn when high-priority findings lack confirmed claims.

## Patch Set

Expected files/modules:

```text
src/pharabius/core/claims.py
src/pharabius/schemas/claims.py
tests/test_claim_confidence_report.py
docs/OPERATIONAL_CLAIMS.md                    # optional incremental update
```

Recommended metrics:

```python
class ClaimConfidenceSummary(BaseModel):
    total_claims: int
    confirmed_claims: int
    inferred_claims: int
    gap_claims: int
    high_confidence: int
    medium_confidence: int
    low_confidence: int
    claims_requiring_human_validation: int
    blocking_gaps: int
    non_blocking_gaps: int
    evidence_linked_claims: int
    evidence_missing_claims: int
    average_evidence_per_claim: float
```

Recommended Markdown sections:

```markdown
# Confidence Report

## Summary
## Claims by Status
## Claims by Confidence
## Claims by Type
## Human Validation Burden
## Gap Summary
## Traceability Density
## Warnings
## Interpretation Notes
```

Required interpretation note:

```text
Confidence distribution is not a factual-precision measurement. It indicates traceability and uncertainty posture based on available repository evidence.
```

## Tests

Add tests for:

- Status counts are correct.
- Confidence counts are correct.
- Claim type counts are correct.
- Human-validation count is correct.
- Blocking/non-blocking gap counts are correct.
- Evidence-linked count is correct.
- Average evidence per claim is deterministic.
- Warning emitted for high-priority finding without confirmed claim.
- Markdown includes interpretation note.
- No canonical artifact mutation.

## Targeted Verification

```bash
pytest tests/test_claim_confidence_report.py
```

## Expected Behavior

Pharabius emits a confidence report:

```text
.ai-debt/claims/confidence-report.md
```

Example summary:

```markdown
## Summary

| Metric | Count |
|---|---:|
| Total claims | 42 |
| Confirmed | 30 |
| Inferred | 9 |
| Gaps | 3 |
| Requires human validation | 7 |
```

## Acceptance Criteria

- Confidence report is generated.
- Metrics are deterministic and test-covered.
- Report distinguishes confidence from factual precision.
- Human-validation burden is visible.
- Warnings identify weak traceability.
- No canonical artifacts are mutated.
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
