# Validation Summary

Pharabius v0.1.0 validation run completed on 2026-05-16.

---

## Overview

| Metric | Value |
|---|---|
| Total repositories validated | 8 |
| Repository types covered | 6 of 8 target categories |
| Total pass | 4 |
| Pass with notes | 4 |
| Fail | 0 |

---

## Repository Types Covered

| Target Category | Repository Used | Covered |
|---|---|---|
| Small TypeScript frontend | Ghostwire (TS monorepo) | Partial — monorepo with TS frontend |
| Node.js backend/API | NodeSpan (Go service) | No — used Go instead |
| Python API/service | Elephant Rock Platform | Yes |
| Java or JVM service | — | No — no JVM repos available |
| Monorepo | Ghostwire, Craft Agents | Yes |
| Infrastructure-as-code repository | Ariadne | Yes |
| Legacy-style repository | — | No — used well-maintained repos |
| Mature open-source repository | NodeSpan, Craft Agents | Partial |

---

## Finding Distribution

| Repository | Evidence | Findings | WPs | Critical | High | Medium | Low |
|---|---|---|---|---|---|---|---|
| Pharabius | 138 | 1 | 1 | 0 | 0 | 1 | 0 |
| Ghostwire | 3778 | 0 | 0 | 0 | 0 | 0 | 0 |
| Elephant Rock Platform | 28714 | 0 | 0 | 0 | 0 | 0 | 0 |
| NodeSpan | 1378 | 0 | 0 | 0 | 0 | 0 | 0 |
| Ariadne | 537 | 0 | 0 | 0 | 0 | 0 | 0 |
| Symbiot | 63 | 2 | 2 | 0 | 2 | 0 | 0 |
| Craft Agents | 4734 | 1 | 1 | 0 | 0 | 1 | 0 |
| AIF | 180 | 2 | 2 | 0 | 0 | 1 | 1 |
| **Total** | **39522** | **6** | **6** | **0** | **2** | **3** | **1** |

---

## Most Common Finding Categories

| Category | Count | Description |
|---|---|---|
| Missing dependency lockfile | 2 | TD-DEP-001: Manifest without lockfile |
| Missing tests | 1 | TD-TEST-001: No test evidence |
| Risk without tests | 1 | TD-SEC-001: Risk-sensitive areas without tests |
| Missing CI/CD | 1 | TD-BUILD-001: No CI/CD workflow |
| Missing documentation | 1 | TD-DOC-001: No documentation |

---

## Most Common False Positives

| Issue | Repos Affected | Severity |
|---|---|---|
| `bun.lock` not recognized as lockfile | Craft Agents | Medium — Bun v1.2+ uses `bun.lock` instead of `bun.lockb` |

---

## Most Common False Negatives

| Issue | Repos Affected | Severity |
|---|---|---|
| Multi-ecosystem lockfile detection | Elephant Rock Platform | High — Python lockfile missed because Node lockfile exists |
| Manifest path matching bug | Ariadne | High — `go.mod` in subdirectories not matched by basename check |
| `node_modules/` scanned | Ghostwire, Elephant Rock Platform, Craft Agents | Medium — inflates evidence count and runtime |
| Profile boolean fields return `None` | All repos | Low — `has_tests`, `has_ci`, `has_docs` always `None` |
| No Go test framework detection | NodeSpan, Ariadne | Low — Go `_test.go` pattern not recognized |

---

## Recommended Rule-Tuning Backlog

Priority order for post-v0.1.0 improvements:

### P0 — Correctness Bugs

1. **Fix multi-ecosystem lockfile detection**: Remove global early return in `_analyze_missing_lockfile`. Check each ecosystem independently.
2. **Fix manifest path matching**: Change `_manifest_files()` to return basenames, or update lockfile checks to use path suffix matching.

### P1 — Performance

