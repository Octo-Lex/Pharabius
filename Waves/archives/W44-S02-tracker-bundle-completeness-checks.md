# Wave 44 — v1.7.1 Export Bundle Polish & Validation

Goal: Improve export-bundle validation, examples, and adoption documentation while preserving the no-API-write boundary.

Release target: `v1.7.1`  
Branch target: `roadmap/v1.7.1-export-bundle-polish`  
Boundary: Repository-local export artifacts only. No Jira, Linear, GitHub Issues, Azure DevOps, or other external API writes.

# W44-S02 — Tracker Bundle Completeness Checks

Risk: Medium  
Slice type: Export quality / completeness reporting  
Artifact impact: Export-bundle sidecar/report only

## Scope

Add tracker-level completeness checks for Jira, Linear, GitHub Issues, and Azure DevOps export bundles. This slice should verify whether each generated tracker bundle contains the expected files, fields, and minimum import-ready content.

## Goals

- Evaluate each tracker bundle as `complete`, `partial`, or `needs_review`.
- Detect missing README files.
- Detect missing Markdown summary files.
- Detect missing CSV/YAML files where expected.
- Detect empty CSV rows or empty GitHub issue YAML sets.
- Detect missing required columns/fields.
- Preserve tracker-specific expectations without creating tracker-specific API dependencies.

## Patch Set

Expected files/modules:

```text
src/pharabius/schemas/export_bundles.py
src/pharabius/core/export_bundle_validation.py
src/pharabius/core/export_bundles.py
tests/test_export_bundle_completeness.py
```

Recommended schema addition:

```python
class TrackerBundleCompleteness(BaseModel):
    tracker: Literal["jira", "linear", "github-issues", "azure-devops"]
    status: Literal["complete", "partial", "needs_review"]
    expected_artifacts: list[str]
    present_artifacts: list[str]
    missing_artifacts: list[str]
    warnings: list[str] = []
```

Tracker-specific expected artifacts:

| Tracker | Expected artifacts |
|---|---|
| Jira | `README.md`, Markdown export, CSV export |
| Linear | `README.md`, Markdown export, CSV export |
| GitHub Issues | `README.md`, Markdown export, `issues/*.yaml` |
| Azure DevOps | `README.md`, Markdown export, CSV export |

Required import fields:

| Tracker | Required fields |
|---|---|
| Jira CSV | Summary, Description, Issue Type, Priority |
| Linear CSV | Title, Description, Priority |
| GitHub YAML | title, body, labels |
| Azure DevOps CSV | Title, Description, Work Item Type, Priority |

## Tests

Add tests for complete bundles for all four trackers, missing README, missing CSV/YAML, empty issue list, missing required fields, deterministic status output, and no external API calls.

## Targeted Verification

```bash
pytest tests/test_export_bundle_completeness.py
pytest tests/test_export_bundles*.py
```

## Expected Behavior

Generated export bundles include a completeness result per tracker. Completeness statuses help PET teams distinguish import-ready bundles from bundles requiring manual review.

## Acceptance Criteria

- Every supported tracker has a completeness check.
- Completeness statuses are deterministic and test-covered.
- Missing or malformed tracker artifacts are reported clearly.
- No export files are uploaded or transmitted.
- No canonical artifacts are mutated.
- No scoring behavior changes.
- All 7 local gates pass.

## Guardrails

- Do not call external tracker APIs.
- Do not create, update, assign, close, or schedule external issues.
- Do not mutate `debt-register.json`.
- Do not mutate canonical work packages.
- Do not change risk scoring behavior.
- Do not let review sidecar decisions influence scores.
- Do not add autonomous remediation or code-modification behavior.
- Keep all generated outputs under `.ai-debt/export-bundles/` or `.ai-debt/reports/`.

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

