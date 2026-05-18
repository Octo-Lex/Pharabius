# Changelog

All notable changes to Pharabius are documented in this file.

## [Unreleased]

### Fixed

- Empty `evidence_ids` now rejected — AI enrichments must include at least one valid evidence ID
- Unknown `--finding-id` now fails clearly instead of silently returning 0 enrichments
- Missing `enrichments` key in AI output now produces rejection record instead of silently passing
- Sidecar markdown now includes Privacy Caution section, timestamp, and canonical-artifact statement

### Tests

- 491 tests (54 new), 83.30% coverage
- New rejection tests: 18 tests covering schema failures, evidence integrity, batch behavior
- New context stress tests: 15 tests for budget caps, truncation, corrupted artifacts, ordering
- New sidecar quality tests: 4 tests for privacy caution, timestamp, canonical statement
- New immutability tests: 6 parameterized modes (disabled, mock, dry-run, strict, finding-id, max-findings)
- New CLI integration tests: 10 tests for enrich command
- New import boundary and privacy checks

### Added

- `ai-debt enrich` command — provider-neutral, schema-validated, evidence-constrained AI enrichment
- `src/pharabius/ai/` package with adapter interface, mock provider, context assembly, and validation
- `src/pharabius/schemas/ai_enrichment.py` — strict Pydantic schemas for AI output
- Sidecar output contract: `.ai-debt/ai/` directory with enrichment-report.json/md, finding-enrichments.json, rejected-ai-output.json
- Provider modes: `disabled` (default), `mock` (deterministic testing)
- CLI options: `--provider`, `--max-findings`, `--finding-id`, `--dry-run`, `--strict`
- Bounded context assembly with budget controls
- Evidence ID validation — AI output must reference existing evidence IDs
- Finding ID validation — AI output must reference existing findings
- Rejection records for invalid AI output with reasons and field names
- Import-linter AI layer contract (`cli → core → ai → schemas`)
- New documentation: `docs/AI_ADAPTER.md`

### Security

- AI disabled by default (`--provider disabled`)
- No real network provider in v0.7.0
- No credentials in repository files
- No secrets in logs

### Tests

- 437 tests (46 new), 82.38% coverage
- New test file: `tests/test_ai_adapter.py` covering adapter, context, validation, enricher, immutability, report format

### Fixed

- FN-003 completed: Symbiot now produces 3 distinct crate nodes and 1 cross-crate edge (symbiot-cli -> symbiot-core) instead of 1 collapsed node with 0 edges
- AIF graph unchanged (16 edges maintained)

### Tests

- 391 tests (22 new), 82.85% coverage
- New tests: workspace node derivation, kebab→snake normalization, cross-crate edges, intra-crate skip, edge aggregation

### Added

- **TS/JS monorepo node splitting** — Detect `package.json` in `packages/*`, `apps/*`, `services/*`, `libs/*`, `modules/*` and create individual package nodes instead of collapsing into a single directory node
- **TS/JS workspace import resolution** — Match imports like `@repo/core` to local package nodes using longest-prefix matching with exact-first rules
- **Python policy-driven sub-package splitting** — Enable sub-package nodes (e.g., `myapp.api`, `myapp.infra`) only when `architecture-policy.yaml` targets subdirectory layers
- **Rust `use` import detection** — Extract `use crate::foo`, `use super::bar`, and grouped `use crate::{foo, bar::baz}` (expanded, no bare prefixes)
- **Rust graph resolution** — Best-effort crate discovery from `Cargo.toml` files, resolve cross-crate imports to local nodes
- **Synthetic target nodes** — Create nodes for unresolved import targets that match policy layer paths
- **Path-based layer matching** — Boundary violation detection now also matches nodes by path against policy patterns
- Line-comment filtering for Rust imports (`// use` not captured)

### Changed

- `_build_package_nodes` is language-aware: dispatches to TS/Rust/Python-specific node derivation
- `_build_edges` is language-aware: dispatches to TS/Rust/Python-specific import resolution
- `build_graph` precomputes TS packages, Rust crates, and policy state for node/edge construction

### Fixed

- FN-001: Ghostwire (314 imports, 0 edges -> 4 meaningful edges)
- FN-002: Craft-Agents (1162 imports, 0 edges -> 22 meaningful edges)
- FN-003: Symbiot/AIF (91 .rs files, 0 imports -> 51+ imports detected, 16+ edges in AIF)
- FN-004: validation-policy (boundary violation now correctly detected with policy-driven sub-package splitting)

### Tests

- 369 tests (52 new), 82.64% coverage
- New: `tests/test_scanner_rust.py` (Rust extraction, grouped expansion, comment filtering)
- New: `tests/test_grapher_ts.py` (TS monorepo nodes, workspace matching, prefix collision)
- New: `tests/test_grapher_rust.py` (Rust crate discovery, graph resolution)
- Updated: `tests/test_grapher.py` (Python sub-package policy tests)

## v0.5.1 — 2026-05-18

### Added

- TD-ARCH findings from `architecture-graph.json` cycles and boundary violations
- `ai-debt analyze --no-ai` reads architecture-graph.json when present
- Circular dependency findings with evidence-backed graph cycle IDs
- Boundary policy violation findings with policy rule and layer context
- Cap at 20 findings per type (cycles/violations) with limitation note
- Graceful skip when architecture-graph.json is absent

## v0.5.0 — 2026-05-18

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
