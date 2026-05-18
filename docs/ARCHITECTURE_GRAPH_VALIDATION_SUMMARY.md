# Architecture Graph Validation Summary

**Pharabius version**: v0.5.1
**Date**: 2026-05-18
**Repositories validated**: 11 (9 real, 2 synthetic)

## Result Matrix

| # | Repository | Ecosystem | Nodes | Edges | Cycles | TD-ARCH | FP | FN | Result |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Pharabius | Python | 11 | 1 | 0 | 0 | 0 | 0 | Pass |
| 2 | elephant-rock-platform | Python | 6 | 3 | 0 | 0 | 0 | 0 | Pass |
| 3 | Ghostwire | TypeScript | 60 | 0 | 0 | 0 | 0 | 1 | Pass with notes |
| 4 | Craft-Agents | TypeScript | 3 | 0 | 0 | 0 | 0 | 1 | Pass with notes |
| 5 | validation-java | Java/Maven | 7 | 0 | 0 | 0 | 0 | 1* | Pass |
| 6 | validation-dotnet | .NET | 6 | 0 | 0 | 0 | 0 | 0 | Pass |
| 7 | Symbiot | Rust | 12 | 0 | 0 | 0 | 0 | 1 | Pass with notes |
| 8 | AIF | Rust | 0 | 0 | 0 | 0 | 0 | 1 | Pass with notes |
| 9 | validation-iac | Terraform | 3 | 0 | 0 | 0 | 0 | 0 | Pass |
| 10 | validation-cycle | Python (synthetic) | 2 | 2 | 1 | 1 | 0 | 0 | Pass |
| 11 | validation-policy | Python (synthetic) | 1 | 0 | 0 | 0 | 0 | 1 | Pass with notes |

*Expected FN — Java import resolution is documented as best-effort.

## Ecosystem Coverage

| Ecosystem | Repos | Edges Found | Status |
|---|---|---|---|
| Python (src layout) | 3 | 6 | Working correctly |
| TypeScript/JS monorepo | 2 | 0 | Node collapse (FN-001/FN-002) |
| Java/Maven | 1 | 0 | Best-effort resolution |
| .NET | 1 | 0 | No imports detected |
| Rust | 2 | 0 | Import detection missing (FN-003) |
| Terraform | 1 | 0 | N/A (no imports) |

## TD-ARCH Quality Summary

| Metric | Value |
|---|---|
| Repos with actionable TD-ARCH findings | 1/11 (validation-cycle) |
| False positive rate | 0% (0 FP across all repos) |
| False negative rate | 4/11 repos (FN-001 through FN-004) |
| Evidence/location accuracy | 100% (where findings exist) |
| Graph ID traceability | 100% (cycle IDs preserved in descriptions) |

## Common False Negatives

| ID | Pattern | Repos Affected | Root Cause |
|---|---|---|---|
| FN-001 | Monorepo node collapse (packages/*) | Ghostwire | Node derivation groups by first directory level |
| FN-002 | Monorepo node collapse (apps/*, packages/*) | Craft-Agents | Same as FN-001 |
| FN-003 | Rust import detection missing | Symbiot, AIF | Scanner IMPORT_PATTERNS lacks Rust `use` syntax |
| FN-004 | Sub-package collapse prevents boundary detection | validation-policy | Node derivation doesn't split sub-packages |

## Common False Positives

None found across all 11 repositories. Zero false positive findings.

## Policy UX Findings

- Policy auto-detection works correctly (`.ai-debt/architecture-policy.yaml`)
- `--policy` flag works for explicit path
- Simple YAML parser works without pyyaml dependency
- **Issue**: Policy is only useful when graph has edges across layers. Monorepo node collapse (FN-001/004) makes boundary checking ineffective for sub-package architectures.

## Recommended Bug Fixes

See [ARCHITECTURE_GRAPH_BACKLOG.md](./ARCHITECTURE_GRAPH_BACKLOG.md) for full prioritization.

## v0.6.0 Readiness Recommendation

**Recommendation: B — Architecture Graph Enhancements before AI**

**Rationale:**
- TD-ARCH false positive rate is 0% — excellent
- TD-ARCH false negative rate is 36% (4/11 repos) — needs improvement
- The primary FN cause is node derivation granularity, not analysis logic
- Graph resolution must improve before AI adds value on top
- AI Adapter without better graph resolution would amplify noise from unresolved imports

**v0.6.0 direction**: Fix P1 node derivation issues (monorepo/sub-package splitting), add Rust import detection. Then proceed to AI Adapter in v0.7.0.
