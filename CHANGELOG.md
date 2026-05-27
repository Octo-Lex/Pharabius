# Changelog

All notable changes to Pharabius are documented in this file.

## [1.10.0] - Unreleased

### Added

- v1 artifact contract inventory (docs/ARTIFACT_CONTRACT.md)
- v1 schema map (docs/SCHEMA_MAP.md)
- End-to-end golden path validation (scripts/validate_golden_path.py)
- v1 readiness report generator (core/v1_readiness.py)
- CLI command reference (docs/CLI.md)
- Documentation index (docs/README.md)
- Quickstart guide (docs/QUICKSTART.md)

### Changed

- Improved CLI help-text consistency with safety language
- Improved documentation architecture and onboarding flow
- Consolidated v1 validation and release-readiness documentation

### Safety

- No new product capability added
- No scoring behavior changes
- No external APIs added
- No autonomous remediation added

## [1.9.1] - Unreleased

### Added

- Operational claim validation (structured error/warning result with cross-reference checks)
- Claim quality and completeness checks (complete/partial/needs_review per claim)
- Richer claims, gaps, questions, confidence, validation, completeness, and traceability examples
- Agent-handoff contract artifact (.ai-debt/agent-handoff-contract.md)
- Operational claims adoption guide (docs/OPERATIONAL_CLAIMS_ADOPTION.md)

### Safety

- Agent-handoff contract is a safety and context artifact, not implementation authority
- No production code is modified
- No autonomous remediation is introduced
- No canonical artifacts are mutated
- No external APIs are called

## [1.9.0] - Unreleased

### Added

- Operational Claim IR and claims register schema (10 claim types, 3 statuses, 3 confidence levels)
- Claim generation from debt-register findings with confirmed/inferred/gap status
- Gap and question registry artifacts (blocking vs non-blocking, 5 question categories)
- Confidence report with distribution metrics and interpretation notes
- Traceability matrices: evidence→finding, finding→claim, claim→work-package
- GapItem and QuestionItem schemas
- `docs/OPERATIONAL_CLAIMS.md` documentation and 7 example files

### Safety

- Operational claims are repository-local specification artifacts, not implementation authority
- Inferred claims and gaps are explicitly labeled
- No production code is modified
- No canonical artifacts are mutated
- No external APIs are called

## [1.8.0] - Unreleased

### Added

- Portfolio summary artifacts (schemas, aggregation, rollups, validation)
- Portfolio repository index with per-repo risk and category summaries
- Portfolio risk and category rollups (aggregate priority and category counts)
- Portfolio readiness and validation rollups (readiness status, ticket/export detection)
- `ai-debt portfolio` CLI command with `--repo` (repeatable) and `--output` options
- Portfolio documentation (`docs/PORTFOLIO.md`) and examples

### Safety

- No server, dashboard, scheduler, database, or remote repository crawling
- No external API calls
- No canonical debt register or work package mutation
- No scoring behavior changes

## [1.7.1] - Unreleased

### Added

- Export bundle manifest validation (missing manifest, invalid JSON, unsupported tracker, duplicate paths, missing artifact files, count mismatch)
- Tracker bundle completeness checks (complete/partial/needs_review) for all four trackers
- Export bundle summary report (`.ai-debt/reports/export-bundle-summary.md`)
- Tracker import workflow adoption guide (`docs/TRACKER_EXPORT_WORKFLOW.md`)
- Richer tracker-specific export examples for Jira, Linear, GitHub Issues, and Azure DevOps

### Changed

- Improved export-bundle documentation and examples
- Added completeness and validation sections to export bundle docs

### Safety

- No external tracker APIs are called
- No issues are created automatically
- No canonical debt register or work package artifacts are mutated

## [1.7.0] - Unreleased

### Added

