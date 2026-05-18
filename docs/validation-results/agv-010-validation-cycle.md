# Architecture Graph Validation: validation-cycle (synthetic)

## Repository
- **Name**: validation-cycle
- **Ecosystem**: Python (synthetic 2-node circular dependency)
- **Commit**: N/A
- **Monorepo**: no
- **File count**: 2 source files (pkg_a/main.py, pkg_b/helper.py)
- **Source file count**: 2

## Commands Run

`init`, `scan`, `map`, `graph`, `analyze --no-ai`

## Graph Summary

| Metric | Value |
|---|---|
| Nodes | 2 |
| Edges | 2 |
| Cycles | 1 |
| Boundary violations | 0 |
| Coupling metrics | 2 |
| Limitations | 2 |
| Runtime | ~30ms |

## Cycle Detail

| Cycle ID | Nodes | Edges | Severity |
|---|---|---|---|
| ARCH-CYCLE-11C1A568 | 2 (pkg_a, pkg_b) | 2 | High |

## TD-ARCH Summary

| Metric | Value |
|---|---|
| Total TD-ARCH findings | 1 |
| Cycle findings | 1 |
| Boundary violation findings | 0 |
| False positives | 0 |
| False negatives | 0 |

## Finding Detail

- **TD-ARCH-001**: Confirmed circular dependency between pkg_a and pkg_b
  - Severity: High
  - Evidence: EVD-000007, EVD-000010
  - Locations: src/pkg_a/main.py, src/pkg_b/helper.py
  - Graph cycle ID: ARCH-CYCLE-11C1A568 preserved in description

## False Positives

None. The cycle is real — `pkg_a.main` imports from `pkg_b.helper`, and `pkg_b.helper` imports from `pkg_a.main`.

## False Negatives

None.

## Decision

- [x] Pass
- [ ] Pass with notes
- [ ] Fail

## Recommended Follow-up

None. Cycle detection and TD-ARCH finding generation working correctly.
