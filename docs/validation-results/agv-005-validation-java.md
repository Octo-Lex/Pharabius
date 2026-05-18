# Architecture Graph Validation: validation-java

## Repository
- **Name**: validation-java
- **Ecosystem**: Java/Maven multi-module (api-service, data-service, common-lib)
- **Commit**: N/A
- **Monorepo**: yes (multi-module Maven)
- **File count**: 4 source files with imports detected
- **Source file count**: 4

## Commands Run

`graph`, `analyze --no-ai`

## Graph Summary

| Metric | Value |
|---|---|
| Nodes | 7 |
| Edges | 0 |
| Cycles | 0 |
| Boundary violations | 0 |
| Limitations | 1 |
| Runtime | ~50ms |

## Node Detail

| Node | Type | Files |
|---|---|---|
| api-service | module | 3 |
| data-service | module | 1 |
| + 5 analysis_unit nodes | analysis_unit | various |

## TD-ARCH Summary

| Metric | Value |
|---|---|
| Total TD-ARCH findings | 0 |
| False positives | 0 |
| False negatives | 1 |

## False Negatives

**Expected FN — Java import resolution**: Java imports use `com.example.*` package paths which don't match `api-service`/`data-service` directory names. The grapher's internal prefix discovery finds no matching prefixes. This is a documented limitation (best-effort for Java).

## Decision

- [x] Pass
- [ ] Pass with notes
- [ ] Fail

## Recommended Follow-up

None. Java resolution is documented as best-effort. The nodes are correctly derived from directory structure.
