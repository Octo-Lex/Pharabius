# Validation Result

## Repository

- **Repository name:** Ariadne
- **Repository path:** `C:\Next-Era\Ariadne`
- **Repository URL:** N/A (internal)
- **Repository type:** Infrastructure / microservices orchestration
- **Stack:** Go (gateway, registry), Docker, Docker Compose, Vault, Redis, Grafana, Prometheus, Spire

## Run Details

- **Date:** 2026-05-16
- **Pharabius version:** 0.1.0
- **Command used:** `python scripts/validate_repo.py C:/Next-Era/Ariadne`
- **Runtime:** ~2.6s

## Results

| Metric | Value |
|---|---|
| Evidence count | 537 |
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

- **Missing go.sum lockfiles**: Two `go.mod` files detected (`src/gateway/go.mod`, `src/registry/go.mod`) but neither has a corresponding `go.sum` file. The lockfile check compares against basename `go.mod` but `_manifest_files()` returns full paths like `src/gateway/go.mod`, so the comparison `"go.mod" in manifests` fails. This is a false negative.
- **No test frameworks detected**: Despite having test files, no test framework is reported. Go `_test.go` pattern not recognized as test framework.
- Infrastructure configuration (Vault, Redis, Grafana, Prometheus) detected as deployment/infra files but no findings generated for configuration debt.

## Output Artifacts Reviewed

- [x] `project-profile.json` — detects Go, Docker, SQL; identifies `go` package manager
- [x] `evidence.json` — 537 items; 43 test_file_detected, 5 deployment_file_detected, 60 documentation_file_detected
- [x] `debt-register.json` — 0 findings (false negative: missing go.sum)
- [x] `architecture-map.md` — correct service detection
- [x] `dependency-health.md` — reasonable but missing lockfile warning

## Decision

- [x] **Pass with notes** — False negative on missing go.sum lockfiles due to manifest path matching bug.

## Notes

- Fast runtime at 2.6s — efficient scanning of infrastructure repos.
- The manifest path matching bug affects any repo where manifests are in subdirectories (common in Go multi-module repos and monorepos).

## Follow-up Actions

- Fix `_manifest_files()` to return basenames for lockfile comparison, or change the lockfile check to use `any(path.endswith("go.mod") for path in manifests)`.
- Consider adding infrastructure-specific analysis rules for IaC repositories.
