# Pharabius v2 Product Thesis

**Status**: Planning draft  
**Date**: 2026-05-27  
**Not an implementation commitment**

## Core Thesis

Pharabius v2 should expand from repository-local intelligence artifacts into governed technical-debt operations, but only where every automated action remains evidence-backed, auditable, reversible, and human-authorized.

## v1 Foundation

Pharabius v1 established:

- **Evidence-first analysis**: Every finding traces to repository evidence
- **Deterministic defaults**: All analysis rule-based; AI is opt-in sidecar
- **Repository-local output**: All artifacts written to `.ai-debt/`
- **No code modification**: Analysis and planning only, never remediation
- **No external writes**: No tracker, CI, or cloud API calls
- **Human ownership**: All outputs are recommendations for human review
- **14/14 taxonomy categories**: Complete debt category coverage
- **40 releases**: Proven delivery cadence (v0.1.0 → v1.11.0)

## v2 Expansion Principles

1. **Evidence remains mandatory**: No finding without evidence. No automation without traceability.
2. **Human authorization gates**: Every write action (file, API, patch) requires explicit human consent.
3. **Reversibility**: Automated actions must be reversible or previewable before execution.
4. **Trust model preservation**: Features that weaken the trust model (silent writes, autonomous remediation, opaque scoring) are out of scope.
5. **Additive capability**: v2 capabilities should extend v1, not replace it. v1 commands and artifacts remain stable.

## What v2 Is

- Governed operations on top of v1 intelligence artifacts
- Optional external integrations with explicit consent gates
- Structured workflows for human review, approval, and sign-off
- Optional automation where every step is auditable and reversible
- Portfolio-level intelligence across multiple repositories

## What v2 Is Not

- Autonomous code modification
- Silent external API writes
- Dashboard-only product requiring a server
- Replacement for v1 local-first analysis
- Opaque AI-driven remediation

## v2 Planning Constraints (Inherited from v1)

| Constraint | v2 Commitment |
|---|---|
| Evidence-first | Maintained. No finding without evidence. |
| Deterministic defaults | Maintained. AI remains opt-in. |
| Repository-local artifacts | Maintained as primary output. |
| No silent writes | All writes are explicit and consented. |
| Human ownership | Maintained. No autonomous decisions. |
| Schema compatibility | v1 schemas remain valid in v2. |
| Command compatibility | v1 commands remain functional in v2. |

## Decision Framework

v2 options will be evaluated against:

1. **Trust preservation**: Does it weaken evidence-traceability or human-authorization?
2. **Value density**: How much debt-reduction value per unit of risk?
3. **Reversibility**: Can the action be undone or previewed?
4. **Adoption friction**: How much new complexity for users?
5. **Maintenance cost**: How much ongoing engineering investment?

## Next Steps

This thesis informs the [v2 Option Map](V2_OPTION_MAP.md) and subsequent planning documents.
