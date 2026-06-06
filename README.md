# Pharabius

Pharabius is a repository-first technical debt intelligence platform.

**Current public baseline: v3.0.0**

It analyzes repositories and produces evidence-backed technical debt reports, remediation roadmaps, and engineering handoff packages. It does not modify production code by default.

Internal development waves through v3.26.0 are consolidated in this release. See `docs/PUBLIC_SYNC_NOTES.md` for the full sync narrative.

## Quick Start

```bash
pip install -e .
ai-debt --version         # Show installed version
ai-debt init              # Create .ai-debt workspace
ai-debt scan              # Collect normalized evidence
ai-debt analyze --no-ai   # Generate deterministic debt findings
ai-debt report            # Generate domain reports
ai-debt export            # Export findings to SARIF, CSV, JSONL, Governance
```

## Commands

```bash
ai-debt --version         # Show installed version
ai-debt init              # Create .ai-debt workspace
ai-debt profile           # Detect repository stack and structure
ai-debt scan              # Collect normalized evidence
ai-debt map               # Map evidence into analysis units
ai-debt analyze --no-ai   # Generate deterministic debt findings
ai-debt report            # Generate domain reports
ai-debt plan              # Generate roadmap, work packages, and handoff
ai-debt verify            # Verify findings against current evidence
ai-debt status            # Show workspace status (read-only)
ai-debt graph             # Build architecture dependency graph
ai-debt export            # Export findings to SARIF, CSV, JSONL, Governance
ai-debt enrich            # AI enrichment (disabled by default, mock or openai-compatible)
ai-debt enrich --context-preview  # Preview context without calling provider
ai-debt enrich --provider openai-compatible --allow-external-provider  # Real provider
ai-debt ai-status         # Show AI sidecar status (read-only)
ai-debt run               # Run full pipeline + write run metadata
```

## Validation

```bash
python -m pytest tests/ --tb=short -q --no-cov    # CLI: 2,970 tests
python scripts/validate_repo.py /path/to/repository
```

See `docs/VALIDATION_MATRIX.md` for the full test plan and `docs/RELEASE_CHECKLIST.md` for release criteria.

## Signal Governance

Pharabius uses a governed signal model with 10 families, 29 adapters, and 4 dispositions:

| Family | Adapters | Description |
|---|---|---|
| Runtime | 7 | Version pins, conflicts, reproducibility |
| Test | 2 | Coverage gaps, test quality |
| Code | 4 | Complexity, duplication, dead code, churn |
| Documentation | 1 | Missing or stale docs |
| Dependency | 7 | Health, freshness, lockfile, transitive |
| Security | 3 | Exposure, compliance, boundary |
| Architecture | 2 | Boundary violations, coupling |
| Configuration | 1 | Environment drift, config inconsistency |
| Observability | 1 | Logging gaps, monitoring coverage |
| Coverage | 1 | Coverage ratio and trend |

See `docs/SIGNAL_GOVERNANCE.md` for the full governance model and `docs/GOVERNANCE_CONTRACT.md` for the frozen v3 contract.

## Platform

Pharabius includes an optional web platform:

- **Backend**: FastAPI, PostgreSQL, 30 API endpoints
- **Frontend**: React, 8 views (FindingsTable, PortfolioSummary, RepositoryDashboard, RepositoryList, ReviewSummary, RunComparison, UploadPage, WorkPackages)
- **Deployment**: Docker Compose

```bash
cd platform && docker compose up
```

## Governance Presets

Five bundled governance presets are available:

- `default` — Balanced technical debt analysis
- `strict` — Conservative finding thresholds
- `advisory-heavy` — More advisory signals, fewer findings
- `security-focused` — Emphasize security exposure signals
- `minimal` — Core analysis only

See `docs/PRESET_REFERENCE.md` for details.

## Known Gaps

Pharabius is a mature CLI engine with an early-stage platform. Current limitations:

- **External scanner connectors** — SARIF, Semgrep, Trivy, Grype, Syft fixture import
  - _v3.3.0 adds **dependency/security connector family**: Trivy vulnerability, Grype vulnerability match, Syft SBOM. Scanner execution is not included._
  - _v3.4.0 adds **external evidence review**: imported and combined evidence visible in reports and status output. No finding creation._
  - _v3.5.0 adds **workflow lifecycle governance**: explicit state model for findings and work packages with transition validation. No auto-promotion._
  - _v3.6.0 adds **evidence-to-finding candidate promotion**: external evidence can propose reviewable candidate findings. Candidates are not accepted findings._
  - _v3.7.0 adds **candidate review workflow**: governed review of candidates with explicit decisions. Acceptance is review-level only, not debt-register promotion._
  - _v3.8.0 adds **candidate decision reporting**: audit trail, review summary in reports and governance export. Read-only — no mutation._
  - _v3.9.0 adds **candidate promotion gate**: eligibility rules for promotion without performing it. Gate-only — no writing to debt-register._
- **No live ticket sync** — No Jira, Linear, or GitHub Issues integration
- **Platform frontend is prototype-grade** — 28 tests pass, build succeeds, but 5 pre-existing TypeScript errors in test mocks
- **No portfolio governance** — Multi-repo governance workflows not implemented
- **Runtime governance is limited** — `AIBudget` handles context assembly only; no Schema-Budget Coupling

See `docs/PROJECT_STATUS.md` for the full maturity assessment.

## Documentation

| Document | Description |
|---|---|
| [Project Status](docs/PROJECT_STATUS.md) | Current maturity and known gaps |
| [Public Sync Notes](docs/PUBLIC_SYNC_NOTES.md) | v2.5.0 → v3.0.0 sync narrative |
| [Release State](docs/RELEASE_STATE.md) | Tag policy and branch structure |
| [Docs Index](docs/README.md) | Full documentation index |
| [Quickstart](docs/QUICKSTART.md) | Install, run, and understand output |
| [CHANGELOG.md](CHANGELOG.md) | Release notes (public + internal archive) |
| [CLI Reference](docs/CLI.md) | All 17 commands with safety classifications |
| [Artifact Contract](docs/ARTIFACT_CONTRACT.md) | Complete artifact inventory |
| [Signal Governance](docs/SIGNAL_GOVERNANCE.md) | Governance model and safety invariants |
| [Governance Contract](docs/GOVERNANCE_CONTRACT.md) | Frozen v3 contract |
| [V4 Readiness](docs/V4_READINESS.md) | v4 direction options |
| [Architecture](docs/ARCHITECTURE.md) | Module structure and import contract |
| [Known Limitations](docs/KNOWN_LIMITATIONS.md) | Honest constraints of current version |
| [Operating Doctrine](docs/OPERATING_DOCTRINE.md) | Release process and wave execution rules |
| [Connectors](docs/CONNECTORS.md) | External evidence connector foundation |
| [Roadmap](docs/ROADMAP.md) | Release history and future work |
