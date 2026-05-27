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


# S04 — SARIF Fixture Validation and Docs

Risk: Medium  
Slice type: SARIF validation / documentation  
Artifact impact: SARIF tests, fixtures, docs

## Scope

Add SARIF fixture validation and documentation for local SARIF generation.

This slice must preserve the clean boundary: Pharabius may generate local SARIF, but must not upload SARIF by default.

## Goals

- Add representative SARIF fixtures.
- Validate SARIF structure.
- Confirm SARIF can be generated locally.
- Document how SARIF maps Pharabius findings/gate results.
- Document optional user-owned upload separately.
- Confirm no default GitHub Code Scanning upload exists.

## Patch Set

Expected files:

```text
tests/test_sarif_fixtures.py
tests/fixtures/sarif/
docs/SARIF.md
docs/GITHUB_ACTION.md
docs/QUALITY_GATE.md
```

Recommended SARIF checks:

| Check | Expected |
|---|---|
| SARIF version | `2.1.0` |
| Runs exist | at least 1 |
| Tool driver name | Pharabius |
| Rules exist | mapped from findings/rules |
| Results exist | when findings/violations exist |
| Locations use repo-relative paths | yes |
| No upload instruction in generation path | yes |

## Tests

Add tests for:

- SARIF fixture parses as JSON.
- SARIF has required top-level fields.
- SARIF generated for a gate failure is valid.
- SARIF generated for findings includes rule IDs.
- SARIF result locations are repo-relative.
- SARIF docs state local generation only.
- No default upload step exists in action/workflow examples.

## Targeted Verification

```bash
pytest tests/test_sarif_fixtures.py
grep -R "upload-sarif" action.yml docs/ci || true
```

## Expected Behavior

Users can trust local SARIF as a portable artifact while understanding that uploading it is their explicit CI configuration decision.

## Acceptance Criteria

- SARIF fixtures validate.
- SARIF docs exist.
- SARIF generation remains local-only.
- No default upload behavior is introduced.
- All 7 local gates pass.

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
