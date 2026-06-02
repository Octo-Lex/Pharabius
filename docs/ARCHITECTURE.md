# Pharabius Architecture

## Architecture Style

Pharabius v1 uses a modular monolith architecture.

The system runs as a local CLI and repository analysis engine. It produces `.ai-debt/` artifacts and does not modify production code by default.

## Current Layers

```text
CLI
 ↓
Core Runtime
 ↓
Schemas / Writers
 ↓
Repository-local Output Contract
```

## Allowed Dependencies

| Layer               | May Import                                                        |
| ------------------- | ----------------------------------------------------------------- |
| `pharabius.cli`     | `pharabius.core`, `pharabius.ai`                                  |
| `pharabius.core`    | `pharabius.schemas`, future `pharabius.writers`                   |
| `pharabius.ai`      | `pharabius.schemas`                                               |
| `pharabius.writers` | `pharabius.schemas`                                               |
| `pharabius.schemas` | Standard library, Pydantic                                        |

## Forbidden Dependencies

| Source              | Forbidden Target            |
| ------------------- | --------------------------- |
| `pharabius.schemas` | `pharabius.cli`             |
| `pharabius.schemas` | `pharabius.core` |
| `pharabius.core`    | `pharabius.cli`  |
| `pharabius.writers` | `pharabius.cli`  |
| `pharabius.writers` | `pharabius.core` |

## Architectural Rule

Lower-level modules must not depend on higher-level orchestration modules.

Schemas are the most stable layer and must remain free of runtime orchestration logic.

## Drift Prevention

Architecture compliance is enforced by:

```bash
lint-imports
```

The CI pipeline must fail if forbidden imports are introduced.

---

## AI Adapter Layer

**Layer:** Peer of `core/`, reads `.ai-debt/` artifacts, writes sidecar enrichment.

**Package:** `src/pharabius/ai/`
**Schemas:** `schemas/ai_enrichment.py`
**Command:** `ai-debt enrich`
**Output:** `.ai-debt/ai/` (sidecar only, not read by other commands)

### Modules

| Module | Responsibility |
|---|---|
| `ai/adapter.py` | `AIAdapter` interface, `AIResponse`, `DisabledAdapter` |
| `ai/mock_provider.py` | Deterministic mock provider for testing |
| `ai/context.py` | Bounded context assembly from `.ai-debt/` artifacts |
| `ai/validator.py` | Schema + ID validation, rejection records |
| `ai/enricher.py` | Orchestration: context → adapter → validation → sidecar |

### Key invariants

- AI enrichments are **sidecar records** — never mutate canonical artifacts
- AI output must reference **existing** finding IDs and evidence IDs
- Provider is **disabled by default** — no automatic data processing
- **No network calls** in v0.7.0 (mock provider only)
- Context assembly is **bounded** with budget controls
- `ai-debt enrich` is **NOT part of `ai-debt run`**

---

## Analysis Unit IR

**Layer:** Between Evidence IR and Finding IR.

**Schema:** `schemas/analysis_unit.py`
**Engine:** `core/mapper.py`
**Output:** `.ai-debt/analysis-units.json`
**Command:** `ai-debt map`

Analysis Units group raw evidence into engineering-meaningful areas:
packages, services, test suites, CI workflows, infrastructure, config surfaces,
documentation areas, and security-sensitive areas.

Each unit has a stable deterministic ID (`AU-{TYPE}-{HEX8}`) enabling cross-run comparison.

### Package vs Service distinction

A directory under `services/api` with `pyproject.toml` may create both:
- **package unit** — represents the dependency/build boundary (has a manifest)
- **service unit** — represents the deployable/operational/domain boundary (lives in a service directory)

These are intentionally separate concerns:
- package = "what dependencies does this code declare?"
- service = "what deployable component does this code belong to?"

### Evidence attachment specificity

Each unit type only claims evidence matching its type allowlist:

| Unit type | Allowed evidence types |
|---|---|
| package | manifest_detected, package_script_detected |
| service | manifest_detected, package_script_detected |
| cli | package_script_detected |
| test_suite | test_file_detected |
| documentation_area | documentation_file_detected |
| config_surface | configuration_file_detected |
| security_sensitive_area | risk_sensitive_path_detected, risk_sensitive_keyword_detected |
| ci_workflow | deployment_file_detected (CI paths) |
| infra_area | infrastructure_file_detected, deployment_file_detected |

### Security-sensitive area grouping

Security evidence is grouped by the nearest meaningful parent directory:
1. Package root (directory with a manifest)
2. Service root (directory under apps/, services/, etc.)
3. Top-level source directory (src/, lib/, cmd/, etc.)
4. Root (fallback)

Risk evidence under docs/, tests/, or cache directories is excluded from
security-sensitive unit creation.

