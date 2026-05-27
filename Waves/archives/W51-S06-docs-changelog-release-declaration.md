# Wave 51 — v1.11.0 Final v1 Stabilization & Declaration

Goal: Declare the v1 product line stable by freezing the v1 artifact contract, command surface, safety boundaries, and compatibility commitments, while adding only final validation, documentation, and release-declaration artifacts.

Release target: `v1.11.0`  
Branch target: `roadmap/v1.11.0-final-v1-stabilization`  
Boundary: Stabilization and declaration only. No new product capability.

# W51-S06 — Docs, Changelog, Release Declaration

Risk: Low  
Slice type: Release finalization / stability declaration  
Artifact impact: Version, docs, changelog, roadmap, release declaration

## Scope

Finalize the v1.11.0 release declaration. This slice bumps version metadata, updates release docs, publishes the v1 stable declaration, and prepares the release notes.

This slice must not add runtime capability beyond final validation wiring or documentation corrections required by earlier slices.

## Goals

- Bump version to `1.11.0`.
- Update `CHANGELOG.md`.
- Update `ROADMAP.md`.
- Update `KNOWN_LIMITATIONS.md`.
- Add final v1 release declaration document.
- Link stability contract, safety boundaries, adoption guide, and validation evidence.
- Confirm build artifact uses version `1.11.0`.
- Confirm all 7 gates pass.
- Prepare GitHub Release notes.

## Patch Set

Expected files:

```text
pyproject.toml
CHANGELOG.md
ROADMAP.md
KNOWN_LIMITATIONS.md
docs/V1_RELEASE_DECLARATION.md              # new
docs/V1_STABILITY_CONTRACT.md
docs/SAFETY_BOUNDARIES.md
docs/V1_ADOPTION_AND_UPGRADE_GUIDE.md
docs/validation-results/v1-final-validation-evidence.md
docs/README.md
README.md                                   # optional link/update
```

Recommended release declaration structure:

```markdown
# Pharabius v1 Release Declaration

## Declaration
## Stable surfaces
## Safety boundaries
## Validation evidence
## Compatibility commitments
## Maintenance policy
## What remains out of scope
## Path to v2.0 planning
```

Recommended changelog entry:

```markdown
## v1.11.0

### Added
- v1 stability contract and compatibility policy.
- Final artifact contract freeze checks.
- Safety boundary policy documentation.
- v1 final validation evidence pack.
- v1 adoption and upgrade guide.
- v1 release declaration.

### Stability
- Declares the v1 artifact contract, command surface, local-first workflow, and safety boundaries stable for adoption.

### Safety
- No new product capability.
- No autonomous remediation.
- No external API writes.
- No canonical artifact mutation beyond normal command behavior.
```

Recommended release headline:

```text
Pharabius v1.11.0 declares the v1 artifact contract, command surface, safety boundaries, and local-first handoff workflow stable for adoption.
```

## Tests

No new feature tests required unless docs/examples validation is added.

Recommended final verification:

```bash
python -m build
python scripts/validate_release_consistency.py
python scripts/validate_artifact_contract.py
python scripts/validate_packaging.py
pytest
```

## Targeted Verification

```bash
grep -R "v1.11.0" CHANGELOG.md ROADMAP.md pyproject.toml
grep -R "v1 Release Declaration" docs/V1_RELEASE_DECLARATION.md
python -m build
```

## Expected Behavior

The release is ready for PR, CI, merge, tag, and GitHub Release as the stable v1 declaration release.

## Acceptance Criteria

- Version is `1.11.0`.
- Build output is `pharabius-1.11.0`.
- Changelog, roadmap, and known limitations are updated.
- v1 release declaration exists.
- Stability contract, safety boundaries, adoption guide, and validation evidence are linked.
- All 7 local gates pass.
- Release notes are prepared.
- No new product capability is introduced.
- No external APIs.
- No autonomous remediation.
## Guardrails

- Do not add new product capabilities.
- Do not add new CLI commands unless strictly diagnostic and explicitly approved; this wave should prefer scripts/docs/checks over command expansion.
- Do not change the v1 artifact contract except to document and freeze it.
- Do not break existing artifact paths, schema names, or command behavior.
- Do not mutate canonical artifacts outside normal command behavior.
- Do not change risk scoring behavior.
- Do not introduce dashboard, server, scheduler, database, remote crawling, or external APIs.
- Do not create external tracker issues or write to external systems.
- Do not authorize autonomous remediation or code modification.
- Treat this wave as a stability declaration and compatibility-hardening wave.

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

