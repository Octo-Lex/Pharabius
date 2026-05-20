# Pharabius

Pharabius is a repository-first technical debt intelligence platform.

v1 analyzes repositories and produces evidence-backed technical debt reports, remediation roadmaps, and engineering handoff packages.

It does not modify production code by default.

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
ai-debt export            # Export findings to SARIF, CSV, JSONL
ai-debt enrich            # AI enrichment (disabled by default, mock or openai-compatible)
ai-debt enrich --context-preview  # Preview context without calling provider
ai-debt enrich --provider openai-compatible --allow-external-provider  # Real provider
ai-debt ai-status         # Show AI sidecar status (read-only)
ai-debt run               # Run full pipeline + write run metadata
```

## Validation

Validate Pharabius against any repository:

```bash
python scripts/validate_repo.py /path/to/repository
```

See `docs/VALIDATION_MATRIX.md` for the full test plan and `docs/RELEASE_CHECKLIST.md` for release criteria.

## Documentation

| Document | Description |
|---|---|
| [CHANGELOG.md](CHANGELOG.md) | Release notes for each version |
| [SAMPLE_OUTPUT.md](docs/SAMPLE_OUTPUT.md) | Curated output snippets and examples |
| [ADOPTION_GUIDE.md](docs/ADOPTION_GUIDE.md) | Product Engineering Team adoption workflow |
| [GOVERNANCE.md](docs/GOVERNANCE.md) | Governance overview and safety invariants |
| [PRESET_REFERENCE.md](docs/PRESET_REFERENCE.md) | Bundled governance preset descriptions |
| [TEMPLATE_OVERRIDES.md](docs/TEMPLATE_OVERRIDES.md) | Template override guide and placeholder reference |
| [KNOWN_LIMITATIONS.md](docs/KNOWN_LIMITATIONS.md) | Honest constraints of current version |
| [ROADMAP.md](docs/ROADMAP.md) | Release history and future work |
| [VALIDATION_SUMMARY.md](docs/VALIDATION_SUMMARY.md) | 8-repository validation results |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | Module structure and import contract |
| [ENGINEERING_POLICY.md](docs/ENGINEERING_POLICY.md) | Quality gates and coding standards |
