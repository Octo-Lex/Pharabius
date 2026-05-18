# Architecture Graph Validation: Ghostwire

## Repository
- **Name**: Ghostwire
- **Ecosystem**: TypeScript/JavaScript monorepo (packages/*)
- **Commit**: N/A
- **Monorepo**: yes (packages/bot, packages/core, packages/desktop, packages/miniapp, packages/app)
- **File count**: ~314 source files with imports detected
- **Source file count**: 314

## Commands Run

`graph`, `analyze --no-ai`

## Graph Summary

| Metric | Value |
|---|---|
| Nodes | 60 |
| Edges | 0 |
| Cycles | 0 |
| Boundary violations | 0 |
| Coupling metrics | 60 |
| Limitations | 420 |
| Runtime | ~300ms |
| File size | ~15 KB |

## Node Detail

| Node | Type | Files |
|---|---|---|
| .github | module | 1 |
| packages | module | 311 |
| scripts | module | 2 |
| + 57 analysis_unit nodes | analysis_unit | 0 |

## TD-ARCH Summary

| Metric | Value |
|---|---|
| Total TD-ARCH findings | 0 |
| False positives | 0 |
| False negatives | 1 (FN-001) |

## False Positives

None.

## False Negatives

**FN-001 — Monorepo node collapse**: Ghostwire has packages like `@ghostwire/core`, `@ghostwire/bot` etc. with inter-package imports. The grapher groups all 311 files under `packages/` into a single "packages" node. All relative imports (e.g., `../services/backup.js`) resolve within this single node → self-import → skipped. The 420 limitations are all unresolved internal-looking imports.

**Root cause**: The node derivation groups by first directory level under `src/` (or repository root). For monorepos using `packages/*` layout, this creates a single massive node instead of individual package nodes.

**Impact**: No edges, no cycles, no TD-ARCH findings for a repo that likely has real package dependencies.

## Debatable Findings

The 57 analysis_unit nodes have 0 files each (units derived from analysis-units.json metadata, not file-level grouping).

## Decision

- [ ] Pass
- [x] Pass with notes
- [ ] Fail

## Recommended Follow-up

**P1 correctness issue**: Node derivation should split monorepo `packages/*` directories into individual package nodes when `package.json` files exist in subdirectories. This is deferred to v0.6.0 (requires design decision on monorepo node strategy).