- Export bundle artifact contract: `schemas/export_bundles.py` with `TrackerKind`, `ExportBundleFormat`, `ExportBundleManifest`
- Core export bundle module: `core/export_bundles.py` with path helpers and manifest writer
- Jira Markdown/CSV export bundle generator with safe CSV escaping
- Linear Markdown/CSV export bundle generator with conservative priority mapping
- GitHub Issues Markdown/YAML export bundle generator with per-issue YAML files
- Azure DevOps Markdown/CSV export bundle generator with semicolon-separated tags
- Export bundle documentation (`docs/EXPORT_BUNDLES.md`)
- Example export bundle artifacts (`docs/examples/export-bundles/`)

### Safety

- No external tracker API writes
- No issue or work-item creation
- No assignment, sprint, milestone, or area path handling
- All artifacts are repository-local handoff files
- No scoring behavior changes
- No canonical artifact mutation

## [1.6.1] - Unreleased

### Added

- Improved ticket draft summary report with generation summary, output artifacts, review decision summary, skipped items, validation issues, completeness counts, and field completeness warnings.
- Richer ticket draft examples demonstrating accepted, needs-investigation, deferred, and rejected work packages.
- Validation behavior for malformed or missing work packages (missing directory, empty directory, unreadable files, invalid IDs).
- Ticket draft field completeness checks (complete/partial/needs_review) with missing and weak field detection.
- Product Engineering Team ticket workflow adoption guide (`docs/PET_TICKET_WORKFLOW.md`).
- `TicketDraftValidationIssue` schema for tracking validation issues in ticket draft generation.
- `TicketDraftCompleteness` schema for field-level completeness assessment.

### Changed

- `generate_ticket_markdown_drafts` now returns `tuple[list[TicketDraft], list[TicketDraftValidationIssue]]` (was `list[TicketDraft]`).
- `generate_ticket_draft_index` accepts optional `validation_issues` parameter.
- `TicketDraft` schema gains optional `completeness` field.
- `TicketDraftIndex` schema gains `validation_issues` field.
- Summary report renderer adds structured sections replacing flat metrics table.

### Safety

- No changes to scoring behavior.
- No changes to canonical debt register behavior.
- No external ticketing API writes.
- No autonomous remediation.

## [1.6.0] - Unreleased

### Added

- Repository-local ticket draft export via `ai-debt tickets` command
- Markdown ticket drafts under `.ai-debt/ticket-drafts/` (one per work package)
- Machine-readable `ticket-drafts.json` index with metadata and content hashes
- Ticket draft summary report at `.ai-debt/reports/ticket-draft-summary.md`
- PET review sidecar filtering: false-positive, rejected, and deferred excluded by default
- `--include-deferred` flag to include deferred-only work packages
- `--force` flag to overwrite existing generated drafts
- Ticket draft schema models (TicketDraft, TicketDraftIndex) in `schemas/tickets.py`
- Deterministic ticket ID mapping (WP-001 → TICKET-WP-001)

### Safety

- No external tickets are created
- No issue tracker APIs are called
- Canonical debt register and work packages are not mutated
- Review sidecar decisions affect inclusion only, not scoring

### Stats

- 1078 tests (+82 from v1.5.1)
- 52 source files (+2 from v1.5.1)

## [1.5.1] - Unreleased

### Added

- Scoring evidence pack format and examples (docs/SCORING_EVIDENCE_PACK.md)
- Field validation summary script (scripts/validate_v151_scoring_calibration.py)
- Calibration fixtures for architecture centrality and change frequency thresholds
  (14 boundary cases, 25 calibration tests)
- Scoring delta Markdown report with structured sections: Configuration, Summary,
  Priority Movement, Changed Findings, Factor Details, Warnings, Reviewer Notes

### Improved

- --scoring-preview now emits both scoring-preview.json and scoring-delta.md
- scoring-delta.md readability with clearer summary, priority movement,
  factor provenance, and warning sections

### Validation

- Enhanced scoring validation produces machine-readable and human-readable evidence packs
- Preview-mode non-mutation, finding ID stability, evidence ID stability,
  and reset/default behavior are validated by tooling
- Calibration decision: no threshold changes in v1.5.1 (evidence did not justify tuning)

