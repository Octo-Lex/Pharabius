# Project Status — Pharabius v3.0.0

> **Last updated:** 2026-06-04
> **Public baseline:** v3.0.0
> **Previous public baseline:** v2.5.0

## Product Summary

Pharabius is a repository-first technical debt intelligence platform with two product surfaces:

| Surface | Description | Size |
|---|---|---|
| **CLI Engine** | Evidence collection, analysis, reporting, export | 115 source files (~30,475 lines) |
| **Platform** | FastAPI backend + React frontend, Docker Compose | Backend 4,766 lines / Frontend 3,788 lines |

## Maturity Assessment

| Dimension | Status | Notes |
|---|---|---|
| CLI engine | **Production-ready** | 2,970 tests, deterministic analysis |
| Platform backend | **Production-ready** | 276 tests, 30 API endpoints, 6 migrations |
| Platform frontend | **Production-ready** | 28 tests, build clean (0 TS errors) |
| External scanners | **Connectors implemented** | SARIF, Semgrep, Trivy, Grype, Syft connectors; external evidence review in reports |
| Live ticket sync | **Not started** | No Jira/Linear integration |
| Runtime governance | **Low** | `AIBudget` is context-assembly only |

## Test Inventory

| Suite | Tests | Status |
|---|---|---|
| CLI engine (`src/pharabius/`) | 3,148 passed, 7 skipped | ✅ Validated |
| Platform backend (`platform/backend/`) | 276 passed, 5 skipped | ✅ Validated |
| Platform frontend (`platform/frontend/`) | 28 passed, 0 TS errors | ✅ Validated |
| **Total collected** | **3,452** | |

## Capabilities Since v2.5.0

### CLI Engine
- Signal governance model: 10 families, 29 adapters, 4 dispositions, 8 invariants, 5 diagnostics
- Governance export (schema v1.0, JSON + JSONL, forbidden field validation)
- Quality metrics (GQM-001–GQM-005)
- Trend computation across run history
- Coverage analysis with configurable presets
- Run comparison and delta computation
- Evidence traceability scoring
- Benchmark regression suite (6 fixture types)
- OSS field validation framework
- Runtime version normalization and conflict detection
- Architecture dependency graphing
- AI enrichment layer (mock + openai-compatible, disabled by default)
- Verification engine
- Scoring system
- Operational claims
- Quality gate engine
- 5 governance presets
- GitHub Action (`action.yml`)

### Platform
- FastAPI backend with 30 API endpoints
- PostgreSQL with 6 Alembic migrations
- React frontend with 8 views
- Docker Compose deployment
- Upload, portfolio summary, repository dashboard, run comparison

### Documentation
- 117 markdown documents
- Signal governance contract (`GOVERNANCE_CONTRACT.md`)
- V4 readiness memo (`V4_READINESS.md`)
- Architecture, configuration, security, observability signal docs
- v2 strategy docs (9 files in `docs/v2/`)

## Known Gaps

1. **External scanner connectors** — Five implemented (SARIF, Semgrep, Trivy, Grype, Syft). External evidence is reviewable in reports. Scanner execution and vulnerability confirmation not included.
2. **Live ticket sync** — No Jira, Linear, or GitHub Issues integration.
3. **Runtime Schema-Budget Coupling** — `AIBudget` handles context assembly only. No budget-schema coupling.
4. **Portfolio orchestration** — No multi-repo governance workflows.
5. **Frontend CI** — 5 pre-existing TypeScript errors in test mock types. Tests pass, build succeeds, but types need cleanup.
6. **Platform documentation** — API docs exist in code but no standalone platform guide.

## Sync Note

This document describes the state at the v3.0.0 public catch-up release. Internal development waves (v3.0.0 through v3.26.0) were consolidated into this single public release. See `PUBLIC_SYNC_NOTES.md` for details.

## Future Directions

See `V4_READINESS.md` for documented v4 options (policy engine, dashboard, enterprise reporting, policy packs). None are implemented.
