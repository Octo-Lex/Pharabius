# Architecture Graph Validation: Symbiot

## Repository
- **Name**: Symbiot
- **Ecosystem**: Rust (crates/* workspace)
- **Commit**: N/A
- **Monorepo**: yes (Rust workspace with multiple crates)
- **File count**: 0 imports detected (29 .rs files exist)
- **Source file count**: 0

## Commands Run

`graph`, `analyze --no-ai`

## Graph Summary

| Metric | Value |
|---|---|
| Nodes | 12 |
| Edges | 0 |
| Cycles | 0 |
| Boundary violations | 0 |
| Limitations | 2 |

## TD-ARCH Summary

| Metric | Value |
|---|---|
| Total TD-ARCH findings | 0 |
| False positives | 0 |
| False negatives | 1 (FN-003) |

## False Negatives

**FN-003 — Rust import detection missing**: 29 `.rs` files exist but 0 `imports_detected` evidence. The scanner's `IMPORT_PATTERNS` regex only matches Python/JS/TS patterns (`import X`, `from X import`, `require('X')`). Rust `use crate::module::item` syntax is not matched.

## Decision

- [ ] Pass
- [x] Pass with notes
- [ ] Fail

## Recommended Follow-up

**P1 correctness issue**: Add Rust `use` pattern to scanner's `IMPORT_PATTERNS`. Deferred to v0.6.0 (scanner change, not grapher fix).