### Compatibility

- Enhanced scoring remains opt-in
- Default scoring remains unchanged when enhanced scoring is disabled
- No threshold changes from v1.5.0
- No scoring algorithm changes

### Stats

- 996 tests (+64 from v1.5.0)
- 100 files tracked

## [1.5.0] - Released 2026-05-22

### Added

- Opt-in enhanced risk scoring with architecture centrality and git change frequency
- --enhanced-scoring / --no-enhanced-scoring CLI flags on analyze
- --scoring-preview for non-mutating sidecar projection
- Architecture centrality from architecture-graph.json (fan-in, cycle, hub detection)
- Change frequency from local git log (commit counts per path)
- Factor scale: Low=1, Medium=3, High=5, Critical=8 (reserved)
- Provenance per finding: level, value, source, reason
- risk_scoring config section in config.yaml (not governance.yaml)
- Performance controls: git/graph timeouts, commit/path caps
- Scoring preview sidecar: .ai-debt/reports/scoring-preview.json
- 24 new scoring tests

### Changed

- _score() in analyzer tolerates mixed-type risk_breakdown dicts

### Not Changed

- Default behavior identical to v1.4.0 (enhanced=false)
- No analyzer rule, provider, governance, or review changes

## [1.4.0] - Released 2026-05-20

### Added

- `ai-debt review` command for non-canonical PET review decisions
  - `--init`: create empty `.ai-debt/review/decisions.json` sidecar
  - `--status`: read-only summary of decisions vs findings
  - `--validate`: validate decisions against debt-register
- `schemas/review.py` — ReviewDecision, ReviewDecisions, ReviewValidationResult, ReviewSummary
- `core/review.py` — loader, validator, summarizer, init
- 7 allowed decision statuses: accepted, rejected, deferred, needs-investigation, duplicate, already-fixed, risk-accepted
- Unknown finding IDs: warning (not error)
- Duplicate finding IDs: first kept + warning
- Invalid statuses: hard validation error
- Stale decisions (finding removed) detected
- Canonical JSON hashes unchanged after all review operations

### Changed

- Version bumped to 1.4.0
- CLI command count: 15 (was 14)

### Not Changed

- No analyzer behavior changes
- No provider behavior changes
- No config/governance behavior changes
- No finding generation changes
- No schema changes to existing schemas
- No remediation/code modification behavior
- No AI-generated canonical findings
- No run/enrich integration

## [1.3.0] - Released 2026-05-20

### Added

- Differentiated governance presets with real Markdown template files:
  - `security-sensitive` — security review sections, sign-off, credential
    caution, escalation guide, compliance emphasis
  - `startup-lean` — condensed work packages, action-oriented handoff,
    minimal verbosity while preserving evidence/actions/verifications
  - `platform-engineering` — platform impact assessment, dependency/ops
    emphasis, operational readiness language
  - `compliance-sensitive` — attestation notice, audit trail, compliance
    escalation guide, regulatory review checklist
- 50 new preset differentiation tests
- Each preset provides 3 template files (work-package, handoff, roadmap)

### Changed

- Version bumped to 1.3.0
- Template engine maps hyphenated preset names to underscored directories

### Not Changed

- Default preset uses built-in rendering (unchanged from v1.2.1)
- No engine/analyzer/provider/config behavior changes
- No canonical JSON schema changes
- No finding generation changes
- No severity/priority changes
- No evidence ID changes

## [1.2.1] - 2026-05-20

### Fixed

- Hardened template override path handling — `override_dir` paths that escape
  the repository root are now rejected with a clear warning
- Reduced `TEMPLATEABLE_ARTIFACTS` to the 3 shipped artifacts
  (work-package, handoff, roadmap); debt-register and foundation-audit-report
  are explicitly deferred

### Added

- 24 new governance hardening tests (path safety, binary/empty template
  fallback, override precedence, canonical immutability, warning clarity)
- Field validation on Pharabius, validation-java, validation-empty

### Changed

- Version bumped to 1.2.1

