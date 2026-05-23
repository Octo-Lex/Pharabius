# Pharabius Roadmap

## v1.9.0 — Operational Claims & Gap Registry (unreleased)

- Operational claim IR and claims register schema
- Claim generation from evidence and findings
- Gap and question registry artifacts
- Confidence report and claim distribution metrics
- Traceability matrices (evidence→finding→claim→work package)
- Operational claims documentation and examples
- 75 new tests
- No code modification, no external APIs

## v1.8.0 — Portfolio Summary Foundation (unreleased)

- Portfolio summary schemas and artifact contract
- Repository summary aggregation from `.ai-debt/` outputs
- Portfolio risk and category rollups
- Portfolio readiness and validation rollups
- `ai-debt portfolio` CLI command
- Portfolio documentation and examples
- 69 new tests
- No server, dashboard, or remote crawling

## v1.7.1 — Export Bundle Polish & Validation (unreleased)

- Export bundle manifest validation (8 rules)
- Tracker bundle completeness checks (complete/partial/needs_review)
- Export bundle summary report
- Tracker import workflow adoption guide
- Richer tracker-specific examples (Jira, Linear, GitHub Issues, Azure DevOps)
- 48 new tests
- No external tracker API writes

## v1.7.0 — Export Bundle & External Tracker Preparation (unreleased)

- Export bundle artifact contract (manifest, tracker enum, format enum)
- Jira Markdown/CSV export bundle generator
- Linear Markdown/CSV export bundle generator with priority mapping
- GitHub Issues Markdown/YAML export bundle generator with per-issue YAML
- Azure DevOps Markdown/CSV export bundle generator with semicolon tags
- Export bundle documentation and examples
- 96 new tests
- No external tracker API writes

## v1.6.1 — Ticket Draft Polish & Adoption Pack (unreleased)

- Improved ticket draft summary report with structured sections
- Richer ticket draft examples (4 work package scenarios)
- Validation for malformed or missing work packages
- Ticket draft field completeness checks (complete/partial/needs_review)
- PET ticket workflow adoption guide
- 39 new tests

## v1.6.0 — Ticket Draft Export (released)

- Repository-local ticket drafts from work packages
- `ai-debt tickets` CLI command
- Markdown drafts + JSON index + summary report
- PET review sidecar filtering
- No external tracker writes
- 82 new tests

## v1.5.1 — Scoring Calibration & Evidence Pack (released 2026-05-22)

- Evidence pack format, fixtures, and field validation tooling
- Scoring delta Markdown readability improvements
- Calibration decision: no threshold changes (evidence did not justify tuning)
- 64 new tests (14 evidence pack + 15 delta report + 25 calibration + 10 validation)
- No scoring algorithm, threshold, or production behavior changes

## v1.5.0 — Opt-in Enhanced Risk Scoring (released 2026-05-22)

- Architecture centrality from existing graph
- Change frequency from local git log
- Opt-in via config or CLI flags
- Scoring preview for evaluation
- 24 new tests
- No engine/analyzer-rule/provider/config/governance/review behavior changes

## v1.4.0 — Review Decision Sidecar (released 2026-05-20)

- `ai-debt review` command with --init/--status/--validate
- Non-canonical PET review decision sidecar
- 7 allowed statuses, validation, stale detection
- 49 new tests
- No engine/analyzer/provider/config behavior changes

## v1.3.0 — Differentiated Governance Presets (released 2026-05-20)

- 4 differentiated presets with real Markdown templates
- security-sensitive, startup-lean, platform-engineering, compliance-sensitive
- 50 new preset tests
- No engine/analyzer/provider/config behavior changes

## v1.2.1 — Governance Field Validation & Template Hardening (released 2026-05-20)

- Path safety hardening for template override_dir
- 24 new governance hardening tests
- Field validation on Pharabius, validation-java, validation-empty
- No engine/analyzer/provider/config behavior changes

## v1.2.0 — Governance Presets and Template Overrides (released 2026-05-20)

- `.ai-debt/governance.yaml` — controls Markdown presentation and handoff policy
- Project-local template overrides via `.ai-debt/templates/`
- Bundled `default` preset
- Safe template engine with `{{ placeholder }}` substitution
- Governance documentation, preset reference, template override guide
- No engine/analyzer/provider/config behavior changes

## v1.1.0 — Adoption Polish (released 2026-05-20)

- `ai-debt --version` flag
- `docs/SAMPLE_OUTPUT.md` — curated output snippets
- `docs/ADOPTION_GUIDE.md` — PET adoption workflow
- No engine changes

## v1.0.0 — First Stable Release (released 2026-05-20)

