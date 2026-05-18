# Architecture Graph Validation: Craft-Agents

## Repository
- **Name**: Craft-Agents
- **Ecosystem**: TypeScript/JavaScript monorepo (apps/*, packages/*)
- **Commit**: N/A
- **Monorepo**: yes
- **File count**: ~1162 source files with imports detected
- **Source file count**: 1162

## Commands Run

`map`, `graph`, `analyze --no-ai`

## Graph Summary

| Metric | Value |
|---|---|
| Nodes | 3 |
| Edges | 0 |
| Cycles | 0 |
| Boundary violations | 0 |
| Coupling metrics | 3 |
| Limitations | 1996 |
| Runtime | ~400ms |

## Node Detail

| Node | Type | Files |
|---|---|---|
| apps | module | 509 |
| packages | module | 643 |
| scripts | module | 10 |

## TD-ARCH Summary

| Metric | Value |
|---|---|
| Total TD-ARCH findings | 0 |
| False positives | 0 |
| False negatives | 1 (FN-002) |

## False Positives

None.

## False Negatives

**FN-002 — Monorepo node collapse (same as FN-001)**: Same root cause as Ghostwire. The `apps/` and `packages/` directories are collapsed into single nodes. 1996 unresolved internal-looking imports.

## Decision

- [ ] Pass
- [x] Pass with notes
- [ ] Fail

## Recommended Follow-up

Same as FN-001. P1 correctness issue deferred to v0.6.0.
