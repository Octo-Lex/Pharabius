# Validation Result

## Repository

- **Repository name:** Ghostwire
- **Repository path:** `C:\Next-Era\Ghostwire`
- **Repository URL:** N/A (internal)
- **Repository type:** TypeScript monorepo (Turbo + pnpm)
- **Stack:** TypeScript, React, Rust, Vitest, Turborepo, pnpm

## Run Details

- **Date:** 2026-05-16
- **Pharabius version:** 0.1.0
- **Command used:** `python scripts/validate_repo.py C:/Next-Era/Ghostwire`
- **Runtime:** ~59s

## Results

| Metric | Value |
|---|---|
| Evidence count | 3778 |
| Finding count | 0 |
| Work package count | 0 |
| Critical findings | 0 |
| High findings | 0 |
| Medium findings | 0 |
| Low findings | 0 |

## Top Findings

- No findings generated.

## False Positives

- None. Zero findings is correct — Ghostwire is a well-maintained monorepo with tests, CI, docs, and lockfiles.

## False Negatives / Missed Risks

- `node_modules/` not excluded from scanning — 3778 evidence items inflated by files inside node_modules. This increases runtime significantly (59s).
- Profile fields `has_tests`, `has_ci`, `has_docs`, `has_lockfile` all return `None` despite correct detection of test frameworks, CI workflows, and documentation. These boolean fields appear unused by the analyzer but the schema inconsistency is noted.

## Output Artifacts Reviewed

- [x] `project-profile.json` — detects monorepo, languages, frameworks (React), package managers (cargo, npm, pnpm), build tools (Turbo, Vite), test frameworks (Vitest)
- [x] `evidence.json` — 3778 items (inflated by node_modules)
- [x] `debt-register.json` — correct: 0 findings
- [x] `architecture-map.md` — correct monorepo detection
- [x] `dependency-health.md` — reasonable
- [x] `test-health.md` — reasonable
- [x] `security-exposure.md` — reasonable
- [x] `business-risk-proxy.md` — reasonable
- [x] `remediation-roadmap.md` — empty (correct)
- [x] `handoff-summary.md` — correct

## Decision

- [x] **Pass with notes** — Correct zero findings, but runtime impacted by node_modules scanning.

## Notes

- Performance concern: 59s runtime, likely due to node_modules traversal.
- Scanner should exclude `node_modules/`, `.venv/`, `target/`, `.git/`, `dist/`, `build/` directories to reduce noise and improve performance.

## Follow-up Actions

- Add directory exclusion list to scanner (node_modules, .venv, target, dist, build).
- Investigate profile boolean fields returning `None` despite correct framework detection.