### Zero-evidence filtering

Units with zero evidence IDs are removed from output after evidence attachment.

### Verifier module

`core/verifier.py` provides `ai-debt verify`:

1. Loads existing `debt-register.json` (source findings)
2. Loads current `evidence.json`
3. Optionally loads `analysis-units.json`
4. Runs `analyze_evidence()` in memory (no disk write)
5. Matches original findings to current findings using multi-criteria matching
6. Checks evidence, unit, and location existence
7. Assigns one of 6 verification statuses
8. Verifies work package linkage
9. Writes `verification-report.json` and `verification-report.md`

Matching priority: category + evidence overlap \u2192 category + locations \u2192 category + title \u2192 finding ID (weak)

Does NOT modify `debt-register.json` or any existing artifact.

### Status reader

`core/status_reader.py` provides `ai-debt status`:

- Read-only summary of `.ai-debt/` workspace state
- Does NOT run scan/analyze/verify
- Does NOT modify files
- Tolerates missing and corrupted artifacts

### Finding lifecycle

**Artifact roles:**

- `debt-register.json` = immutable snapshot of deterministic analyzer output
- `verification-report.json` = revalidation result against current repository state
- Work packages may become stale as findings evolve

### Export layer

`core/exporter.py` provides `ai-debt export`:

- Reads `debt-register.json` (required) and optional verification/units artifacts
- Writes SARIF v2.1.0, CSV, and JSONL to `.ai-debt/exports/`
- Does not create new findings or modify source artifacts
- Enriches exports with verification status and work package linkage when available

### Architecture graph layer

`core/grapher.py` provides `ai-debt graph`:

- Reads `evidence.json` (required) and optional analysis-units, project-profile, policy
- Builds package/module and analysis-unit dependency graph
- Detects cycles via Tarjan SCC (no new dependencies)
- Checks boundary violations against optional `architecture-policy.yaml`
- Computes coupling metrics (fan-in, fan-out, instability)
- Writes `.ai-debt/architecture-graph.json`
- Not part of `ai-debt run` pipeline (standalone command)
- Not exported by `ai-debt export`
- Does not parse `.importlinter`

### Architecture analyzer layer

`core/architecture_analyzer.py` generates TD-ARCH findings from graph IR:

- Reads `architecture-graph.json` (optional — gracefully skips if absent)
- Creates TD-ARCH findings for cycles with evidence (cap at 20)
- Creates TD-ARCH findings for boundary violations with evidence (cap at 20)
- Does not create findings from high-coupling metrics, unresolved, or external imports
- Integrated into `ai-debt analyze` via `analyzer.py`
- Returns finding specs; `analyzer.py` owns `FindingBuilder` (no circular imports)

**Finding states (current):**

- `Detected` (in `debt-register.json`)

**Verification statuses (in `verification-report.json`):**

| Status | Meaning |
|---|---|
| `still_detected` | Current analyzer confirms with supporting evidence |
| `likely_remediated` | No match, evidence gone, locations gone |
| `evidence_missing` | Evidence gone, cannot confirm remediation |
| `partially_supported` | Some evidence remains, support incomplete |
| `stale` | Structural mismatch (units, locations, or links drifted) |
| `uncertain` | Insufficient inputs for defensible result |

**Future concepts (NOT implemented):** `confirmed`, `accepted_risk`, `deferred`, `planned`, `false_positive`

**Key invariants:**

- `verify` does NOT mutate `debt-register.json`
- `verify` is NOT part of `ai-debt run`
- Verification is evidence-based, not proof of remediation

### Import contract

```
mapper imports from: schemas.analysis_unit, schemas.evidence, schemas.repository
mapper does NOT import from: analyzer, reporter, planner
```

### Pipeline order

```
init → profile → scan → map → analyze → report → plan
```

### Node derivation strategy

`ai-debt graph` creates architecture nodes from source files using this strategy:

1. **Python (src layout, no policy)**: Files under `src/<top_package>/` are grouped into a single package node named after the top-level package directory.
2. **Python (src layout, with policy)**: When `architecture-policy.yaml` targets subdirectory layers under `src/<pkg>/`, files are split into sub-package nodes (e.g., `myapp.api`, `myapp.infra`).
3. **TypeScript/JS monorepo**: When `package.json` files exist under `packages/*`, `apps/*`, `services/*`, `libs/*`, or `modules/*`, each becomes a separate package node named from the `package.json` `name` field.
4. **TypeScript/JS non-monorepo**: Files are grouped by the first directory level.
5. **Rust workspace**: When `Cargo.toml` files with `[package]` exist under `crates/*`, each becomes a separate module node named from the package name. Cross-crate imports resolved via kebab-to-snake name normalization.
6. **Other ecosystems**: First-level directory grouping.

