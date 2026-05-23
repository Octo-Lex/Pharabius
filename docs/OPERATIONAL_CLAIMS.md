# Operational Claims and Gap Registry

## Purpose

Pharabius generates operational claims — explicit, evidence-backed statements about repository behavior, architecture, dependencies, and risk posture. Claims are derived from existing findings and evidence, not invented from speculation.

## Safety Boundary

> Operational claims are repository-local specification artifacts.
> They are **handoff documents**, not implementation authority.
> No production code is modified. No external APIs are called.
> Inferred claims and gaps are explicitly labeled.

## Artifact Layout

```text
.ai-debt/claims/
  operational-claims.json    # Full claims register
  operational-claims.md      # Human-readable claims summary
  confidence-report.md       # Confidence distribution and metrics
  gaps.md                    # Gap registry (blocking + non-blocking)
  questions.md               # Human-validation questions

.ai-debt/traceability/
  evidence-finding-matrix.md
  finding-claim-matrix.md
  claim-workpackage-matrix.md
```

## Claim Statuses

| Status | Meaning |
|---|---|
| `confirmed` | Direct evidence supports this claim |
| `inferred` | Evidence exists but impact is inferred |
| `gap` | No evidence available; manual validation required |

## Confidence Levels

| Level | Meaning |
|---|---|
| `High` | Direct evidence with concrete locations |
| `Medium` | Evidence exists but impact is inferred |
| `Low` | No evidence; gap requires human review |

## Confirmed vs Inferred vs Gap

- **Confirmed** claims have at least one evidence ID and no inferred business impact.
- **Inferred** claims have evidence but the business impact basis contains "inferred".
- **Gap** claims have no evidence IDs and require manual validation.

## Gap and Question Registries

Gaps are classified as:
- **Blocking**: High/Critical findings without evidence — must be resolved before safe implementation
- **Non-blocking**: Lower-priority findings without evidence — should be reviewed but don't block work

Questions are generated from claims requiring human validation, grouped by category.

## Confidence Report

The confidence report provides distribution metrics across all claims. It includes an explicit interpretation note:

> Confidence distribution is not a factual-precision measurement. It indicates traceability and uncertainty posture based on available repository evidence.

## Traceability Matrices

Three matrices link the full chain:
1. **Evidence → Finding**: Which evidence supports which findings
2. **Finding → Claim**: Which findings generated which claims
3. **Claim → Work Package**: Which claims link to which remediation work

Warnings flag: orphan evidence, findings without claims, and work packages with blocking gaps.

## Human Validation Workflow

1. Review the confidence report for high-risk gaps
2. Check blocking gaps in `gaps.md`
3. Answer questions in `questions.md`
4. Use traceability matrices to verify evidence chains
5. Never treat inferred or gap claims as confirmed without direct evidence

## What Pharabius Intentionally Does Not Do

- Does not modify production/source code
- Does not generate remediation patches
- Does not create pull requests or external issues
- Does not call external APIs
- Does not convert inferred claims into confirmed claims
- Does not hide gaps inside generic limitations
- Does not claim factual precision for confidence distributions

## Related Documentation

- [Operational Claims Adoption Guide](OPERATIONAL_CLAIMS_ADOPTION.md)
- [Portfolio Summary](PORTFOLIO.md)
- [Review Workflow](REVIEW_WORKFLOW.md)
- [Ticket Drafts](TICKET_DRAFTS.md)
