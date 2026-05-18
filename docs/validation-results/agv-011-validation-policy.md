# Architecture Graph Validation: validation-policy (synthetic)

## Repository
- **Name**: validation-policy
- **Ecosystem**: Python (synthetic boundary violation)
- **Commit**: N/A
- **Monorepo**: no
- **File count**: 3 source files (cli/app.py, core/engine.py, schemas/models.py)
- **Source file count**: 3
- **Policy**: .ai-debt/architecture-policy.yaml (cli may import core, core may import schemas, schemas may import nothing)

## Commands Run

`init`, `scan`, `map`, `graph`, `graph --policy`, `analyze --no-ai`

## Graph Summary

| Metric | Value |
|---|---|
| Nodes | 1 |
| Edges | 0 |
| Cycles | 0 |
| Boundary violations | 0 |
| Limitations | 1 |

## TD-ARCH Summary

| Metric | Value |
|---|---|
| Total TD-ARCH findings | 0 |
| Cycle findings | 0 |
| Boundary violation findings | 0 |
| False positives | 0 |
| False negatives | 1 (FN-004) |

## False Negatives

**FN-004 — Boundary violation not detected**: `cli/app.py` imports `from myapp.schemas.models import User`, violating the policy (cli may only import core). However, the grapher groups all files under `src/myapp` into a single "myapp" node. The import resolves to the same node → self-import → no edge → no violation.

**Root cause**: Same as FN-001/FN-002 — node derivation doesn't split sub-packages under a common parent. The `src/myapp/cli`, `src/myapp/core`, and `src/myapp/schemas` directories all collapse into one "myapp" package node.

## Decision

- [ ] Pass
- [x] Pass with notes
- [ ] Fail

## Recommended Follow-up

**P1 correctness issue**: Same root cause as FN-001/FN-002. Node derivation should split `src/<package>/<sub-package>` into separate nodes when sub-packages exist. Deferred to v0.6.0.
