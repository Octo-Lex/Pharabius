# Pharabius Roadmap

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

## v0.9.1 — Real Provider Safety & Manual Smoke Validation (unreleased)

- Selected-finding boundary enforcement
- Duplicate enrichment detection
- Output budget enforcement
- Provider telemetry in sidecar/status
- Credential redaction tests
- 27 provider variability tests
- Optional manual smoke script
- Privacy caution updated

## Future (v0.10.x+)

- Real provider integration (OpenAI, Claude, or local model)
- Report integration for AI enrichments
- Configuration file for AI settings
- `--apply-enrichment` flag for merging validated enrichments
- Block-comment filtering for Rust imports
- Test-scope edge confidence reduction
- Non-standard monorepo layout support

## Future Considerations

- Git history analysis (change frequency, hotspots, churn metrics)
- Multi-repository comparison and portfolio-level dashboards
- IDE plugin integration (VS Code, JetBrains)
- CI/CD gate mode (exit non-zero when new debt is introduced)
- Dependency freshness and deprecation tracking
- Architecture decision record (ADR) generation from findings
