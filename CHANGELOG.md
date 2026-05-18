# Changelog

All notable changes to Pharabius are documented in this file.

## [Unreleased]

### Fixed

- .NET manifest detection: `.csproj`, `.fsproj`, `.vbproj` now produce `manifest_detected` evidence
- .NET solution files (`.sln`) emit `solution_file_detected`, not dependency manifest evidence
- `.NET` dependency findings now produced for projects without `packages.lock.json`
- Java Maven parent/aggregator POMs no longer produce TD-DEP dependency findings
- Java Maven library modules no longer produce TD-DEP dependency findings
- CI workflow files no longer trigger false risk signals from `actions/checkout` or `deploy` keywords
- `.terraform.lock.hcl` now detected as reproducibility evidence

### Added

- Suffix-based manifest detection for .NET project files
- Maven POM role classification (parent/library/application/unknown)
- CI/deployment file context-aware keyword suppression
- Terraform lockfile evidence detection
- NuGet package manager detection in profiler via `.csproj`/`.fsproj` suffix

## v0.3.1 — 2026-05-17

### Added

- `ai-debt verify` — Verify existing findings against current repository evidence
- `.ai-debt/verification-report.json` — Machine-readable verification results
- `.ai-debt/verification-report.md` — Human-readable verification report
- 6 verification statuses: `still_detected`, `likely_remediated`, `evidence_missing`, `partially_supported`, `stale`, `uncertain`
- Location verification (checks if finding file paths still exist)
- Structured work package verification with `valid`/`stale`/`orphaned`/`needs_review` statuses

## v0.2.1 — 2026-05-17

### Changed

- Remove phantom "profile boolean fields return None" limitation (fields never existed)
- Update GitHub Actions to Node.js 24-compatible versions (checkout@v6, setup-python@v6)

## v0.2.0 — 2026-05-17

### Added

- `ai-debt map` — Map repository evidence into analysis units
- `.ai-debt/analysis-units.json` — Structured analysis unit output
- Analysis Unit IR with 9 initial unit types: package, service, cli, test_suite, ci_workflow, infra_area, config_surface, documentation_area, security_sensitive_area
- Stable deterministic analysis unit IDs (AU-{TYPE}-{HEX8})
- Trust-boundary tags for security-sensitive areas
- Evidence-to-unit linkage
- Finding-to-unit linkage (`analysis_unit_ids` on DebtFinding)
- Report sections for analysis units (foundation, architecture, security, test)
- Run metadata includes `analysis_unit_count`

### Changed

- Analysis unit evidence attachment is now type-specific (reduces collateral linkage)
- Security-sensitive areas are grouped by nearest package/service root (reduces explosion)
- Risk evidence in docs/ and tests/ no longer creates security-sensitive units
- Tool/cache directories (.importlinter_cache, .pytest_cache, etc.) no longer produce units
- Zero-evidence units are filtered from output

## v0.1.0 — 2026-05-16

### Added

- **`ai-debt init`** — Create `.ai-debt/` workspace with config and README.
- **`ai-debt profile`** — Detect repository languages, frameworks, package managers, build tools, test frameworks, entry points, deployment files, infrastructure files, documentation, risk areas, and monorepo structure.
- **`ai-debt scan`** — Collect normalized evidence: file tree, manifests, lockfiles, configuration, tests, CI/CD, Docker, IaC, documentation, imports, git metadata, risk keywords, and build/test scripts.
- **`ai-debt analyze --no-ai`** — Generate deterministic debt findings from evidence using 6 analysis rules:
  - Missing tests (TD-TEST)
  - Risk-sensitive areas without tests (TD-SEC)
  - Missing CI/CD (TD-BUILD)
  - Missing documentation (TD-DOC)
  - Missing dependency lockfile (TD-DEP)
  - Environment config without example (TD-CONFIG)
- **`ai-debt report`** — Generate 6 Markdown domain reports:
  - Architecture map
  - Dependency health
  - Test health
  - Security exposure
  - Business risk proxy
  - Foundation audit report
- **`ai-debt plan`** — Generate remediation roadmap, work packages (WP-*.md), and engineering handoff summary from the debt register.
- **`ai-debt run`** — Execute the full deterministic pipeline in order and write run metadata to `.ai-debt/runs/RUN-YYYYMMDD-HHMMSS.json`.
- **Run metadata** — Structured JSON capturing run ID, timestamp, repository, git info, commands run, files written, limitations, and summary statistics.
- **Validation matrix** — 8 repository types defined for pre-release testing.
- **Validation script** — `scripts/validate_repo.py` for repeatable validation.
- **Release checklist** — Comprehensive pre-release verification checklist.
- **Governance** — Import layer contract (`cli → core → schemas`), CI workflow, ruff/mypy/pytest-cov/import-linter configuration.

### Changed

- **Step 7.4 — Release hardening**:
  - Ecosystem-specific lockfile detection — each ecosystem (Node.js, Python, Go, Rust, Java, PHP, Ruby, .NET) checked independently.
  - Package-root-aware manifest/lockfile matching — lockfiles must exist in the same directory as the manifest. Nested manifests are no longer masked by root lockfiles.
  - Shared exclusion module (`core/exclusions.py`) — scanner and profiler use identical directory exclusion logic.
  - Bun lockfile support — `bun.lock` and `bun.lockb` recognized as Node.js lockfiles.
  - Go `*_test.go` detection — Go test files recognized in scanner and profiler.
  - Rust Cargo.lock caution — Rust lockfile findings use Medium severity with library crate caution in description, risks, and verification recommendations.

- **Step 7.5 — Node workspace lockfile policy**:
  - Node workspace satisfaction rule — nested `package.json` files are considered lockfile-satisfied when workspace evidence exists and a root Node lockfile is present.
  - Workspace markers detected: `pnpm-workspace.yaml`, `turbo.json`, `nx.json`, `lerna.json`, `rush.json`, root `package.json` with `"workspaces"` field.
  - Root-only enforcement — only root `package.json` is inspected for workspaces field.
  - Non-Node ecosystems remain strictly package-root-aware.

### Known Limitations

See [docs/KNOWN_LIMITATIONS.md](docs/KNOWN_LIMITATIONS.md) for the full list.
