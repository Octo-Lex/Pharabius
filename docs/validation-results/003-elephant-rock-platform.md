# Validation Result

## Repository

- **Repository name:** Elephant Rock Platform
- **Repository path:** `C:\Next-Era\elephant-rock-platform`
- **Repository URL:** N/A (internal)
- **Repository type:** Python API/service + frontend monorepo
- **Stack:** Python (FastAPI), TypeScript (React), Docker, Alembic, pytest, Vitest

## Run Details

- **Date:** 2026-05-16
- **Pharabius version:** 0.1.0
- **Command used:** `python scripts/validate_repo.py C:/Next-Era/elephant-rock-platform`
- **Runtime:** ~108s

## Results

| Metric | Value |
|---|---|
| Evidence count | 28714 |
| Finding count | 0 |
| Work package count | 0 |
| Critical findings | 0 |
| High findings | 0 |
| Medium findings | 0 |
| Low findings | 0 |

## Top Findings

- No findings generated.

## False Positives

- None.

## False Negatives / Missed Risks

- **Missing Python lockfile**: Root `pyproject.toml` exists without a corresponding `poetry.lock`, `uv.lock`, or `Pipfile.lock`. The analyzer did not flag this because `frontend/package-lock.json` was detected, and the lockfile check has an early return when ANY lockfile is found anywhere in the repo. This masks the missing Python lockfile.
- **Performance**: 28714 evidence items — inflated by `.mypy_cache/`, `node_modules/`, and other generated directories. 108s runtime.
- Profile fields `has_tests`, `has_ci`, `has_docs` all `None` despite correct detection of test frameworks (pytest, Vitest) and CI (.github).

## Output Artifacts Reviewed

- [x] `project-profile.json` — detects FastAPI, React, pytest, Vitest, Docker; monorepo correctly identified
- [x] `evidence.json` — 28714 items (severely inflated by cache/node_modules)
- [x] `debt-register.json` — 0 findings (false negative: missing Python lockfile)
- [x] `architecture-map.md` — correct monorepo detection
- [x] `dependency-health.md` — reasonable but lacks Python lockfile warning
- [x] `test-health.md` — reasonable
- [x] `security-exposure.md` — reasonable
- [x] `business-risk-proxy.md` — reasonable
- [x] `handoff-summary.md` — correct but incomplete

## Decision

- [x] **Pass with notes** — Critical false negative: multi-ecosystem lockfile detection.

## Notes

- The early return in `_analyze_missing_lockfile` when ANY lockfile exists is a design flaw for multi-ecosystem repos. The check should be per-ecosystem, not global.
- Runtime of 108s is impractical for CI. Directory exclusion is essential.

## Follow-up Actions

- Fix lockfile detection to check per-ecosystem instead of global early-return.
- Add directory exclusion list to scanner (`.mypy_cache`, `node_modules`, `.venv`, `target`, `dist`, `build`, `.pytest_cache`, `.ruff_cache`, `__pycache__`).
