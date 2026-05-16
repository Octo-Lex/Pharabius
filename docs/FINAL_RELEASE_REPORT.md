# Pharabius v0.1.0 — Final Release Report

**Date:** 2026-05-16
**Version:** 0.1.0
**Status:** Release candidate frozen. Ready for git init + tag.

---

## 1. File Inventory

### Source (17 files)

```
src/pharabius/__init__.py
src/pharabius/cli.py
src/pharabius/core/__init__.py
src/pharabius/core/analyzer.py
src/pharabius/core/exclusions.py
src/pharabius/core/init_workspace.py
src/pharabius/core/planner.py
src/pharabius/core/profiler.py
src/pharabius/core/reporter.py
src/pharabius/core/run_metadata.py
src/pharabius/core/scanner.py
src/pharabius/schemas/__init__.py
src/pharabius/schemas/evidence.py
src/pharabius/schemas/finding.py
src/pharabius/schemas/repository.py
src/pharabius/schemas/run_metadata.py
src/pharabius/schemas/work_package.py
```

### Tests (10 files, 65 tests)

```
tests/test_analyzer.py            — 27 tests
tests/test_cli.py                 —  8 tests
tests/test_init_workspace.py      —  1 test
tests/test_planner.py             —  3 tests
tests/test_profiler.py            —  2 tests
tests/test_profiler_coverage.py   —  6 tests
tests/test_reporter.py            —  3 tests
tests/test_run_metadata.py        —  3 tests
tests/test_scanner.py             —  8 tests
tests/test_validate_script.py     —  4 tests
```

### Scripts (1 file)

```
scripts/validate_repo.py
```

### Documentation (16 files)

```
CHANGELOG.md
README.md
docs/ARCHITECTURE.md
docs/ENGINEERING_POLICY.md
docs/KNOWN_LIMITATIONS.md
docs/RELEASE_CHECKLIST.md
docs/ROADMAP.md
docs/VALIDATION_MATRIX.md
docs/VALIDATION_SUMMARY.md
docs/templates/validation-result.md
docs/validation-results/001-pharabius.md
docs/validation-results/002-ghostwire.md
docs/validation-results/003-elephant-rock-platform.md
docs/validation-results/004-nodespan.md
docs/validation-results/005-ariadne.md
docs/validation-results/006-symbiot.md
docs/validation-results/007-craft-agents.md
docs/validation-results/008-aif.md
```

### Configuration (3 files)

```
pyproject.toml
.importlinter
.gitignore
```

---

## 2. Release Gates — All 7 Pass

| # | Gate | Result |
|---|---|---|
| 1 | `ruff format --check .` | ✅ 28 files already formatted |
| 2 | `ruff check .` | ✅ All checks passed |
| 3 | `mypy src` | ✅ Success: no issues in 17 source files |
| 4 | `lint-imports` | ✅ Pharabius modular-monolith layers KEPT. 1 kept, 0 broken |
| 5 | `pytest` | ✅ **65 passed** in 4.26s, coverage **88.39%** |
| 6 | `python -m build` | ✅ Built pharabius-0.1.0.tar.gz + pharabius-0.1.0-py3-none-any.whl |
| 7 | `python scripts/validate_repo.py .` | ✅ 147 evidence, 1 finding, 1 work package |

---

## 3. Clean Wheel Install Proof

Installed from wheel in an isolated venv in `/tmp/`, **outside** the source tree.

### Python version confirmed

```
Python 3.11.9
```

### ai-debt --help (from installed wheel)

```
 Usage: ai-debt [OPTIONS] COMMAND [ARGS]...

 Pharabius technical debt intelligence CLI.

 Options:
 --install-completion   Install completion for the current shell.
 --show-completion      Show completion for the current shell.
 --help                 Show this message and exit.

 Commands:
 init     Create the .ai-debt workspace and default output contract.
 profile  Detect repository structure, stack, tooling, tests, docs, and risk-sensitive areas.
 scan     Collect normalized repository evidence.
 analyze  Convert normalized evidence into deterministic technical debt findings.
 report   Generate deterministic Markdown reports from profile, evidence, and findings.
 plan     Generate remediation roadmap, work packages, and handoff summary.
 run      Run the full deterministic v1 pipeline and write run metadata.
```

