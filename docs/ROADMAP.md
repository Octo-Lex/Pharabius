# Pharabius Roadmap

## v0.3.1 — Stabilization & Verification UX

- Verification report readability improvements
- Verification edge-case test coverage for all 6 statuses
- `ai-debt status` read-only workspace summary command
- Lifecycle documentation
- Documentation consistency

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

## v0.5.0 — AI Adapter (Evidence-Constrained) (planned)

- AI adapter interface behind `--ai` flag
- Evidence-constrained: AI may only comment on evidence IDs already collected by the deterministic scanner
- No hallucinated findings, no fabricated evidence
- Human-readable narrative reports from AI analysis
- Risk narrative generation for handoff summaries

## Future Considerations

- Git history analysis (change frequency, hotspots, churn metrics)
- Multi-repository comparison and portfolio-level dashboards
- IDE plugin integration (VS Code, JetBrains)
- CI/CD gate mode (exit non-zero when new debt is introduced)
- Dependency freshness and deprecation tracking
- Architecture decision record (ADR) generation from findings
