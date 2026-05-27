# v2.0.1 — CI Gate Adoption & SARIF Polish

Goal: Harden v2.0.0 for real CI adoption by improving quality-gate usability, SARIF validation, GitHub Action documentation, failure-mode guidance, and report readability without adding new product capability.

Release posture: patch release, not feature release.

Core boundary:
- No external SARIF upload by default
- No PR comments
- No GitHub Checks API integration
- No tracker writes
- No issue creation
- No dashboard
- No database
- No server
- No autonomous remediation
- No source code modification


# S06 — Docs, Changelog, Release

Risk: Low  
Slice type: Release finalization  
Artifact impact: Version, changelog, docs, release notes

## Scope

Finalize v2.0.1 release documentation, changelog, roadmap, known limitations, and release notes.

No new runtime behavior should be added in this slice beyond final wiring or documentation corrections required by earlier slices.

## Goals

- Bump version to `2.0.1`.
- Update `CHANGELOG.md`.
- Update `ROADMAP.md`.
- Update `KNOWN_LIMITATIONS.md`.
- Ensure docs link coherently.
- Confirm build artifact is `pharabius-2.0.1`.
- Confirm all 7 gates pass.
- Prepare release notes.

## Patch Set

Expected files:

```text
pyproject.toml
CHANGELOG.md
ROADMAP.md
KNOWN_LIMITATIONS.md
docs/QUALITY_GATE.md
docs/GITHUB_ACTION.md
docs/SARIF.md
docs/CI_TROUBLESHOOTING.md
docs/README.md
```

Recommended changelog entry:

```markdown
## v2.0.1

### Improved
- CI quality gate adoption documentation.
- GitHub Action usage guidance.
- Quality gate Markdown report readability.
- SARIF fixture validation and documentation.
- CI troubleshooting and failure-mode guidance.

### Safety
- No external SARIF upload by default.
- No PR comments, issue creation, tracker writes, or external API calls.
- No autonomous remediation or source code modification.
```

## Tests

Run all tests and release validation.

Recommended release checks:

```bash
python -m build
python scripts/validate_release_consistency.py
python scripts/validate_packaging.py
pytest
```

## Targeted Verification

```bash
grep -R "v2.0.1" CHANGELOG.md ROADMAP.md
grep -R "upload SARIF" docs/SARIF.md docs/GITHUB_ACTION.md docs/CI_TROUBLESHOOTING.md
python -m build
```

## Expected Behavior

v2.0.1 is ready for PR, CI, merge, tag, and release.

## Acceptance Criteria

- Version is `2.0.1`.
- Build output is `pharabius-2.0.1`.
- Changelog, roadmap, and known limitations are updated.
- Docs are coherent and linked.
- All tests pass.
- All 7 gates pass.
- No new product capability beyond adoption hardening.

## Guardrails

- Preserve v2.0.0 behavior unless the change is a bug fix or readability improvement.
- Do not add external writes.
- Do not upload SARIF by default.
- Do not post PR comments.
- Do not create issues.
- Do not add tracker API calls.
- Do not add dashboard/server/database scope.
- Do not mutate canonical Pharabius artifacts.
- Do not change scoring semantics.
- Do not add autonomous remediation.

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
