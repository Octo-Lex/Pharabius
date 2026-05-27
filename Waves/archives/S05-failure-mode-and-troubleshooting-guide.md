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


# S05 — Failure-Mode and Troubleshooting Guide

Risk: Low  
Slice type: Documentation / diagnostics  
Artifact impact: Docs only, optional diagnostic message polish

## Scope

Create a practical troubleshooting guide for common CI quality-gate failures and first-run issues.

This slice should help users resolve failures without weakening the gate or bypassing safety boundaries.

## Goals

- Add CI troubleshooting guide.
- Document common gate failures.
- Explain exit codes.
- Explain missing artifact errors.
- Explain strict/warn/advisory modes.
- Explain SARIF local generation vs upload.
- Explain what to do when `ai-debt doctor` reports missing workspace/artifacts.
- Include copyable remediation commands that generate artifacts, not code changes.

## Patch Set

Expected files:

```text
docs/CI_TROUBLESHOOTING.md
docs/QUALITY_GATE.md
docs/GITHUB_ACTION.md
docs/README.md
```

Recommended sections:

```markdown
# CI Troubleshooting

## Quality gate failed
## Quality gate warned
## Missing required artifacts
## Missing optional artifacts
## Contract drift errors
## Blocking gaps
## Readiness is needs_review
## SARIF file not found
## GitHub Action failed
## Exit codes
## Safe recovery commands
## What Pharabius will not do
```

Safe recovery commands:

```bash
ai-debt doctor
ai-debt init
ai-debt profile
ai-debt scan
ai-debt analyze --no-ai
ai-debt report
ai-debt plan
ai-debt gate --mode warn
```

## Tests

Documentation-only slice. Optional tests:

- Docs file exists.
- Docs mention exit codes.
- Docs mention no external writes.
- Docs mention SARIF upload is not default.
- Docs include `ai-debt doctor`.

## Targeted Verification

```bash
grep -R "ai-debt doctor" docs/CI_TROUBLESHOOTING.md
grep -R "does not upload SARIF by default" docs || true
```

## Expected Behavior

Users have a clear path from a failed CI gate to safe diagnosis and artifact regeneration.

## Acceptance Criteria

- Troubleshooting guide exists.
- Guide covers the major failure modes.
- Guide does not recommend bypassing safety boundaries.
- Guide does not recommend external writes.
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
