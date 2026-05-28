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


# S03 — Quality Gate Report Readability Improvements

Risk: Low-medium  
Slice type: Report polish  
Artifact impact: `.ai-debt/reports/quality-gate.md` and possibly JSON metadata only

## Scope

Improve quality-gate Markdown report readability without changing gate decision semantics.

This slice may reorganize sections, improve tables, add clearer recommended actions, and make fail/warn/pass output easier to understand in CI artifacts.

## Goals

- Make the result visible at the top of the report.
- Separate blocking violations from warnings.
- Include rule summary table.
- Include artifact input summary.
- Include CI interpretation guidance.
- Include next recommended command/action.
- Preserve JSON compatibility unless a backward-compatible field is added.

## Patch Set

Expected files:

```text
src/pharabius/core/quality_gate.py
src/pharabius/schemas/quality_gate.py        # only if additive metadata is needed
tests/test_quality_gate_report_readability.py
docs/QUALITY_GATE.md
```

Recommended Markdown structure:

```markdown
# Pharabius Quality Gate

## Result: FAIL
## Why This Result Happened
## Blocking Violations
## Warnings
## Rule Summary
## Artifact Inputs
## Recommended Actions
## CI Exit Behavior
## Safety Boundary
```

Recommended result block:

```markdown
## Result: FAIL

Mode: strict  
Exit code: 1  
Blocking violations: 2  
Warnings: 1
```

## Tests

Add tests for:

- PASS report includes result heading.
- WARN report includes warning section.
- FAIL report includes blocking violations section.
- Report includes CI exit behavior.
- Report includes safety boundary.
- Report includes recommended actions.
- Existing gate result decision is unchanged.
- Markdown output is deterministic.

## Targeted Verification

```bash
pytest tests/test_quality_gate_report_readability.py
```

## Expected Behavior

CI users can understand why the gate passed, warned, or failed without reading JSON.

## Acceptance Criteria

- Report readability improves.
- Gate decision logic is unchanged.
- Markdown remains deterministic.
- JSON changes, if any, are backward-compatible.
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
