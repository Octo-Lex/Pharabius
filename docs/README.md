# Pharabius Documentation

## Getting Started

- [Quickstart](QUICKSTART.md) — Install, run, and understand output
- [Adoption Checklist](ADOPTION_CHECKLIST.md) — Go/no-go checklist for teams
- [Adoption Guide](ADOPTION_GUIDE.md) — Practical adoption walkthrough
- [Sample Output](SAMPLE_OUTPUT.md) — Example report output

## Reference

- [CLI Command Reference](CLI.md) — All 17 commands with safety classifications
- [Artifact Contract](ARTIFACT_CONTRACT.md) — Complete artifact inventory
- [Schema Map](SCHEMA_MAP.md) — Pydantic schema to artifact mapping
- [Architecture](ARCHITECTURE.md) — Module architecture and import contract

## Workflows

- [Governance Presets](GOVERNANCE.md) — Preset system and template overrides
- [Template Overrides](TEMPLATE_OVERRIDES.md) — Custom template engine
- [Review Workflow](REVIEW_WORKFLOW.md) — PET review sidecar
- [Ticket Drafts](TICKET_DRAFTS.md) — Local ticket draft generation
- [PET Ticket Workflow](PET_TICKET_WORKFLOW.md) — PET adoption workflow
- [Tracker Export Workflow](TRACKER_EXPORT_WORKFLOW.md) — Export bundle import guide
- [Export Bundles](EXPORT_BUNDLES.md) — Tracker-preparation artifacts
- [Portfolio Summary](PORTFOLIO.md) — Multi-repo portfolio rollups
- [Operational Claims](OPERATIONAL_CLAIMS.md) — Claims, gaps, traceability
- [Operational Claims Adoption](OPERATIONAL_CLAIMS_ADOPTION.md) — Claims usage guide
- [Scoring Evidence Pack](SCORING_EVIDENCE_PACK.md) — Enhanced risk scoring

## Validation

- [Release Checklist](RELEASE_CHECKLIST.md) — Pre-release verification
- [Validation Matrix](VALIDATION_MATRIX.md) — Multi-repo validation
- [Validation Summary](VALIDATION_SUMMARY.md) — v1.0.0 field validation
- [Architecture Graph Validation](ARCHITECTURE_GRAPH_VALIDATION_SUMMARY.md)
- [Known Limitations](KNOWN_LIMITATIONS.md)

## Safety Boundaries

Pharabius v1 does **not**:

- Modify production or source code
- Generate remediation patches
- Create pull requests or external issues
- Call external APIs (except optional OpenAI-compatible provider with explicit consent)
- Authorize autonomous remediation
- Perform remote repository crawling
- Claim factual precision for confidence distributions

## Release Notes

- [V1 Readiness Audit](V1_READINESS_AUDIT.md)
- [Scoring Calibration Decision](release-notes/v1.5.1-scoring-calibration-decision.md)
- [Changelog](../CHANGELOG.md)
- [Roadmap](ROADMAP.md)
