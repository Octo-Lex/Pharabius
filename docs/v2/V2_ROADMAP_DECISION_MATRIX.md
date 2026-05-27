# Pharabius v2 Roadmap Decision Matrix

**Status**: Planning draft  
**Date**: 2026-05-27  
**Not an implementation commitment**

This document scores v2 expansion options against consistent criteria to produce a recommended primary track.

## Evaluation Criteria

| Criterion | Weight | Description |
|---|---|---|
| PET value | 2× | Direct value to Product Engineering Teams |
| Enterprise value | 1× | Value to managers, architects, platform/security teams |
| Trust-model fit | 2× | Preserves evidence, traceability, human control |
| Safety risk | 2× (inverse) | Risk of unintended external/code changes (lower = better) |
| Implementation complexity | 1× (inverse) | Engineering effort (lower = better) |
| Maintenance burden | 1× (inverse) | Long-term support cost (lower = better) |
| Adoption acceleration | 1× | Helps teams adopt Pharabius faster |
| v1 continuity | 1× | Builds on existing v1 artifacts cleanly |
| Differentiation | 1× | Strengthens unique market position |

**Scale**: 1–5 (5 = highest value / lowest risk)

## Option Scores

| Option | PET Value | Ent. Value | Trust Fit | Safety | Complexity | Maintenance | Adoption | v1 Cont. | Differentiation | **Weighted Total** |
|---|---|---|---|---|---|---|---|---|---|---|
| **Policy engine** (F1-F3) | 4 | 4 | 5 | 5 | 4 | 4 | 4 | 5 | 3 | **62** |
| **Human validation workflow** (B1-B3) | 5 | 4 | 5 | 5 | 4 | 4 | 5 | 5 | 3 | **65** |
| **Audit trails** (H1) | 3 | 5 | 5 | 5 | 4 | 4 | 3 | 5 | 2 | **58** |
| **Static dashboard** (D2) | 3 | 4 | 4 | 5 | 3 | 3 | 4 | 4 | 3 | **51** |
| **SQLite index** (D1) | 3 | 3 | 5 | 5 | 4 | 4 | 3 | 5 | 2 | **53** |
| **Dependency suggestions** (A3) | 4 | 3 | 5 | 5 | 3 | 3 | 4 | 4 | 2 | **52** |
| **External tracker writes** (C1) | 5 | 4 | 3 | 2 | 2 | 2 | 5 | 3 | 4 | **46** |
| **Governed patch proposals** (A4) | 4 | 3 | 3 | 2 | 2 | 2 | 3 | 3 | 5 | **40** |
| **API server/dashboard** (D3-D4) | 2 | 4 | 2 | 2 | 1 | 1 | 2 | 2 | 4 | **30** |
| **Multi-repo crawler** (E1) | 2 | 4 | 2 | 2 | 1 | 1 | 2 | 2 | 3 | **27** |
| **Autonomous remediation** (A6) | 2 | 2 | 1 | 1 | 1 | 1 | 1 | 1 | 2 | **15** |

## Track Classification

### 🟢 Primary Track (Recommended for v2.0)

| Track | Options | Score | Rationale |
|---|---|---|---|
| **Governed validation workflow** | B1, B2, B3, F1, F2, F3, H1, H2 | 62–65 | Highest trust fit, lowest risk, strongest v1 continuity |

### 🟡 Secondary Track (v2.1+ Candidates)

| Track | Options | Score | Rationale |
|---|---|---|---|
| **Portfolio intelligence** | D1, D2 | 51–53 | Adds query/visualization without trust changes |
| **Dependency intelligence** | A3 | 52 | Advisory-only, preserves trust model |

### 🔴 Deferred Track (v2+ After Governance Foundation)

| Track | Options | Score | Rationale |
|---|---|---|---|
| **External tracker writes** | C1 | 46 | High value but requires consent infrastructure first |
| **Governed patch proposals** | A4 | 40 | Complex; requires governance foundation |

### ⛔ Rejected Track (Not Recommended for v2.x)

| Track | Options | Score | Rationale |
|---|---|---|---|
| **API server/dashboard** | D3, D4 | 30 | Breaks local-first, high ops burden |
| **Multi-repo crawler** | E1 | 27 | Network dependency, auth complexity |
| **Autonomous remediation** | A6 | 15 | Violates core trust model |

## Recommended v2.0 Direction

**Primary**: Local policy engine + human validation workflow

This track:
- Preserves the trust model completely (trust fit = 5)
- Has lowest safety risk (safety = 5)
- Builds directly on v1 artifacts (v1 continuity = 5)
- Has manageable implementation complexity
- Enables enterprise governance without external writes

**Phasing**:
1. **v2.0**: Policy engine (custom scoring, completeness rules, thresholds)
2. **v2.1**: Human validation workflow (claim review, gap closure, sign-off)
3. **v2.2**: Audit trails and ownership
4. **v2.3**: Portfolio intelligence (SQLite index, static dashboard)
5. **v2.4**: External tracker writes (after consent infrastructure exists)

## Decision Record

| Date | Decision | Rationale |
|---|---|---|
| 2026-05-27 | Primary track: governed validation workflow | Highest weighted score, strongest trust preservation |

## Related Documents

- [v2 Product Thesis](V2_PRODUCT_THESIS.md)
- [v2 Option Map](V2_OPTION_MAP.md)
- [Automation Boundary Model](V2_AUTOMATION_BOUNDARY_MODEL.md)
- [External Integration Risk Model](V2_EXTERNAL_INTEGRATION_RISK_MODEL.md)
- [Data Model and Deployment Options](V2_DATA_MODEL_AND_DEPLOYMENT_OPTIONS.md)