### ai-debt run (from installed wheel, temp repo outside source)

```
Repository: C:\Users\USER\AppData\Local\Temp\tmp.xxx\testrepo
Run ID:     RUN-20260516-204249
Evidence:   2 items
Findings:   3
Packages:   3

Output files created:
  .ai-debt/README.md
  .ai-debt/architecture-map.md
  .ai-debt/business-risk-proxy.md
  .ai-debt/config.yaml
  .ai-debt/debt-register.json
  .ai-debt/debt-register.md
  .ai-debt/dependency-health.md
  .ai-debt/evidence.json
  .ai-debt/handoff-summary.md
  .ai-debt/project-profile.json
  .ai-debt/remediation-roadmap.md
  .ai-debt/reports/foundation-audit-report.md
  .ai-debt/runs/RUN-20260516-204249.json
  .ai-debt/security-exposure.md
  .ai-debt/test-health.md
  .ai-debt/work-packages/WP-001-no-test-evidence-detected.md
  .ai-debt/work-packages/WP-002-no-ci-cd-workflow-evidence-detected.md
  .ai-debt/work-packages/WP-003-no-documentation-evidence-detected.md
```

---

## 4. Git Clean / Artifact Check

| Check | Result |
|---|---|
| `.gitignore` covers `.ai-debt/` | ✅ Present |
| `.gitignore` covers `dist/` | ✅ Present |
| `.gitignore` covers `__pycache__/` | ✅ Present |
| `.gitignore` covers `.mypy_cache/`, `.ruff_cache/` | ✅ Present |
| `.gitignore` covers `.validation-repos/` | ✅ Present |
| `.gitignore` covers `*.whl`, `*.tar.gz` | ✅ Present |
| TODOs in `src/` | ✅ None found |
| Git repository initialized | ⚠️ **No** — no `.git` directory exists |
| `dist/` artifacts present | ✅ `pharabius-0.1.0.tar.gz` (39KB) + `pharabius-0.1.0-py3-none-any.whl` (37KB) |

---

## 5. Package Metadata

| Field | Value |
|---|---|
| name | `pharabius` |
| version | `0.1.0` |
| description | Repository-first technical debt intelligence platform |
| readme | `README.md` |
| requires-python | `>=3.11` |
| license | **NOT SET** — no LICENSE file exists, deferred |
| classifiers | **NOT SET** — deferred pending license decision |
| dependencies | typer, pydantic, pyyaml, rich |
| dev dependencies | pytest, pytest-cov, ruff, mypy, import-linter, build |
| scripts | `ai-debt = pharabius.cli:app` |

---

## 6. Remaining Release Blockers

| # | Issue | Severity | Action Required |
|---|---|---|---|
| 1 | **No git repository** | Release-blocking | `git init` + initial commit required before tagging |
| 2 | **No LICENSE file** | Low — documented in KNOWN_LIMITATIONS.md | Optional: add LICENSE + pyproject classifiers before public release |
| 3 | **No classifiers in pyproject.toml** | Low — deferred with license | Optional: add Development Status, Programming Language, etc. |

**Items 2 and 3 are explicitly documented as deferred and do not block functional use.**

---

## 7. Tagging Commands (Prepared, Not Executed)

Requires separate approval.

```bash
cd C:\Next-Era\Pharabius\pharabius
git init
git add .
git commit -m "Release v0.1.0 — deterministic technical debt intelligence pipeline

Full v1 deterministic pipeline: init, profile, scan, analyze, report, plan, run.
Evidence-backed findings, markdown reports, remediation roadmaps, work packages,
run metadata, validation matrix, release hardening, Node workspace lockfile policy.
65 tests, 88.39% coverage, all 7 release gates green."

git tag -a v0.1.0 -m "Pharabius v0.1.0 — Deterministic Technical Debt Intelligence Pipeline"
```