### Not Changed

- No engine/analyzer/provider/config behavior changes
- No new templateable artifacts
- No full non-default preset templates
- No canonical JSON schema changes
- No finding generation changes

## [1.2.0] - 2026-05-20

### Summary

Pharabius v1.0.0 is the first stable release. This is a version-only bump from
v1.0.0rc1 with documentation updates. No source code, schema, command, provider,
or config behavior changes.

The v1 product surface was frozen at v1.0.0rc1 and validated across 8 repositories
with zero P0 or P1 blockers found.

### RC Validation Summary

- 8 repositories validated (Python, Java, .NET, Terraform, Rust, TypeScript, empty)
- 112/112 command executions passed (14 commands × 8 repos)
- P0 blockers: 0
- P1 blockers: 0
- 731 tests, 85.07% coverage
- All 7 local gates passed
- GitHub CI passed
- Deterministic runs verified on Pharabius and validation-java
- Install/package audit passed
- Provider safety verified (canonical immutability proven via hash)
- Config safety verified
- False positive review: zero false positives across all repos
- Zero feature additions since RC

### P2 Items Accepted for v1.1

- Sample output gallery
- `--version` CLI flag
- Full graph/git-backed risk scoring (`architecture_centrality`, `change_frequency`)
- Governance presets and template overrides
- Git history analysis, incremental mode, IDE integrations

### Changed

- Version bumped from `1.0.0rc1` to `1.0.0`
- CHANGELOG.md updated with v1.0.0 final section
- KNOWN_LIMITATIONS.md header updated to v1.0.0
- ROADMAP.md updated with v1.0.0 final entry

### Not Changed

- No source code changes
- No schema changes
- No command changes
- No provider changes
- No config behavior changes
- No new tests

## [1.0.0rc1] - 2026-05-19

### Changed

- Version bumped to `1.0.0rc1` (release candidate)
- `RunMetadata` now includes `schema_version: "1.0"` in run JSON
- `RunMetadata.tool_version` now reads from installed package metadata (was hardcoded `"0.1.0"`)

### Documentation

- Fixed KNOWN_LIMITATIONS.md header version (was incorrectly `v0.2.1`)
- Updated ROADMAP.md to show v0.11.0 as released
- Updated V1_READINESS_AUDIT.md to reflect v0.11.0 state
- Added schema compatibility policy to ARCHITECTURE.md
- Updated command count to 14 in all documentation

### Validation

- 9-repository field validation matrix executed
- Full workflow validated (all 14 commands)
- Install/packaging audit completed
- Provider safety audit completed (15 checks)
- Config runtime audit completed (12 checks)
- `.ai-debt/` contract freeze verified

### Notes

- This is a release candidate. Not production-ready until v1.0.0 final.
- No feature additions, no new providers, no new taxonomy categories.
- Risk scoring gaps documented as v1.1 follow-up.

## [0.11.0] - 2026-05-19

### Added

- Config runtime: `.ai-debt/config.yaml` is now read by commands
- New `src/pharabius/schemas/config.py` — Pydantic config model with safe defaults
- New `src/pharabius/core/config.py` — config loader with warning behavior
- `scan` command reads `analysis.exclude_paths` from config (supplements hardcoded exclusions)
- `scan` command reads `analysis.max_file_size_kb` from config
- Malformed config produces clear warning + safe defaults
- Unknown config keys produce clear warning + ignored
- Missing config uses safe defaults (no warning)
- CLI flags always override config values
- 20 config tests: model, loader, integration, provider safety

### Fixed

- Config path matching bug: `.git` exclusion no longer incorrectly matches `.github/`

### Changed

- `scan_repository()` accepts optional `extra_exclude_paths` and `max_file_size_kb` params
- `write_evidence_store()` passes config-derived settings to scanner

### Documentation

- Updated KNOWN_LIMITATIONS.md #65: config is now read by commands
- Updated ARCHITECTURE.md with config runtime architecture
- Updated V1_READINESS_AUDIT.md with config runtime status

