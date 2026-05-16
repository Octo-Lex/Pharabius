# Pharabius Roadmap

## v0.1.1 — Polish & Validation-Driven Fixes

- Validation-driven false positive tuning
- Dependency policy refinements (per-package-root exclusions, workspace-aware Python monorepos)
- Runtime performance improvements (large repo optimization, streaming evidence)
- Additional repository test cases (Java, .NET, IaC-only)
- P2 backlog from validation summary: profile boolean fields, Go test framework, pnpm workspace lockfile per-package check

## v0.2.0 — Export & Connectors

- `ai-debt export --format sarif` — SARIF output for GitHub Security tab integration
- `ai-debt export --format csv` — CSV output for spreadsheet analysis and reporting
- Coverage report ingestion (pytest-cov XML, Istanbul/NYC JSON, Go coverage)
- Static-analysis evidence connector (Semgrep, ruff audit mode)
- Import graph analysis (coupling metrics, circular dependency detection)

## v0.3.0 — AI Adapter (Evidence-Constrained)

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