**Synthetic target nodes**: When a Python import targets a sub-package that matches a policy layer path but has no source evidence, a synthetic node is created to enable boundary violation detection.

**Remaining limitations**: See KNOWN_LIMITATIONS.md items 38–39.

## Artifact ownership

Each CLI command produces specific `.ai-debt/` artifacts:

| Command | Artifacts |
|---|---|
| `init` | `config.yaml`, `README.md`, empty templates |
| `profile` | `project-profile.json` |
| `scan` | `evidence.json` |
| `map` | `analysis-units.json` |
| `graph` | `architecture-graph.json` |
| `analyze` | `debt-register.json`, `debt-register.md` |
| `report` | `architecture-map.md`, `dependency-health.md`, `test-health.md`, `security-exposure.md`, `business-risk-proxy.md`, `reports/foundation-audit-report.md` |
| `plan` | `remediation-roadmap.md`, `handoff-summary.md`, `work-packages/WP-*.md` |
| `run` | `runs/RUN-*.json` (metadata for full pipeline) |
| `export` | SARIF, CSV, JSONL exports (outside `.ai-debt/` by default) |
| `enrich` | `.ai-debt/ai/` sidecar files |
| `verify` | No files (read-only, console output) |
| `status` | No files (read-only, console output) |
| `ai-status` | No files (read-only, console output) |

**Config note:** `.ai-debt/config.yaml` is written by `init` and read by commands starting
in v0.11.0. `analysis.exclude_paths` and `analysis.max_file_size_kb` are authoritative.
CLI flags always override config values.

---

## Schema Compatibility Policy

**Canonical schemas** (everything in `schemas/` except `ai_enrichment.py`) follow
additive-only changes during v1.x where practical:
- Fields will not be removed or renamed without a migration note in CHANGELOG.md
- New optional fields may be added
- `schema_version` will be incremented if breaking changes are ever introduced
- All canonical JSON artifacts include `schema_version: "1.0"`

**AI sidecar schemas** (`schemas/ai_enrichment.py`) are optional/experimental and may
evolve independently. Sidecar output is never read by canonical commands.

**Derived/export schemas** (SARIF, CSV, JSONL) follow their respective external standards.
SARIF uses the SARIF 2.1.0 schema; JSONL and CSV are flat projections of finding data.

## Scanner Module Structure (v3.4.0)

The scanner was refactored in v3.4.0 from a monolithic 2048-line file into focused modules:

| Module | Responsibility | Public API |
|---|---|---|
| `core/scanner.py` | File iteration, evidence orchestration, file-level analysis | `scan_repository()`, `write_evidence_store()` |
| `core/io_helpers.py` | Shared `read_text()` and `read_json()` with error handling | `read_text()`, `read_json()` |
| `core/coverage_parsers.py` | Istanbul, Python coverage, LCOV, Cobertura, JaCoCo parsing | `scan_coverage_artifact()` |
| `core/dependency_parsers.py` | Manifest parsing, unpinned deps, lockfile consistency | `scan_dependency_manifest()`, `scan_repository_dependency_consistency()` |
| `core/runtime_parsers.py` | Runtime version pin detection (Python + Node.js) | `detect_runtime_version_pins()` |
| `core/constants.py` | Evidence types, thresholds, quality metadata constants | Constants only |
| `core/path_utils.py` | Path normalization and pattern matching utilities | `normalize_repo_path()`, `relative_repo_path()`, etc. |
| `core/dependency_utils.py` | PEP 508 / Poetry / Pipfile specifier classification | `classify_python_specifier()` |
| `core/run_history.py` | Run history snapshots, index, trend computation, rendering | `build_current_run_snapshot()`, `build_run_history_summary()` |
| `schemas/evidence.py` | `EvidenceStore`, `EvidenceItem`, `EvidenceLocation`, `EvidenceBuilder` | Data models + builder |

### Module dependency graph

```text
scanner.py
  ├── io_helpers.py
  ├── coverage_parsers.py ── io_helpers.py, schemas/evidence.py
  ├── dependency_parsers.py ── io_helpers.py, dependency_utils.py, schemas/evidence.py
  ├── runtime_parsers.py ── io_helpers.py, schemas/evidence.py
  ├── constants.py
  └── path_utils.py
```

---

## Implementation Status (v3.9.0)

