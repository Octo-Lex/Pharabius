# Architecture Graph Validation: AIF

## Repository
- **Name**: AIF
- **Ecosystem**: Rust (multi-crate workspace)
- **Commit**: N/A
- **Monorepo**: yes
- **File count**: 0 imports detected (62 .rs files exist)
- **Source file count**: 0

## Commands Run

`map`, `graph`, `analyze --no-ai`

## Graph Summary

| Metric | Value |
|---|---|
| Nodes | 0 |
| Edges | 0 |
| Cycles | 0 |
| Boundary violations | 0 |
| Limitations | 3 |

## TD-ARCH Summary

| Metric | Value |
|---|---|
| Total TD-ARCH findings | 0 |
| False positives | 0 |
| False negatives | 1 (FN-003, same as Symbiot) |

## False Negatives

**FN-003** (same as Symbiot): Rust `use` syntax not matched by scanner import patterns.

## Decision

- [ ] Pass
- [x] Pass with notes
- [ ] Fail

## Recommended Follow-up

Same as Symbiot FN-003.
