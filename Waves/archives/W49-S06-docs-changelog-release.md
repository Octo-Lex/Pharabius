# Wave 49 — v1.10.1 RC Hardening & Field Validation

Goal: Validate v1.10.0 across representative repositories, fix documentation/validation gaps, and produce a field-validation evidence pack without adding new product capability.

Release target: `v1.10.1`  
Branch target: `roadmap/v1.10.1-rc-hardening`  
Boundary: Release-candidate hardening only. No new product capability, no new command surface, no external integrations, no remediation automation.

# W49-S06 — Docs, Changelog, Release

Risk: Low  
Slice type: Release finalization  
Artifact impact: Version, docs, changelog, roadmap, release notes

## Scope

Finalize v1.10.1 release documentation, version metadata, changelog, roadmap, known limitations, validation evidence links, and release notes.

This slice must not add new runtime behavior beyond corrections required by earlier slices.

## Goals

- Bump version to `1.10.1`.
- Update `CHANGELOG.md`.
- Update `ROADMAP.md`.
- Update `KNOWN_LIMITATIONS.md`.
- Link the field-validation evidence pack from docs where appropriate.
- Confirm docs describe v1.10.1 as RC hardening, not new capability.
- Confirm build artifact uses version `1.10.1`.
- Confirm all 7 gates pass.
- Prepare release notes.

## Patch Set

Expected files:

```text
pyproject.toml
CHANGELOG.md
ROADMAP.md
KNOWN_LIMITATIONS.md
docs/README.md
docs/QUICKSTART.md
validation/field/v1.10.1/README.md
```

Recommended changelog entry:

```markdown
## v1.10.1

### Added
- v1 golden-path field-validation evidence pack.
- Artifact contract drift checks.
- Readiness report calibration.

### Changed
- Improved v1 readiness explanations and documentation clarity.
- Clarified command preconditions and artifact contract expectations from field validation.

### Safety
- No new product capability.
- No scoring behavior changes.
- No canonical artifact mutation.
- No external APIs.
- No autonomous remediation.
```

Recommended release headline:

```text
Pharabius v1.10.1 hardens the v1 release-candidate foundation with field validation, artifact contract drift checks, readiness calibration, and documentation fixes.
```

## Tests

No new product tests required unless docs/evidence helpers introduce validation tests.

Run the full suite and record totals.

## Targeted Verification

```bash
python -m build
grep -R "v1.10.1" CHANGELOG.md ROADMAP.md
grep -R "field validation" docs validation || true
pytest
```

## Expected Behavior

The branch is ready for PR, CI, squash merge, tag, and GitHub Release.

## Acceptance Criteria

- Version is `1.10.1`.
- Build output is `pharabius-1.10.1`.
- Changelog, roadmap, and known limitations are updated.
- Field-validation evidence is linked or discoverable.
- Release notes clearly state this is hardening, not new capability.
- All 7 local gates pass.
- No new runtime scope beyond approved Wave 49 slices.
- No external APIs.
- No canonical artifact mutation.
- No scoring behavior changes.
## Guardrails

- Do not add new product capability.
- Do not add new CLI commands unless required only for validation and explicitly scoped as internal/script tooling.
- Do not change risk scoring behavior.
- Do not mutate canonical artifacts during validation except by normal command execution in temporary validation workspaces.
- Do not modify production/source code in analyzed repositories.
- Do not call external APIs or remote repository services.
- Do not introduce dashboards, servers, schedulers, databases, queues, or background jobs.
- Do not create external issues, tickets, pull requests, assignments, milestones, or tracker updates.
- Do not weaken the v1 no-remediation boundary.
- Treat all outputs as repository-local validation and evidence artifacts.

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

