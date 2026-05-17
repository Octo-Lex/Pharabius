# Pharabius

Pharabius is a repository-first technical debt intelligence platform.

v1 analyzes repositories and produces evidence-backed technical debt reports, remediation roadmaps, and engineering handoff packages.

It does not modify production code by default.

## Commands

```bash
ai-debt init              # Create .ai-debt workspace
ai-debt profile           # Detect repository stack and structure
ai-debt scan              # Collect normalized evidence
ai-debt map               # Map evidence into analysis units
ai-debt analyze --no-ai   # Generate deterministic debt findings
ai-debt report            # Generate domain reports
ai-debt plan              # Generate roadmap, work packages, and handoff
ai-debt verify            # Verify findings against current evidence
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
| [KNOWN_LIMITATIONS.md](docs/KNOWN_LIMITATIONS.md) | Honest constraints of current version |
| [ROADMAP.md](docs/ROADMAP.md) | Planned v0.2.1, v0.3.0, and future work |
| [VALIDATION_SUMMARY.md](docs/VALIDATION_SUMMARY.md) | 8-repository validation results |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | Module structure and import contract |
| [ENGINEERING_POLICY.md](docs/ENGINEERING_POLICY.md) | Quality gates and coding standards |