### Tests

- 729 tests (20 new), 85%+ coverage

## [0.10.1] - Unreleased

### Changed

- Fixed `config.yaml` defaults: `ai.enabled: false`, `ai.provider: "disabled"`, removed `model: "auto"` and `allow_business_inference`
- Previous config had `enabled: true` / `provider: "auto"` which contradicted actual CLI defaults
- Config is still written but not read — no command behavior changes

### Added

- 8 config default tests verifying safe defaults, no secrets, blueprint priority bands
- 10 first-run smoke tests covering the full CLI workflow on a tiny fixture repo
- `docs/V1_READINESS_AUDIT.md` — v1 readiness audit documenting config, risk scoring, contract, and readability
- Artifact ownership table in `docs/ARCHITECTURE.md`
- Risk scoring comment in `analyzer.py` documenting 2 unused factors

### Documentation

- Updated `KNOWN_LIMITATIONS.md` #65: config is written but not read
- Updated `KNOWN_LIMITATIONS.md` #66: clarified which 2 risk factors are unused

### Tests

- 709 tests (18 new), 84%+ coverage

## [0.10.0] - Unreleased

### Added

- 7 new deterministic analysis rules completing the 14-category taxonomy:
  - **TD-CODE**: Large source files (>1000 lines), accumulated debt markers (TODO/FIXME/HACK)
  - **TD-COMP**: Potential compliance exposure (PII, GDPR, HIPAA, PCI, audit, retention)
  - **TD-OPS**: Deployment files without healthcheck/rollback indicators
  - **TD-DATA**: Schema migrations without rollback/down evidence
  - **TD-PERF**: Synchronous/blocking patterns near risk-sensitive areas
  - **TD-OBS**: Deployment without observability (logging/monitoring/tracing) evidence
  - **TD-PROCESS**: Missing repository process artifacts (CODEOWNERS, CONTRIBUTING, PR templates)
- All new rules are evidence-backed: no evidence → no finding
- Conservative severity: new categories default to Medium/Low severity
- All new findings use "inferred" language for business impact

### Tests

- 657 tests (28 new), 84%+ coverage
- 28 taxonomy closure tests covering all 7 new categories
- Negative tests: no evidence → no finding for each category
- Existing category stability verified

## [0.9.1] - Unreleased

### Added

- Selected-finding boundary enforcement: enrichments for unselected findings are rejected
- Duplicate enrichment detection: first valid enrichment kept, duplicates rejected
- Output budget enforcement: provider output exceeding `max_output_chars` rejected before parsing
- `AIUsageSummary` extended with `latency_ms`, `request_id`, `provider_error_code`
- Sidecar markdown shows token usage, latency, request ID when non-zero
- `ai-status` shows token usage, latency, provider error code when present
- Provider error messages improved: timeout suggests `--timeout-seconds`, rate-limit suggests waiting, network error includes base URL
- Consent message improved with numbered steps and "No data was sent" reassurance
- Privacy caution updated to reflect external provider capability
- 5 credential redaction tests with sentinel-based leak detection
- 27 provider variability tests (response format, boundary, budget, errors)
- `scripts/manual_provider_smoke.py` — optional manual smoke validation script
- `docs/templates/provider-smoke-result.md` — smoke result template

### Changed

- `enrich_findings()` passes selected finding IDs (not all register IDs) to validator
- `validate_raw_output()` detects and rejects duplicate finding ID enrichments
- Provider output exceeding `AIBudget.max_output_chars` rejected without parsing

### Tests

- 629 tests (32 new), 83%+ coverage
- All tests use MockTransport — no real network in CI

## [0.9.0] - Unreleased

### Added