- First stable v1 release
- Version bump from v1.0.0rc1 with documentation updates only
- 14 CLI commands, 14 taxonomy categories, complete `.ai-debt/` handoff contract
- RC validation: 8 repos, 112/112 commands passed, 0 P0/P1 blockers
- 731 tests, 85.07% coverage
- No source code changes from RC

## v1.0.0rc1 — Release Candidate (released 2026-05-19)

- Version bumped to 1.0.0rc1
- RunMetadata schema_version and tool_version fixes
- Schema compatibility policy documented
- P1 doc fixes (ROADMAP, KNOWN_LIMITATIONS, V1_READINESS_AUDIT)
- 9-repo validation matrix, install audit, provider/config safety audits

## v0.5.1 — TD-ARCH Finding Integration (released 2026-05-18)

- TD-ARCH findings from architecture-graph.json cycles and boundary violations
- `ai-debt analyze --no-ai` reads graph when present, skips gracefully when absent
- Circular dependency findings with graph cycle IDs
- Boundary policy violation findings with policy context
- Cap at 20 findings per type
- 317 tests passing, 84% coverage

## v0.5.0 — Architecture Graph IR (released 2026-05-18)

- `ai-debt graph` — Build import dependency graph from existing evidence
- Package/module and analysis-unit node derivation
- Tarjan SCC cycle detection (no new dependencies)
- Optional boundary policy via `.ai-debt/architecture-policy.yaml`
- Coupling metrics: fan-in, fan-out, instability
- Deterministic stable IDs
- Graph IR only — no TD-ARCH findings
- 282 tests passing, 84% coverage

## v0.4.0 — Export Formats (released 2026-05-18)

- `ai-debt export` — SARIF v2.1.0, CSV, JSONL output formats
- SARIF for GitHub Security / VS Code integration
- CSV for spreadsheet triage
- JSONL for CI/CD gates and custom tooling
- Verification status and work package enrichment
- 219 tests passing, 86% coverage

## v0.3.2 — Field-Validation Bug Fixes (released 2026-05-18)

- .NET manifest detection: `.csproj`, `.fsproj`, `.vbproj` produce evidence
- .NET dependency findings for projects without `packages.lock.json`
- Java Maven parent/library POM false positives eliminated
- CI/deployment keyword false positives suppressed
- Terraform `.terraform.lock.hcl` evidence detection
- 195 tests passing, 87% coverage

## v0.3.1 — Stabilization & Verification UX (released 2026-05-17)

## v0.3.0 — Finding Verification (released 2026-05-17)

- `ai-debt verify` — Revalidate findings against current evidence
- 6 verification statuses: `still_detected`, `likely_remediated`, `evidence_missing`, `partially_supported`, `stale`, `uncertain`
- Location verification (file path existence)
- Structured work package verification
- Deterministic matching (category + evidence overlap, locations, title)

## v0.2.0 — Analysis Unit IR (released 2026-05-17)

- `ai-debt map` — Map repository evidence into analysis units
- 9 analysis unit types with deterministic `AU-*` IDs
- Finding-to-unit linkage via `analysis_unit_ids`
- Trust-boundary tags for security-sensitive areas
- Noise reduction: type-specific evidence, security grouping, cache filtering

## v0.2.1 — Maintenance (released 2026-05-17)

- Documentation correctness (phantom limitations, version metadata)
- GitHub Actions maintenance (Node.js 24 compatibility)
- Developer audit helper for analysis units

## v0.4.0 — Export & Connectors (planned)

- `ai-debt export --format sarif` — SARIF output for GitHub Security tab integration
- `ai-debt export --format csv` — CSV output for spreadsheet analysis and reporting
- Coverage report ingestion (pytest-cov XML, Istanbul/NYC JSON, Go coverage)
- Static-analysis evidence connector (Semgrep, ruff audit mode)
- Import graph analysis (coupling metrics, circular dependency detection)

## v0.5.2 — Architecture Graph Field Validation (2026-05-18)

- 11-repository validation of architecture graph and TD-ARCH findings
- 4 false negatives documented (FN-001 through FN-004)
- 0 false positives across all repos
- Node derivation strategy documented
- Backlog created for v0.6.0 graph improvements

## v0.6.0 — Architecture Graph Enhancements (upcoming)

- TS/JS monorepo package-node splitting (`packages/*`, `apps/*`) — fixes FN-001, FN-002
- Python policy-driven sub-package granularity — fixes FN-004
- Rust `use` import detection with grouped expansion — fixes FN-003
- TS workspace import longest-prefix matching
- Synthetic target nodes for policy-matched imports
- Path-based layer matching for boundary violations

## v0.6.1 — Rust Workspace Graph Completion (upcoming)

