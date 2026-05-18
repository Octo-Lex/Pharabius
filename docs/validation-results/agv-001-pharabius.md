# Architecture Graph Validation: Pharabius

## Repository
- **Name**: Pharabius
- **Ecosystem**: Python (src layout)
- **Commit**: `a58a7fe`
- **Monorepo**: no
- **File count**: ~48
- **Source file count**: 45 (imports_detected)

## Commands Run

Full sequence: `init`, `profile`, `scan`, `map`, `graph`, `analyze --no-ai`, `report`, `plan`, `verify`, `status`, `export`

## Graph Summary

| Metric | Value |
|---|---|
| Nodes | 11 (both scope) / 3 (package) / 8 (analysis_unit) |
| Edges | 1 (both/package) / 0 (analysis_unit) |
| Cycles | 0 |
| Boundary violations | 0 |
| Coupling metrics | 11 |
| Limitations | 2 |
| Runtime | ~80ms |
| File size | ~10 KB |

## Scope Variants

| Scope | Nodes | Edges | Cycles |
|---|---|---|---|
| package | 3 | 1 | 0 |
| analysis_unit | 8 | 0 | 0 |
| both | 11 | 1 | 0 |

## TD-ARCH Summary

| Metric | Value |
|---|---|
| Total TD-ARCH findings | 0 |
| Cycle findings | 0 |
| Boundary violation findings | 0 |
| False positives | 0 |
| False negatives | 0 |

## False Positives

None found.

## False Negatives

None for this repo — all internal imports resolve to the single `pharabius` package, which is correct for the src layout.

**Debatable**: The single edge (tests -> pharabius) represents 50 test imports. This is technically correct but not architecturally interesting — test code importing production code is expected.

## Export Verification

- **SARIF**: pass — 1 result, correct structure
- **CSV**: pass — 1 data row
- **JSONL**: pass — 1 line

## Verify/Status Behavior

- **verify**: pass — TD-DEP-001 verified as still_detected
- **status**: pass — shows workspace status correctly

## Decision

- [x] Pass
- [ ] Pass with notes
- [ ] Fail

## Recommended Follow-up

None. Pharabius is the reference implementation and behaves correctly.
