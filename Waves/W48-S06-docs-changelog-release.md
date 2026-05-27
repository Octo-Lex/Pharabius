# Wave 48 — v1.10.0 v1 Contract Consolidation & Release Candidate

Goal: Consolidate the v1 artifact contract, command surface, documentation, examples, validation scripts, and release readiness into a coherent v1.10 release candidate without adding a new product capability.

Release target: `v1.10.0`  
Branch target: `roadmap/v1.10.0-v1-contract-consolidation`  
Boundary: Consolidation, validation, documentation, and release-readiness only. No new product capability, no autonomous remediation, no external API writes.

# W48-S06 — Docs, Changelog, Release

Risk: Low  
Slice type: Release finalization  
Artifact impact: Version, docs, changelog, roadmap

## Scope

Finalize v1.10.0 release documentation, version metadata, changelog, roadmap, known limitations, and release notes.

This slice must not add new runtime behavior beyond final wiring or documentation corrections required by earlier slices.

## Goals

- Bump version to `1.10.0`.
- Update `CHANGELOG.md`.
- Update `ROADMAP.md`.
- Update `KNOWN_LIMITATIONS.md`.
- Finalize docs links.
- Confirm artifact contract inventory and schema map are linked.
- Confirm CLI docs are current.
- Confirm validation docs reference golden path and readiness report.
- Confirm build artifact uses version `1.10.0`.
- Confirm all 7 gates pass.
- Prepare release notes.

## Patch Set

Expected files:

```text
pyproject.toml
CHANGELOG.md
ROADMAP.md
KNOWN_LIMITATIONS.md
README.md
docs/README.md
docs/QUICKSTART.md
docs/CLI.md
docs/ARTIFACT_CONTRACT.md
docs/SCHEMA_MAP.md
docs/VALIDATION.md
```

Recommended changelog entry:

```markdown
## v1.10.0

### Added
- v1 artifact contract inventory.
- v1 schema map.
- End-to-end golden path validation.
- v1 readiness report.

### Changed
- Improved CLI help consistency.
- Improved documentation architecture and onboarding.
- Consolidated v1 validation and release-readiness documentation.

### Safety
- No new product capability added.
- No scoring behavior changes.
- No external APIs added.
- No autonomous remediation added.
```

## Tests

No new product tests required unless final docs/examples introduce validation failures.

Recommended final checks:

- Version is `1.10.0`.
- Build artifact is `pharabius-1.10.0`.
- All docs links required by tests pass.
- All local gates pass.

## Targeted Verification

```bash
python -m build
grep -R "v1.10.0" CHANGELOG.md ROADMAP.md
grep -R "Artifact Contract" docs/README.md README.md
grep -R "Golden Path" docs/VALIDATION.md
pytest
```

## Expected Behavior

The release is ready for PR, CI, merge, tag, and GitHub Release.

Expected release line:

```text
Pharabius v1.10.0 consolidates the v1 artifact contract, command surface, validation path, documentation architecture, and release-readiness reporting as a v1 release-candidate foundation.
```

## Acceptance Criteria

- Version is `1.10.0`.
- Build output is `pharabius-1.10.0`.
- Changelog, roadmap, and known limitations are updated.
- Artifact contract, schema map, CLI, validation, and onboarding docs are linked coherently.
- All 7 local gates pass.
- No new product capability is introduced.
- No external APIs.
- No canonical artifact mutation outside expected generated validation reports.
- No scoring behavior changes.
## Guardrails

- Do not add a new product capability.
- Do not modify production/source code under analysis.
- Do not generate remediation patches.
- Do not create pull requests or external issues.
- Do not call external APIs.
- Do not add a server, dashboard, scheduler, queue, remote crawler, or database.
- Do not change risk scoring behavior.
- Do not mutate canonical analysis artifacts except where explicitly regenerating validation outputs in controlled tests.
- Do not weaken the no-remediation boundary.
- Treat this wave as a v1 contract consolidation and release-candidate hardening wave.

## Verification Commands

Run the full local gate suite:

```bash
ruff format --check .
ruff check .
mypy src
lint-imports
pytest
python -m build
python scripts/validate_repo.py .
```

Additional targeted checks for this slice are listed below.

