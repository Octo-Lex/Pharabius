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

## v0.6.0 — Architecture Graph Enhancements (planned)

- Monorepo node splitting (packages/*, apps/*) — fixes FN-001, FN-002, FN-004
- Rust import detection (use statements) — fixes FN-003
- Sub-package node derivation for Python src layouts
- Test-scope edge confidence reduction
- Architecture policy matching improvement

## v0.7.0 — AI Adapter (Evidence-Constrained) (planned)

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