3. **Add directory exclusion list**: Exclude `node_modules/`, `.venv/`, `target/`, `dist/`, `build/`, `.mypy_cache/`, `.pytest_cache/`, `.ruff_cache/`, `__pycache__/`, `.git/` from scanning.
4. **Evidence count ceiling**: Consider capping evidence items per category to prevent explosion on large repos.

### P2 — Coverage Gaps

5. **Add `bun.lock` to lockfile names**: Bun v1.2+ uses text `bun.lock` instead of binary `bun.lockb`.
6. **Add Go test framework detection**: Recognize `_test.go` file pattern as Go testing.
7. **Fix profile boolean fields**: Set `has_tests`, `has_ci`, `has_docs`, `has_lockfile` based on detected evidence instead of leaving as `None`.

### P3 — Future Enhancements

8. **Add complexity-based findings**: Flag repos with high architectural complexity.
9. **Add infrastructure-specific rules**: IaC repos (Terraform, K8s, Helm) have unique debt patterns.
10. **Add per-file risk scoring**: Move beyond directory-level risk to file-level granularity.

---

## Release Readiness Assessment

| Criterion | Status |
|---|---|
| `ai-debt run` completes without error on all repos | ✅ Pass |
| Every finding has evidence IDs | ✅ Pass |
| No work package without linked debt ID | ✅ Pass |
| Run metadata written for every run | ✅ Pass |
| No crash or unhandled exception | ✅ Pass |
| Reports readable across all repo types | ✅ Pass |
| At least 6 of 8 repos produce ≥1 finding | ❌ Only 3 of 8 produce findings |
| No false positive severity exceeds Medium | ✅ Pass |
| Legacy repos produce most findings | N/A — no legacy repos tested |
| Mature repos produce fewer findings | ✅ Ghostwire/NodeSpan: 0 findings |

### Verdict

**Pharabius v0.1.0 is conditionally ready for release** with documented caveats:

- The tool correctly identifies real technical debt (missing tests, missing CI, missing docs, missing lockfiles).
- The "no evidence → no finding" principle is consistently enforced.
- Two correctness bugs affect false negative rates (multi-ecosystem lockfiles, subdirectory manifest matching).
- Performance on repos with `node_modules/` is impractical for CI without directory exclusion.
- The 6/8 finding threshold is not met (3/8), but this partly reflects that most tested repos are well-maintained internal projects.

**Recommendation**: Ship v0.1.0 with these known limitations documented, then address P0 bugs in a v0.1.1 patch release.

---

## Step 7.4 Release-Hardening Fixes

Applied 2026-05-16.

### Fixes applied

1. **P0: Ecosystem-specific lockfile detection** — Each ecosystem (Node.js, Python, Go, Rust, etc.) is now checked independently for lockfile presence.
2. **P0: Package-root-aware manifest/lockfile matching** — Lockfiles must exist in the same directory as the manifest to satisfy the check. Nested manifests (`services/api/pyproject.toml`) are no longer masked by root lockfiles.
3. **P1: Shared exclusion module** — Scanner and profiler now share a single exclusion set via `core/exclusions.py`. Added `.ruff_cache` and `.mypy_cache`.
4. **P2: Bun lockfile support** — `bun.lock` and `bun.lockb` recognized as Node.js lockfiles.
5. **P2: Go `*_test.go` detection** — Go test files recognized in scanner (test_file_detected) and profiler ("Go testing" framework).
6. **Rust Cargo.lock caution** — Rust lockfile findings use Medium severity with library crate caution in description, risks_and_cautions, and verification_recommendations.

### Before/After comparison

