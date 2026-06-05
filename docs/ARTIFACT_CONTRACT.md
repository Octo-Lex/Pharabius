# Artifact Contract Inventory

This document lists every artifact in the Pharabius v1 `.ai-debt/` contract, organized by category. It is the authoritative inventory for maintainers and integrators.

## Canonical Analysis Artifacts

These artifacts are produced by the core analysis pipeline and serve as the source of truth for downstream commands.

| Artifact | Schema | Version | Producer | Consumers | Mutation | Stability |
|---|---|---|---|---|---|---|
| `.ai-debt/evidence.json` | `EvidenceStore` | 1.0 | `scan` | `analyze`, `verify`, `enrich`, `portfolio`, claims | Regenerated | Stable |
| `.ai-debt/combined-evidence.json` | `EvidenceStore` | 1.0 | `combine-evidence` | `analyze --evidence` | Optional | Stable |
| `.ai-debt/combined-evidence-manifest.json` | `CombinedEvidenceManifest` | 1.0 | `combine-evidence` | Audit/traceability | Optional | Stable |
| `.ai-debt/debt-register.json` | `DebtRegister` | 1.0 | `analyze` | `report`, `plan`, `verify`, `status`, `tickets`, `export`, `portfolio`, claims | Regenerated | Stable |
| `.ai-debt/project-profile.json` | `RepositoryProfile` | 1.0 | `profile` | `report`, `portfolio` | Regenerated | Stable |
| `.ai-debt/analysis-units.json` | `AnalysisUnitStore` | 1.0 | `map-units` | `analyze`, `report` | Regenerated | Stable |
| `.ai-debt/architecture-graph.json` | `ArchitectureGraph` | 1.0 | `graph` | `analyze` (TD-ARCH), scoring | Regenerated | Stable |

## Human-Readable Canonical Mirrors

| Artifact | Format | Source | Mutation | Stability |
|---|---|---|---|---|
| `.ai-debt/debt-register.md` | Markdown | `debt-register.json` via `report` | Regenerated | Stable |

## Reports

| Artifact | Format | Producer | Mutation | Stability |
|---|---|---|---|---|
| `.ai-debt/reports/foundation-audit-report.md` | Markdown | `report` | Regenerated | Stable |
| `.ai-debt/reports/scoring-preview.json` | JSON | `analyze --scoring-preview` | Regenerated | Stable |
| `.ai-debt/reports/scoring-delta.md` | Markdown | `analyze --scoring-preview` | Regenerated | Stable |
| `.ai-debt/reports/ticket-draft-summary.md` | Markdown | `tickets` | Regenerated | Stable |
| `.ai-debt/reports/export-bundle-summary.md` | Markdown | `export` | Regenerated | Stable |

## Planning Artifacts

| Artifact | Format | Producer | Consumers | Mutation | Stability |
|---|---|---|---|---|---|
| `.ai-debt/remediation-roadmap.md` | Markdown (templateable) | `plan` | `tickets`, `portfolio` | Regenerated | Stable |
| `.ai-debt/handoff-summary.md` | Markdown (templateable) | `plan` | `portfolio` | Regenerated | Stable |
| `.ai-debt/work-packages/WP-*.md` | Markdown (templateable) | `plan` | `verify`, `tickets`, claims | Regenerated | Stable |

## Review Sidecar

| Artifact | Schema | Version | Producer | Consumers | Mutation | Stability |
|---|---|---|---|---|---|---|
| `.ai-debt/review/decisions.json` | `ReviewDecisions` | 1.0 | `review --init` | `review --status`, `review --validate`, `tickets`, `portfolio` | Append-only (human edits) | Stable |

## Scoring Artifacts

| Artifact | Format | Producer | Mutation | Stability |
|---|---|---|---|---|
| `.ai-debt/reports/scoring-preview.json` | JSON | `analyze --scoring-preview` | Regenerated | Stable |
| `.ai-debt/reports/scoring-delta.md` | Markdown | `analyze --scoring-preview` | Regenerated | Stable |

## Ticket Drafts

| Artifact | Schema | Version | Producer | Consumers | Mutation | Stability |
|---|---|---|---|---|---|---|
| `.ai-debt/ticket-drafts/ticket-drafts.json` | `TicketDraftIndex` | 1.0 | `tickets` | `export`, `portfolio` | Regenerated | Stable |
| `.ai-debt/ticket-drafts/TICKET-WP-*.md` | Markdown | `tickets` | `export` | Regenerated | Stable |

## Export Bundles

| Artifact | Schema | Version | Producer | Consumers | Mutation | Stability |
|---|---|---|---|---|---|---|
| `.ai-debt/export-bundles/manifest.json` | `ExportBundleManifest` | 1.0 | `export` | `portfolio` | Regenerated | Stable |
| `.ai-debt/export-bundles/{tracker}/` | Tracker-specific | — | `export` | External import | Regenerated | Stable |

