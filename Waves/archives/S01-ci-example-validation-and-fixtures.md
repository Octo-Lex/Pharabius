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


# S01 — CI Example Validation and Fixtures

Risk: Medium  
Slice type: CI example validation / fixtures  
Artifact impact: Docs, fixtures, tests only

## Scope

Add validation for CI examples introduced around the v2.0.0 quality gate. This slice should make examples safer to copy, easier to test, and less likely to drift.

## Goals

- Validate GitHub Actions, GitLab CI, Azure Pipelines, Jenkins, and portable shell examples.
- Add fixture files for CI examples.
- Assert examples use local-only behavior.
- Assert examples do not include external write steps.
- Assert examples archive or expose local quality-gate reports where practical.
- Preserve no-credentials, no-token defaults.

## Patch Set

Expected files:

```text
docs/ci/github-actions.md
docs/ci/gitlab-ci.md
docs/ci/azure-pipelines.md
docs/ci/jenkins.md
docs/ci/portable-shell.md
tests/test_ci_examples.py
tests/fixtures/ci/
```

Recommended checks:

| Example | Check |
|---|---|
| GitHub Actions | YAML parses, includes `ai-debt gate`, does not include `upload-sarif` by default |
| GitLab CI | YAML parses, archives `.ai-debt/reports/quality-gate.*` |
| Azure Pipelines | YAML parses, publishes reports only |
| Jenkins | Contains `ai-debt gate`, archives local reports |
| Portable shell | Uses `set -euo pipefail`, runs local commands only |

## Tests

Add tests for:

- CI example files exist.
- YAML examples parse where applicable.
- Examples include `ai-debt gate`.
- Examples do not include default external upload steps.
- Examples do not require tokens or secrets.
- Examples refer to local report artifacts.
- Portable shell example is syntactically simple and copyable.

## Targeted Verification

```bash
pytest tests/test_ci_examples.py
grep -R "ai-debt gate" docs/ci
grep -R "upload-sarif" docs/ci || true
```

## Expected Behavior

Users can copy CI examples with confidence that they run Pharabius locally and produce local quality-gate artifacts.

## Acceptance Criteria

- CI example validation tests pass.
- No example uploads SARIF by default.
- No example creates issues or PR comments.
- No example requires tracker credentials.
- Examples clearly archive or expose local reports.
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