- Rust `crates/*` node splitting from Cargo.toml discovery
- Kebab→snake crate name normalization for import resolution
- Synthetic target nodes for imports matching discovered crates
- FN-003 completed: Symbiot now produces cross-crate edges

## v0.7.0 — Evidence-Constrained AI Adapter (released 2026-05-19)

- `ai-debt enrich` command — provider-neutral AI enrichment
- Provider interface with mock and disabled modes
- Strict schema validation (Pydantic, extra fields forbidden)
- Bounded context assembly with budget controls
- Evidence ID and finding ID validation
- Sidecar output contract: `.ai-debt/ai/`
- No canonical artifact mutation
- No real network provider in v0.7.x
- AI disabled by default

## v0.7.1 — AI Adapter Stabilization (released 2026-05-19)

- Rejection test hardening (54 new tests)
- Empty evidence_ids rejected
- Unknown --finding-id fails clearly
- Sidecar markdown privacy caution and timestamp
- Context assembly stress tests
- Canonical immutability across all modes
- CLI integration tests for enrich
- Import boundary and privacy checks

## v0.7.2 — AI Sidecar UX & Review Workflow (released 2026-05-19)

- `ai-debt ai-status` — read-only sidecar status summary
- `ai-debt ai-status --json` — machine-readable output
- Sidecar markdown summary table, review checklist, deterministic ordering
- Sidecar enrichments sorted by finding_id
- Sidecar evidence IDs sorted alphabetically
- Sidecar rejections with headings, invalid fields, hashes
- Sidecar review workflow documented
- Privacy and sharing guidance

## v0.8.0 — Provider Interface Readiness (released 2026-05-19)

- `ai-debt enrich --context-preview` — preview bounded context without calling provider
- Provider interface hardening: structured error fields in `AIResponse`
- Token/cost fields in `AIUsageSummary`
- Provider timeout/retry fields in `AIBudget`
- Provider simulation tests: 14 failure modes
- Improved unknown provider error message
- Provider readiness checklist (25 criteria audited)
- Prompt contract and credential policy documented
- No real provider — readiness only

## v0.9.0 — First Real Provider Adapter (released 2026-05-19)

- First real provider: `openai-compatible` adapter
- Optional dependency: `pip install "pharabius[openai-compatible]"`
- `--allow-external-provider` consent flag
- `--model` flag for provider model selection
- `--timeout-seconds` flag for provider timeout
- Credential handling from environment variables only
- Provider error mapping: auth, rate-limit, timeout, content filter, network
- Token usage and latency captured
- No real network in CI — all tests use mock transport

## v0.9.1 — Real Provider Safety & Manual Smoke Validation (released 2026-05-19)

- Selected-finding boundary enforcement
- Duplicate enrichment detection
- Output budget enforcement
- Provider telemetry in sidecar/status
- Credential redaction tests
- 27 provider variability tests
- Optional manual smoke script
- Privacy caution updated

## v0.10.0 — Taxonomy Closure & v1 Readiness (released 2026-05-19)

- 7 new analysis rules: TD-CODE, TD-COMP, TD-OPS, TD-DATA, TD-PERF, TD-OBS, TD-PROCESS
- Full 14/14 taxonomy coverage
- Evidence-backed findings only
- Conservative severity defaults
- False positive suppression for scanner/docs/test keyword noise
- CI-only workflow suppression for TD-OPS/TD-OBS
- Directory-structure matching for TD-DATA (no broad "schema" matching)

## v0.10.1 — v1 Readiness Audit (released 2026-05-19)

- Config defaults fixed (safe, accurate)
- First-run smoke tests
- Risk scoring audit documented
- `.ai-debt/` contract audit
- Report readability audit
- Artifact ownership documented

## v0.11.0 — Config Runtime (released 2026-05-19)

- Config.yaml now read by commands
- `exclude_paths` and `max_file_size_kb` configurable
- Safe defaults, malformed config warning, unknown key warning
- CLI flags override config
- No credentials in config, no provider consent bypass

## Future (v1.1+)

- `--version` CLI flag
- Sample output gallery (`docs/SAMPLE_OUTPUT.md`)
- Full graph/git-backed risk scoring (`architecture_centrality`, `change_frequency`)
- Governance presets and template overrides
- Report integration for AI enrichments
- Git history analysis (change frequency, hotspots, churn metrics)
- Incremental analysis mode
- IDE plugin integration (VS Code, JetBrains)
- CI/CD gate mode (exit non-zero when new debt is introduced)
- Dependency freshness and deprecation tracking
- Architecture decision record (ADR) generation from findings
- Multi-repository comparison and portfolio-level dashboards
- Jira/GitHub Issues export