## Portfolio Summaries

| Artifact | Format | Producer | Mutation | Stability |
|---|---|---|---|---|
| `.ai-debt/portfolio/portfolio-summary.json` | JSON | `portfolio` | Regenerated | Stable |
| `.ai-debt/portfolio/portfolio-summary.md` | Markdown | `portfolio` | Regenerated | Stable |
| `.ai-debt/portfolio/repository-index.json` | JSON | `portfolio` | Regenerated | Stable |
| `.ai-debt/portfolio/validation-rollup.md` | Markdown | `portfolio` | Regenerated | Stable |

## Operational Claims

| Artifact | Format | Producer | Consumers | Mutation | Stability |
|---|---|---|---|---|---|
| `.ai-debt/claims/operational-claims.json` | JSON | claims pipeline | `portfolio`, handoff | Regenerated | Stable |
| `.ai-debt/claims/operational-claims.md` | Markdown | claims pipeline | Human review | Regenerated | Stable |
| `.ai-debt/claims/confidence-report.md` | Markdown | claims pipeline | Human review | Regenerated | Stable |
| `.ai-debt/claims/gaps.md` | Markdown | claims pipeline | Human review, handoff | Regenerated | Stable |
| `.ai-debt/claims/questions.md` | Markdown | claims pipeline | Human review | Regenerated | Stable |
| `.ai-debt/traceability/evidence-finding-matrix.md` | Markdown | claims pipeline | Human review | Regenerated | Stable |
| `.ai-debt/traceability/finding-claim-matrix.md` | Markdown | claims pipeline | Human review | Regenerated | Stable |
| `.ai-debt/traceability/claim-workpackage-matrix.md` | Markdown | claims pipeline | Human review | Regenerated | Stable |
| `.ai-debt/agent-handoff-contract.md` | Markdown | claims pipeline | Downstream agents | Regenerated | Stable |

## AI Sidecar

| Artifact | Format | Producer | Mutation | Stability |
|---|---|---|---|---|
| `.ai-debt/ai/enrichment-report.json` | JSON | `enrich` | Regenerated | Stable |
| `.ai-debt/ai/enrichment-report.md` | Markdown | `enrich` | Regenerated | Stable |

## Run Metadata

| Artifact | Schema | Version | Producer | Mutation | Stability |
|---|---|---|---|---|---|
| `.ai-debt/runs/RUN-*.json` | `RunMetadata` | 1.0 | `run` | Append-only | Stable |

## Configuration

| Artifact | Schema | Producer | Mutation | Stability |
|---|---|---|---|---|
| `.ai-debt/config.yaml` | `ProjectConfig` | `init` | Human-edited | Stable |
| `.ai-debt/governance.yaml` | `GovernanceConfig` | Human-created | Human-edited | Stable |
| `architecture-policy.yaml` | None (user-authored) | Human-created | Human-edited | Stable |

## Mutation Policies

| Policy | Meaning |
|---|---|
| **Regenerated** | Artifact is overwritten completely each time the producer runs. Previous content is not preserved. |
| **Append-only** | New entries are added; existing entries are not modified by Pharabius. |
| **Human-edited** | Artifact is created by Pharabius (or user) but only modified by human editors. Pharabius reads but does not write. |
| **Read-only** | Pharabius reads the artifact but never writes it. |

## Stability Levels

| Level | Meaning |
|---|---|
| **Stable** | Artifact format is part of the v1 contract. Breaking changes require a major version bump. |

## Required vs Optional vs Conditional

**Required** artifacts are produced by every `ai-debt run` invocation. If a required artifact is missing, the v1 readiness report will report `fail` status.

**Optional** artifacts are produced only when their preconditions are met. For example:
- `architecture-graph.json` requires `ai-debt graph` to have been run
- `review/decisions.json` requires `ai-debt review --init`
- `ticket-drafts/*` requires `ai-debt tickets`
- `portfolio/*` requires `ai-debt portfolio`
- `claims/*` and `traceability/*` require the claims pipeline

**Conditional** artifacts depend on analysis results. For example:
- Work packages are generated only when findings exist
- Export bundles are generated only when `ai-debt export` is run

Missing optional artifacts produce `warning` status in the readiness report, not `fail`.

## Readiness Status Semantics

| Status | Meaning |
|---|---|
| **ready** | All required artifacts present and valid. No warnings. |
| **partial** | All required artifacts present and valid. Some optional artifacts missing or issues found. Review before release. |
| **needs_review** | One or more required artifacts missing or invalid. Do not release without addressing failures. |
