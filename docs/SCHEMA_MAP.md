# Schema Map

This document maps every Pydantic schema in Pharabius to its source module, governing artifacts, and schema version.

## Core Schemas

| Schema | Module | Governs | Version |
|---|---|---|---|
| `EvidenceStore` | `schemas/evidence.py` | `.ai-debt/evidence.json` | 1.0 |
| `DebtRegister` | `schemas/finding.py` | `.ai-debt/debt-register.json` | 1.0 |
| `RepositoryProfile` | `schemas/repository.py` | `.ai-debt/project-profile.json` | 1.0 |
| `AnalysisUnitStore` | `schemas/analysis_unit.py` | `.ai-debt/analysis-units.json` | 1.0 |
| `ArchitectureGraph` | `schemas/architecture_graph.py` | `.ai-debt/architecture-graph.json` | 1.0 |
| `RunMetadata` | `schemas/run_metadata.py` | `.ai-debt/runs/RUN-*.json` | 1.0 |
| `VerificationReport` | `schemas/verification.py` | Verification output | 1.0 |
| `PlanResult` | `schemas/work_package.py` | Planning output | — |

## Review Schemas

| Schema | Module | Governs | Version |
|---|---|---|---|
| `ReviewDecisions` | `schemas/review.py` | `.ai-debt/review/decisions.json` | 1.0 |
| `ReviewDecision` | `schemas/review.py` | Single decision entry | — |
| `DecisionStatus` | `schemas/review.py` | Allowed statuses enum | — |

## Ticket Schemas

| Schema | Module | Governs | Version |
|---|---|---|---|
| `TicketDraftIndex` | `schemas/tickets.py` | `.ai-debt/ticket-drafts/ticket-drafts.json` | 1.0 |
| `TicketDraft` | `schemas/tickets.py` | Single ticket draft | — |
| `TicketDraftValidationIssue` | `schemas/tickets.py` | Validation issues | — |
| `TicketDraftCompleteness` | `schemas/tickets.py` | Completeness assessment | — |

## Export Bundle Schemas

| Schema | Module | Governs | Version |
|---|---|---|---|
| `ExportBundleManifest` | `schemas/export_bundles.py` | `.ai-debt/export-bundles/manifest.json` | 1.0 |
| `ExportBundleSummary` | `schemas/export_bundles.py` | Bundle summary | — |
| `TrackerKind` | `schemas/export_bundles.py` | Tracker enum | — |
| `ExportBundleFormat` | `schemas/export_bundles.py` | Format enum | — |

## Portfolio Schemas

| Schema | Module | Governs | Version |
|---|---|---|---|
| `PortfolioSummary` | `schemas/portfolio.py` | `.ai-debt/portfolio/portfolio-summary.json` | — |
| `PortfolioRepositoryEntry` | `schemas/portfolio.py` | Repository entries | — |
| `PortfolioRiskRollup` | `schemas/portfolio.py` | Risk rollup | — |
| `PortfolioCategoryRollup` | `schemas/portfolio.py` | Category rollup | — |
| `PortfolioReadinessRollup` | `schemas/portfolio.py` | Readiness rollup | — |

## Claims Schemas

| Schema | Module | Governs | Version |
|---|---|---|---|
| `OperationalClaim` | `schemas/claims.py` | Claim entries | — |
| `OperationalClaimsRegister` | `schemas/claims.py` | `.ai-debt/claims/operational-claims.json` | — |
| `GapItem` | `schemas/claims.py` | Gap entries | — |
| `QuestionItem` | `schemas/claims.py` | Question entries | — |
| `ClaimValidationResult` | `schemas/claims.py` | Validation result | — |
| `ClaimCompleteness` | `schemas/claims.py` | Per-claim completeness | — |
| `ClaimRegisterCompleteness` | `schemas/claims.py` | Register completeness | — |

## AI Schemas

| Schema | Module | Governs | Version |
|---|---|---|---|
| `FindingEnrichment` | `schemas/ai_enrichment.py` | Enrichment entries | — |
| `AIUsageSummary` | `schemas/ai_enrichment.py` | Usage tracking | — |
| `AIBudgetSummary` | `schemas/ai_enrichment.py` | Budget tracking | — |
| `AIContextSummary` | `schemas/ai_enrichment.py` | Context tracking | — |
| `EvidenceReference` | `schemas/ai_enrichment.py` | Evidence references | — |

## Config Schemas

| Schema | Module | Governs | Version |
|---|---|---|---|
| `ProjectConfig` | `schemas/config.py` | `.ai-debt/config.yaml` | — |
| `GovernanceConfig` | `schemas/governance.py` | `.ai-debt/governance.yaml` | — |

## Schema Compatibility Policy

During v1.x, canonical schemas follow **additive-only** changes:
- New optional fields may be added.
- Existing fields are not removed or renamed.
- Field semantics are not changed.
- Breaking changes require a major version bump (v2).

## Unstructured Artifacts

The following artifacts use Markdown without a formal schema:

- All `.md` report files
- Work package files (`WP-*.md`)
- Templateable artifacts (`remediation-roadmap.md`, `handoff-summary.md`, `work-package.md`)
- Traceability matrices
- Agent-handoff contract
- Gaps and questions registries

These are human-readable renderings governed by template structure and section conventions, not formal schemas.
