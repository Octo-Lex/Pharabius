# Operational Claims Adoption Guide

## Who Should Use This Guide

- **Product Engineering Teams (PETs)** reviewing technical debt findings and planning remediation
- **Architects** validating architecture claims against system knowledge
- **Security reviewers** assessing gap coverage for security-sensitive code
- **AI-agent operators** using claims as context for planning or code review

## Artifact Map

| Artifact | Location | Purpose |
|---|---|---|
| Claims register | `.ai-debt/claims/operational-claims.json` | Full claims data |
| Claims summary | `.ai-debt/claims/operational-claims.md` | Human-readable claims |
| Confidence report | `.ai-debt/claims/confidence-report.md` | Distribution metrics |
| Gap registry | `.ai-debt/claims/gaps.md` | Blocking + non-blocking gaps |
| Question registry | `.ai-debt/claims/questions.md` | Human-validation questions |
| Evidence→Finding | `.ai-debt/traceability/evidence-finding-matrix.md` | Evidence chains |
| Finding→Claim | `.ai-debt/traceability/finding-claim-matrix.md` | Claim coverage |
| Claim→Work Package | `.ai-debt/traceability/claim-workpackage-matrix.md` | Implementation readiness |
| Agent-handoff contract | `.ai-debt/agent-handoff-contract.md` | Safety/review contract |

## Recommended Review Workflow

1. Open the **confidence report** for an overview
2. Review **confirmed claims** as reliable context
3. Review **inferred claims** with caution — treat as hypotheses
4. Review **blocking gaps** — these must be resolved before implementation
5. Answer **questions** in the question registry
6. Inspect **traceability matrices** for weak chains
7. Use the **agent-handoff contract** as a planning reference

## Reviewing Confirmed Claims

Confirmed claims have direct evidence backing. They represent the strongest traceability in the repository. You can use them as reliable context for planning and prioritization.

However, confirmed claims describe **current state**, not desired state. A confirmed architecture claim does not mean the architecture is good — it means the evidence supports the description.

## Reviewing Inferred Claims

Inferred claims have evidence but the business impact or operational significance is inferred rather than directly observable. These require domain expertise to validate.

**Action**: For each inferred claim, confirm with the relevant domain owner whether the inference is correct. Document the outcome.

## Reviewing Gaps and Questions

- **Blocking gaps**: High/Critical findings without evidence. These represent unknowns that could affect safety. **Do not proceed with linked work packages** until blocking gaps are resolved.
- **Non-blocking gaps**: Lower-priority findings without evidence. Review and schedule resolution.
- **Questions**: Human-validation questions requiring expert input.

## Reading Confidence Metrics

The confidence report provides distribution metrics across claims. It includes an explicit interpretation note:

> **Confidence distribution is not a factual-precision measurement.** It indicates traceability and uncertainty posture based on available repository evidence.

High confidence does not mean the claim is correct — it means the evidence chain is strong. Low confidence means the chain is weak or absent.

## Reading Traceability Matrices

Three matrices link the full audit chain:

1. **Evidence → Finding**: Which evidence supports which findings
2. **Finding → Claim**: Which findings generated which claims (with gap counts)
3. **Claim → Work Package**: Which claims link to which remediation work

Look for:
- **Warnings** in the matrices (findings without claims, blocking gaps linked to work packages)
- **Orphan evidence** not linked to any finding
- **Weak chains** where high-priority findings have only gap claims

## Using the Agent-Handoff Contract

The agent-handoff contract (`agent-handoff-contract.md`) is a safety and review artifact. It summarizes:
- What confirmed claims can be used as reliable context
- What inferred claims require caution
- What blocking gaps prevent safe implementation
- What actions are **forbidden** (including code modification)

The contract does **not** authorize code modification. It is a context document for planning.

## Product Engineering Checklist

- [ ] Confirm high-priority findings have traceable claims
- [ ] Review all blocking gaps before implementation
- [ ] Validate inferred business or security claims with domain owners
- [ ] Confirm work packages do not depend on unresolved gaps
- [ ] Use agent-handoff contract as context only, not permission to modify code
- [ ] Document resolution of each gap and question

## Security/Compliance Checklist

- [ ] All security findings (TD-SEC) have confirmed or gap claims
- [ ] Blocking gaps for security findings are escalated
- [ ] No security-sensitive changes planned without human approval
- [ ] Agent-handoff contract reviewed before any security-related work

## AI-Agent Operator Checklist

- [ ] Treat confirmed claims as context, not absolute truth
- [ ] Treat inferred claims as hypotheses requiring validation
- [ ] Stop when a blocking gap is encountered
- [ ] Ask for human validation before security, compliance, auth, data, payment, migration, or public API changes
- [ ] Do not execute code modification unless separately authorized outside Pharabius v1

## What Pharabius Intentionally Does Not Do

- Does not modify production or source code
- Does not generate remediation patches
- Does not create pull requests or external issues
- Does not call external APIs
- Does not convert inferred claims into confirmed claims
- Does not authorize autonomous remediation
- Does not claim factual precision for confidence distributions

## Related Documentation

- [Operational Claims Reference](OPERATIONAL_CLAIMS.md)
- [Portfolio Summary](PORTFOLIO.md)
- [Review Workflow](REVIEW_WORKFLOW.md)
- [Ticket Drafts](TICKET_DRAFTS.md)