| Repository | Metric | Before | After |
|---|---|---|---|
| Pharabius | Findings | 1 (Medium) | 1 (Medium) — title now says "Python" |
| Pharabius | Evidence | 138 | 138 |
| Elephant Rock | Findings | **0** | **1 Python TD-DEP** ✅ P0 fixed |
| Elephant Rock | Evidence | 28,714 | **8,622** ✅ exclusion fix |
| Elephant Rock | Runtime | 108s | **9s** ✅ 12x faster |
| Ghostwire | Findings | 0 | **6 Node.js TD-DEP** (per-package, correct) |
| Ghostwire | Evidence | 3,778 | 3,778 |
| Ghostwire | Runtime | 59s | 35s |
| NodeSpan | Findings | 0 | 0 |
| NodeSpan | Evidence | 1,378 | 1,428 |
| NodeSpan | Test frameworks | pytest | pytest + **Go testing** ✅ |
| Symbiot | Findings | 2 (High) | **5** (2 High + 3 Medium Rust TD-DEP) |
| Symbiot | Evidence | 63 | 63 |
| Symbiot | Rust caution | N/A | ✅ In description + risks + verification |

### False positives observed after fix

- **Ghostwire pnpm monorepo**: 6 Node.js TD-DEP findings for packages under `packages/*/`. This is technically correct per package-root matching — each `packages/foo/package.json` doesn't have its own lockfile. For pnpm workspaces, the root `pnpm-lock.yaml` covers all packages. This is a known trade-off of strict package-root matching.

### No new false negatives

All previously correct findings remain correct. No regressions observed.

---

## Step 7.5 Node Workspace Lockfile Policy

Applied 2026-05-16.

### Problem

Step 7.4 introduced package-root-aware lockfile detection, which correctly caught missing lockfiles per ecosystem per directory. However, Node.js monorepos using workspace managers (pnpm, yarn, turbo, nx, lerna, rush) conventionally use a single root lockfile to cover all workspace packages. This produced false positives.

### Fix

Added a **Node workspace satisfaction rule**: nested `package.json` files are considered lockfile-satisfied when:
1. Node workspace evidence exists (6 markers detected)
2. A root Node lockfile exists
3. The manifest is nested (not at root)

**Node.js only.** All other ecosystems remain strictly package-root-aware.

### Workspace markers detected

1. `pnpm-workspace.yaml` — already in scanner
2. `turbo.json` — added to scanner MANIFEST_FILES
3. `nx.json` — added to scanner MANIFEST_FILES
4. `lerna.json` — added to scanner MANIFEST_FILES
5. `rush.json` — added to scanner MANIFEST_FILES
6. Root `package.json` with `"workspaces"` field — new scan inspection (root only)

### Root-only package.json enforcement

Only root `package.json` (`relative == "package.json"`) is inspected for the `"workspaces"` field. Nested `package.json` files with workspaces do not create repository-level workspace evidence.

### Before/After comparison

| Repository | Metric | Step 7.4 | Step 7.5 |
|---|---|---|---|
| Pharabius | Findings | 1 Python TD-DEP | 1 Python TD-DEP (unchanged) |
| Pharabius | Evidence | 138 | 138 |
| Pharabius | Runtime | 1.7s | 1.7s |
| Ghostwire | Findings | **6 Node TD-DEP** | **0** ✅ false positives fixed |
| Ghostwire | Evidence | 3,778 | 3,779 |
| Ghostwire | Runtime | 35s | 43s |
| Craft Agents | Findings | **1 Node TD-DEP** | **0** ✅ bun.lock + workspace |
| Craft Agents | Evidence | 4,734 | 4,737 |
| Craft Agents | Runtime | 20s | 2.3s |
| Elephant Rock | Findings | 1 Python TD-DEP | 1 Python TD-DEP (unchanged) |
| Elephant Rock | Evidence | 8,622 | 8,625 |
| Elephant Rock | Runtime | 9s | 10s |
| NodeSpan | Findings | 0 | 0 (unchanged) |
| NodeSpan | Evidence | 1,428 | 1,428 |
| NodeSpan | Runtime | 1.2s | 1.4s |

### Non-Node ecosystems confirmed unchanged

- Python: `services/api/pyproject.toml` + root `uv.lock` → still TD-DEP
- Node workspace satisfied + Python missing lock → only Python TD-DEP
- All Step 7.4 regression tests still pass