- First real provider: `openai-compatible` adapter for any endpoint implementing the expected OpenAI-compatible `/v1/chat/completions` request and response shape
- Optional dependency: `pip install "pharabius[openai-compatible]"` (adds `httpx`)
- `--allow-external-provider` consent flag required before any external provider call
- `--model` flag for provider model selection (required for openai-compatible if `PHARABIUS_OPENAI_MODEL` not set)
- `--timeout-seconds` flag for provider call timeout
- Credential handling from `PHARABIUS_OPENAI_API_KEY` environment variable only
- `PHARABIUS_OPENAI_BASE_URL` for endpoint configuration (default: `https://api.openai.com`)
- Provider error mapping: auth_failed, rate_limit, timeout, server_error, content_filter, network_error
- Token usage captured from provider responses
- Request ID and latency captured from provider responses

### Security

- Consent gate at CLI level: provider module never imported without `--allow-external-provider`
- No credentials in sidecars, logs, or error messages
- No `.env` loading, no config file, no credential storage
- `--context-preview` works without credentials or consent

### Tests

- 597 tests (32 new), 83.88% coverage
- OpenAI-compatible adapter tests: 22 tests with `httpx.MockTransport` (no real network)
- CLI consent tests: 10 tests for consent gate, context preview, credential safety
- Regression tests: 3 tests confirming unchanged behavior

## [0.8.0] - Unreleased

### Added

- `ai-debt enrich --context-preview` — preview bounded context without calling any provider or writing files
- Provider interface hardening: `AIResponse` gains `request_id`, `latency_ms`, `response_truncated`, `provider_error_code`, `provider_error_message`
- `AIUsageSummary` gains `prompt_tokens`, `completion_tokens`, `total_tokens`, `estimated_cost`
- `AIBudget` gains `provider_timeout_seconds`, `max_provider_retries`
- `AIAdapter.generate_json` accepts `timeout_seconds` keyword parameter
- Provider simulation tests: 14 tests covering timeout, rate-limit, auth failure, malformed JSON, markdown-fenced JSON, partial JSON, JSON with comments, content filter, truncated output, empty response, mixed batch
- Context preview tests: 17 tests covering CLI and unit behavior
- Improved unknown provider error message: references v0.8.0 and lists available providers

### Changed

- Unknown provider error now reads: `Provider '<name>' is not available in v0.8.0. Available providers: disabled, mock.`
- Provider-level errors (timeout, rate-limit, auth, content filter) now produce rejection records instead of crashing

### Documentation

- Provider readiness checklist (25 criteria)
- Prompt contract requirements for future providers
- Future credential policy: environment variables only, no repository files
- Future external-provider consent requirement documented
- Strict JSON requirement: markdown-fenced, comments, and partial JSON are rejected

### Tests

- 565 tests (36 new), 84.02% coverage
- Provider simulation tests: 14 tests for failure modes
- Context preview tests: 17 tests for --context-preview flag
- AIResponse/AIUsageSummary field tests: 5 tests for new fields
- Unknown provider message tests: 2 tests

## [0.7.2]

### Added

- `ai-debt ai-status` — read-only command that summarizes AI sidecar state
- `ai-debt ai-status --json` — machine-readable JSON output
- `src/pharabius/ai/status_reader.py` — sidecar status reader (in `ai/` package, preserving core boundary)
- Sidecar markdown improvements: summary table, review checklist, deterministic ordering
- Sidecar enrichments sorted by `finding_id` alphabetically
- Sidecar evidence IDs sorted alphabetically within each enrichment
- Sidecar rejections sorted by `finding_id` (unknown last) with heading format
- Sidecar rejection entries now include invalid fields, missing evidence IDs, and hash

### Changed

- Sidecar markdown now uses `## Summary` table instead of flat list
- Sidecar markdown now embeds review checklist before footer
- Sidecar rejections use `###` headings instead of bullet points for readability
- Privacy version string updated from v0.7.1 to v0.7.2

### Tests

- 529 tests (38 new), 83.33% coverage
- New status reader tests: 16 tests for read_ai_status and SidecarStatus
- New CLI ai-status tests: 10 tests for command behavior
- New markdown UX tests: 9 tests for summary table, checklist, ordering, diffability
- New regression tests: 5 tests confirming existing behavior unchanged

## [0.7.1]

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
