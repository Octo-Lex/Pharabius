# Validation Result

## Repository

- **Repository name:** Craft Agents
- **Repository path:** `C:\Next-Era\Craft-Agents`
- **Repository URL:** N/A (internal)
- **Repository type:** TypeScript monorepo (Bun workspaces + Electron)
- **Stack:** TypeScript, Bun, Electron, pnpm/Bun workspaces

## Run Details

- **Date:** 2026-05-16
- **Pharabius version:** 0.1.0
- **Command used:** `python scripts/validate_repo.py C:/Next-Era/Craft-Agents`
- **Runtime:** ~20s

## Results

| Metric | Value |
|---|---|
| Evidence count | 4734 |
| Finding count | 1 |
| Work package count | 1 |
| Critical findings | 0 |
| High findings | 0 |
| Medium findings | 1 |
| Low findings | 0 |

## Top Findings

1. **TD-DEP-001** (Medium): Dependency manifest detected without lockfile evidence

## False Positives

- **Potential false positive on lockfile**: Craft-Agents uses `bun.lock` (detected as `bun.lock` in the repo root). The scanner's lockfile check recognizes `bun.lockb` but not `bun.lock` (Bun v1.2+ changed from binary `bun.lockb` to text `bun.lock`). The missing lockfile finding may be incorrect.

## False Negatives / Missed Risks

- 4734 evidence items — suggests some directories (like `node_modules/`) are being scanned.
- Profile fields `has_tests`, `has_ci`, `has_docs` return `None` despite `.github/` and documentation present.

## Output Artifacts Reviewed

- [x] `project-profile.json` — detects TypeScript, Bun, Electron workspaces
- [x] `evidence.json` — 4734 items
- [x] `debt-register.json` — 1 finding (potential false positive on bun.lock)
- [x] `architecture-map.md` — correct monorepo detection
- [x] `dependency-health.md` — reasonable
- [x] `handoff-summary.md` — correct

## Decision

- [x] **Pass with notes** — Lockfile detection may not recognize `bun.lock` (Bun v1.2+ format).

## Notes

- Bun recently changed from `bun.lockb` (binary) to `bun.lock` (text). The LOCKFILE_NAMES set includes `bun.lockb` but not `bun.lock`. This needs updating.

## Follow-up Actions

- Add `bun.lock` to `LOCKFILE_NAMES` in the analyzer.
- Verify whether `bun.lockb` should remain or be deprecated in favor of `bun.lock`.
