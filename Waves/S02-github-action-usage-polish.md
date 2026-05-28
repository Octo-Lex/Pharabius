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


# S02 — GitHub Action Usage Polish

Risk: Medium  
Slice type: GitHub Action adoption / metadata hardening  
Artifact impact: `action.yml`, docs, tests

## Scope

Polish the GitHub Action wrapper to make it easier and safer to use in CI while preserving local-only defaults.

The action must not upload SARIF, post comments, create issues, or require a GitHub token by default.

## Goals

- Improve `action.yml` descriptions and inputs.
- Confirm default action behavior is local-only.
- Add examples for strict/warn/advisory gate modes.
- Add examples for local SARIF artifact generation.
- Clearly separate local SARIF generation from optional user-configured upload.
- Add metadata tests for action safety.

## Patch Set

Expected files:

```text
action.yml
docs/GITHUB_ACTION.md
docs/ci/github-actions.md
tests/test_github_action_metadata.py
```

Recommended action inputs:

| Input | Purpose | Default |
|---|---|---|
| `mode` | strict / warn / advisory | strict |
| `max-critical` | critical threshold | 0 |
| `max-high` | high threshold | 5 |
| `fail-on-blocking-gaps` | fail on blocking gaps | true |
| `generate-sarif` | generate local SARIF artifact | false or existing default |
| `output-dir` | report output directory | `.ai-debt/reports` |

## Tests

Add tests for:

- `action.yml` parses.
- Action does not reference `github/codeql-action/upload-sarif`.
- Action does not require `GITHUB_TOKEN`.
- Action does not call GitHub REST/GraphQL APIs.
- Action contains safety description.
- Docs include local-only statement.
- Docs show optional SARIF upload as user-owned workflow step, not action default.

## Targeted Verification

```bash
pytest tests/test_github_action_metadata.py
grep -R "upload-sarif" action.yml || true
grep -R "GITHUB_TOKEN" action.yml || true
```

## Expected Behavior

The GitHub Action remains a wrapper for local Pharabius execution and local artifact generation.

## Acceptance Criteria

- Action metadata is validated.
- No default upload step exists.
- No token is required by default.
- Documentation clearly distinguishes local SARIF generation from optional user-managed upload.
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