| Capability | Status |
|---|---|
| Evidence-backed debt register | ✅ Implemented |
| TD-CODE detection (large files + debt markers) | ✅ Implemented (v3.1.0 repair) |
| TD-CODE detection (long functions + broad exceptions) | ✅ Implemented (v3.2.0) |
| Finding deduplication | ✅ Minimal deterministic (v3.1.0) |
| Work-package grouping | ✅ Conservative grouping (v3.1.0) |
| Operational claims with gap tracking | ✅ Implemented |
| Claims pipeline wired into `ai-debt run` | ✅ Implemented (v3.1.0) |
| Traceability matrices wired into `ai-debt run` | ✅ Implemented (v3.1.0) |
| Traceability quality metrics + grading | ✅ Implemented (v3.2.0) |
| Traceability quality trend (historical) | ✅ Implemented (v3.3.0) |
| Quality gate thresholds | ✅ Implemented |
| Review decision sidecar | ✅ Implemented |
| Trend trajectory analysis | ✅ Heuristic (not scientific) |
| AI enrichment (optional) | ✅ OpenAI-compatible adapter |
| Mock AI provider confidence fix | ✅ Fixed (v3.1.0) |
| Shared constants module | ✅ Implemented (v3.2.0) |
| Shared path normalization | ✅ Implemented (v3.3.0) |
| Shared I/O helpers | ✅ Implemented (v3.4.0) |
| `max_file_size_kb` enforcement | ✅ Implemented (v3.2.0) |
| Coverage ingestion (Istanbul/Python/LCOV) | ✅ Implemented (v3.2.0) |
| Coverage ingestion (Cobertura/JaCoCo) | ✅ Implemented (v3.3.0) |
| Coverage parser module | ✅ Extracted (v3.4.0) |
| Dependency health signals (unpinned + lockfile conflict) | ✅ Partial (v3.2.0: Node + Python req) |
| Dependency health signals (pyproject/Poetry/Pipfile) | ✅ Implemented (v3.3.0) |
| Dependency parser module | ✅ Extracted (v3.4.0) |
| Runtime version pinning (Python + Node) | ✅ Implemented (v3.3.0) |
| Runtime parser module | ✅ Extracted (v3.4.0) |
| Evidence system documentation | ✅ Implemented (v3.4.0) |
| TD-TEST low-coverage finding | ✅ Implemented (v3.2.0) |
| Scanner modularization (2048→1045 lines) | ✅ Complete (v3.4.0) |
| Run history intelligence (snapshots + trends) | ✅ Implemented (v3.5.0) |
| Finding trend by category | ✅ Implemented (v3.5.0) |
| Risk trend by category | ✅ Implemented (v3.5.0) |
| Evidence coverage trend | ✅ Implemented (v3.5.0) |
| Work-package readiness trend | ✅ Implemented (v3.5.0) |
| Run history documentation | ✅ Implemented (v3.5.0) |
| Benchmark validation & calibration | ✅ Implemented (v3.6.0) |
| Executable finding-quality rubric | ✅ Implemented (v3.6.0) |
| Threshold calibration (all kept) | ✅ Implemented (v3.6.0) |
| Validation documentation | ✅ Implemented (v3.6.0) |
| Advisory classification for structural signals | ✅ Implemented (v3.7.0) |
| OSS benchmark lane (3 pinned repos) | ✅ Implemented (v3.7.0) |
| Advisory severity cap (Low, risk ≤ 10) | ✅ Implemented (v3.7.0) |
| Planner/claims advisory exclusion | ✅ Implemented (v3.7.0) |
| Run history advisory tracking | ✅ Implemented (v3.7.0) |
| Classification-boundary warning | ✅ Implemented (v3.7.0) |
| Performance smoke test (1000-file repo) | ✅ Implemented (v3.7.0) |
| Runtime conflict detection (Python/Node) | ✅ Implemented (v3.8.0) |
| Ruby runtime pin evidence | ✅ Implemented (v3.8.0) |
| Java runtime pin evidence | ✅ Implemented (v3.8.0) |
| Dockerfile runtime evidence | ✅ Implemented (v3.8.0) |
| GitHub Actions runtime evidence | ✅ Implemented (v3.8.0) |
| Constraint kind model (exact/range/partial) | ✅ Implemented (v3.8.0) |
| Runtime reproducibility documentation | ✅ Implemented (v3.8.0) |
| Runtime package split (8 modules) | ✅ Implemented (v3.9.0) |
| RuntimeEvidence IR model | ✅ Implemented (v3.9.0) |
| RuntimeConstraint model (5 kinds) | ✅ Implemented (v3.9.0) |
| RuntimeConflictGroup model | ✅ Implemented (v3.9.0) |
| Centralized signal policy | ✅ Implemented (v3.9.0) |
| Runtime summary in history snapshot | ✅ Implemented (v3.9.0) |
| Schema-Budget Coupling | 📋 Design only |
| AST-based analysis | 🔜 Deferred |
| Dependency vulnerability scanning | 🔜 Deferred |
| Long-function detection for non-Python | 🔜 Deferred (JS/Go/Swift) |
| Runtime version conflict detection | 🔜 Deferred |
| Ruby/Java runtime pinning | 🔜 Deferred |
