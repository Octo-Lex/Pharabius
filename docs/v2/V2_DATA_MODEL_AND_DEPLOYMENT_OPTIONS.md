# Pharabius v2 Data Model and Deployment Architecture Options

**Status**: Planning draft  
**Date**: 2026-05-27  
**Not an implementation commitment**

This document maps possible v2 deployment models and data architectures with tradeoff analysis.

## Deployment Options

| Option | Description | Ops Burden | Local-First | Trust Model | Recommendation |
|---|---|---|---|---|---|
| **D0** | CLI-only, file-based (v1 current) | None | ✅ Full | Preserved | **v2.0 baseline** |
| **D1** | CLI + local SQLite cache/index | Low | ✅ Full | Preserved | Strong v2 candidate |
| **D2** | CLI + static HTML dashboard | Low | ✅ Full | Preserved | Possible v2.1+ |
| **D3** | Local FastAPI service | Medium | ⚠️ Optional | Requires local auth | Premature for v2.0 |
| **D4** | Hosted API server | High | ❌ Requires network | Requires auth, TLS, ops | v2+ exploration |
| **D5** | Multi-tenant SaaS | Very high | ❌ Cloud-dependent | Major trust change | Not recommended |
| **D6** | Scheduled organization crawler | High | ⚠️ Hybrid | Requires repo auth | v2+ exploration |

## Data Model Options

| Model | Description | Rebuildable | Portability | Complexity | Recommendation |
|---|---|---|---|---|---|
| **File contract only** | `.ai-debt/` is source of truth | N/A | ✅ Full | Minimal | **v2.0 baseline** |
| **SQLite index** | Derived local index over artifacts | ✅ Rebuildable | ✅ Full | Low | Strong v2 candidate |
| **Postgres service DB** | Centralized state store | ⚠️ Migration needed | ❌ Service-dependent | High | Premature for v2.0 |
| **Graph DB** | Deep relationship queries | ⚠️ Migration needed | ❌ Service-dependent | High | Premature |
| **Object storage + metadata DB** | Scalable artifact archive | ⚠️ Migration needed | ❌ Service-dependent | High | v2+ only |

## Architectural Principles

Any v2 architecture must satisfy:

1. **`.ai-debt/` remains portable**: Copy the directory, get the full analysis state
2. **Any database is derived/rebuildable**: Not canonical unless explicitly declared
3. **Local-only mode remains supported**: No network required for core workflow
4. **No hidden network operations**: All network calls explicit and user-visible
5. **Schema compatibility maintained**: v1 schemas parse in v2 without data loss
6. **CLI-first**: All features accessible via CLI; UI/API is additive

## Option Analysis

### D0: CLI-only, File-Based (v1 Current)

**Pros**: Zero ops, fully portable, offline-capable, trust-preserving  
**Cons**: No query capability across runs, no temporal tracking, limited portfolio scale  
**Migration**: None (current state)

### D1: CLI + Local SQLite Cache

**Pros**: Fast cross-run queries, temporal tracking, still local-first, rebuildable from `.ai-debt/`  
**Cons**: SQLite dependency, cache invalidation complexity  
**Migration**: Auto-build from existing `.ai-debt/` on first run; no user action needed  
**Scope**: Portfolio queries, temporal diff ("what changed since last run?"), cross-repo analytics

### D2: CLI + Static HTML Dashboard

**Pros**: Visual portfolio overview, no server runtime, portable HTML  
**Cons**: Limited interactivity, generation time, stale-by-default  
**Migration**: Generate from `.ai-debt/` on demand; no persistent state  
**Scope**: Portfolio visualization, executive summaries, trend charts

### D3: Local FastAPI Service

**Pros**: Real-time queries, API for integrations, WebSocket updates  
**Cons**: Process management, local auth, startup time  
**Migration**: Index `.ai-debt/` on startup; derived state  
**Scope**: Dashboard backend, CI integration, agent API

### D4-D6: Hosted/Cloud Options

**Analysis deferred to v2+**. These introduce significant operational burden and trust model changes.

## Migration Considerations

### v1 → v2 File Contract

| Concern | Approach |
|---|---|
| Existing `.ai-debt/` directories | v2 must read v1 artifacts without migration |
| Schema versioning | `schema_version: "1.0"` remains valid; v2 schemas may be `"2.0"` |
| New artifact types | Additive only; v2 artifacts coexist with v1 |
| Removed artifact types | Not allowed in v2.x per stability contract |

### D1 SQLite Migration Path

1. v2 CLI detects `.ai-debt/` directory
2. Auto-builds SQLite index from artifacts
3. Index is treated as derived cache; deletable without data loss
4. Future runs update index incrementally

## Recommendation

**v2.0 should adopt D0 as baseline with D1 as the primary expansion candidate.**

- D0 preserves complete v1 compatibility
- D1 adds query capability without sacrificing local-first
- D2 can follow as a presentation layer in v2.1+
- D3-D6 require significant design work and should be evaluated in v2+ planning cycles

## Related Documents

- [v2 Product Thesis](V2_PRODUCT_THESIS.md)
- [v2 Option Map](V2_OPTION_MAP.md)
- [Automation Boundary Model](V2_AUTOMATION_BOUNDARY_MODEL.md)
- [External Integration Risk Model](V2_EXTERNAL_INTEGRATION_RISK_MODEL.md)
