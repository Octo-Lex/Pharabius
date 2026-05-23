# Wave 45 — v1.8.0 Portfolio Summary Foundation

Goal: Add repository-local portfolio summary artifacts that consolidate one or more Pharabius runs into a lightweight portfolio view, without adding a server, dashboard, scheduler, database, remote repository crawler, or external integration.

Release target: `v1.8.0`  
Branch target: `roadmap/v1.8.0-portfolio-summary`  
Boundary: File-based, repository-local or workspace-local portfolio summaries only.

# Wave 45 Patch-Set Index

This directory contains standalone Markdown patch-set files for Wave 45.

| Slice | Title | Risk | File |
|---|---|---|---|
| W45-S01 | Portfolio summary artifact contract | Medium | `W45-S01-portfolio-summary-artifact-contract.md` |
| W45-S02 | Aggregate repository summaries from `.ai-debt/` outputs | Medium | `W45-S02-aggregate-repository-summaries.md` |
| W45-S03 | Portfolio risk/category rollups | Medium | `W45-S03-portfolio-risk-category-rollups.md` |
| W45-S04 | Portfolio readiness and validation rollups | Medium | `W45-S04-portfolio-readiness-validation-rollups.md` |
| W45-S05 | CLI command: `ai-debt portfolio` | Medium | `W45-S05-cli-command-ai-debt-portfolio.md` |
| W45-S06 | Docs, examples, tests, changelog, release | Low | `W45-S06-docs-examples-tests-changelog-release.md` |

## Wave-Level Acceptance Criteria

- Portfolio output is file-based and repository-local/workspace-local.
- No dashboard, server, scheduler, database, or remote crawler is added.
- No external APIs are called.
- No external issues are created.
- Source `.ai-debt/debt-register.json` files are not mutated.
- Work packages are not mutated.
- Risk scoring behavior is unchanged.
- Review sidecar decisions do not influence scores.
- Portfolio rollups are deterministic and derived from existing artifacts.
- All 7 local gates pass.
