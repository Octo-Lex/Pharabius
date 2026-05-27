# Pharabius v2.0 Planning Report

**Status**: Planning report — not an implementation commitment  
**Date**: 2026-05-27  
**Wave**: Wave 52 — v2.0 Strategy & Boundary Planning

## Executive Recommendation

Start v2 with a **local policy engine and human-validation workflow**. Defer external writes, dashboards, servers, remote crawling, and code-modification automation until the governance layer is proven.

## v2 Product Thesis

Pharabius v2 expands from repository-local intelligence artifacts into governed technical-debt operations, where every automated action remains evidence-backed, auditable, reversible, and human-authorized.

**Five expansion principles**:
1. Evidence remains mandatory
2. Human authorization gates every write action
3. Reversibility is required
4. Trust model is preserved
5. Additive capability — v2 extends v1, does not replace it

## What v2 May Become

| Capability | Automation Level | Integration Class |
|---|---|---|
| Local policy engine | A0-A1 | I0 |
| Human validation workflow | A0-A1 | I0 |
| Audit trails | A0 | I0 |
| Dependency suggestions | A0-A1 | I0 |
| Portfolio intelligence (SQLite) | A0-A1 | I0-I1 |
| Static HTML dashboard | A0-A1 | I0 |
| External tracker writes | A3 | I4 |
| Governed patch proposals | A4 | I0 |

## What Remains Forbidden

| Action | Status | Forever? |
|---|---|---|
| Silent code modification | **Forbidden** | Unless major redesign |
| Silent external writes | **Forbidden** | Unless major redesign |
| Autonomous remediation | **Forbidden** | Unless major redesign |
| Opaque scoring changes | **Forbidden** | Unless major redesign |
| Mandatory network access | **Forbidden** | Unless major redesign |
| Mandatory server/database | **Forbidden** | Unless major redesign |

## Automation Boundary Summary

7 levels defined (A0–A6). v1 uses A0–A1. v2.0 will use A0–A1. v2.1+ may introduce A2–A3 with required controls.

**Required controls for A3+**: preview, approval, audit log, rollback, idempotency, no hidden network, visible diff.

## External Integration Risk Posture

7 integration classes defined (I0–I6). v1 uses I0. v2.0 remains I0. External tracker writes (I4) deferred to v2.4+ after consent infrastructure exists.

## Data and Deployment Recommendation

**v2.0**: D0 (CLI-only, file-based) as baseline, with D1 (SQLite index) as primary expansion.

- `.ai-debt/` remains source of truth and portable
- SQLite is derived/rebuildable cache, not canonical
- Local-only mode always supported

## Roadmap Decision Matrix Summary

| Rank | Option | Score | Track |
|---|---|---|---|
| 1 | Human validation workflow | 65 | 🟢 Primary |
| 2 | Policy engine | 62 | 🟢 Primary |
| 3 | Audit trails | 58 | 🟢 Primary |
| 4 | SQLite index | 53 | 🟡 Secondary |
| 5 | Static dashboard | 51 | 🟡 Secondary |
| 6 | Dependency suggestions | 52 | 🟡 Secondary |
| 7 | External tracker writes | 46 | 🔴 Deferred |
| 8 | Governed patch proposals | 40 | 🔴 Deferred |
| 9 | API server/dashboard | 30 | ⛔ Rejected |
| 10 | Multi-repo crawler | 27 | ⛔ Rejected |
| 11 | Autonomous remediation | 15 | ⛔ Rejected |

## Recommended v2 Phasing

| Phase | Version | Focus | Options |
|---|---|---|---|
| **Phase 1** | v2.0 | Policy engine foundation | F1, F2, F3 |
| **Phase 2** | v2.1 | Human validation workflow | B1, B2, B3 |
| **Phase 3** | v2.2 | Audit trails and ownership | H1, H2, H3 |
| **Phase 4** | v2.3 | Portfolio intelligence | D1, D2, A3 |
| **Phase 5** | v2.4 | External tracker writes | C1 (after consent infrastructure) |

## v1 Maintenance Posture

| Aspect | Commitment |
|---|---|
| v1 bug fixes | Continue through v2 development |
| v1.x releases | Patch releases as needed |
| v1 artifact contract | Frozen per v1 Stability Contract |
| v1 command surface | Stable; no removals |
| v1 safety boundaries | Unchanged |
| v1 schema compatibility | Preserved in v2 |

## Next Wave Proposal

**Wave 53 — v2.0 Local Policy Engine Foundation**

- Custom scoring rules (F1)
- Artifact completeness policies (F2)
- Threshold-based alerts (F3)
- Local config-driven policy engine
- No external writes, no server, no network

## Planning Artifacts Produced

| Document | Slice |
|---|---|
| [V2_PRODUCT_THESIS.md](V2_PRODUCT_THESIS.md) | W52-S01 |
| [V2_OPTION_MAP.md](V2_OPTION_MAP.md) | W52-S01 |
| [V2_AUTOMATION_BOUNDARY_MODEL.md](V2_AUTOMATION_BOUNDARY_MODEL.md) | W52-S02 |
| [V2_EXTERNAL_INTEGRATION_RISK_MODEL.md](V2_EXTERNAL_INTEGRATION_RISK_MODEL.md) | W52-S03 |
| [V2_DATA_MODEL_AND_DEPLOYMENT_OPTIONS.md](V2_DATA_MODEL_AND_DEPLOYMENT_OPTIONS.md) | W52-S04 |
| [V2_ROADMAP_DECISION_MATRIX.md](V2_ROADMAP_DECISION_MATRIX.md) | W52-S05 |
| This report | W52-S06 |
