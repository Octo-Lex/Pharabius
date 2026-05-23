# Wave 44 — v1.7.1 Export Bundle Polish & Validation

Goal: Improve export-bundle validation, examples, and adoption documentation while preserving the no-API-write boundary.

Release target: `v1.7.1`  
Branch target: `roadmap/v1.7.1-export-bundle-polish`  
Boundary: Repository-local export artifacts only. No Jira, Linear, GitHub Issues, Azure DevOps, or other external API writes.

# W44-S05 — Add Export-Bundle Summary Report

Risk: Low-medium  
Slice type: Reporting / sidecar artifact  
Artifact impact: New report under `.ai-debt/reports/`

## Scope

Add a human-readable export-bundle summary report generated alongside tracker export bundles. The report should summarize generated tracker artifacts, completeness status, validation issues, skipped items, and safety boundaries.

## Goals

- Create `.ai-debt/reports/export-bundle-summary.md`.
- Summarize all tracker bundles in one place.
- Include validation and completeness results from W44-S01 and W44-S02.
- List skipped items and reasons.
- List generated artifact paths.
- Explicitly state that no external APIs were called.
- Keep the report deterministic and diff-friendly.

## Patch Set

Expected files/modules:

```text
src/pharabius/core/export_bundles.py
src/pharabius/core/export_bundle_reports.py       # new, if useful
src/pharabius/schemas/export_bundles.py
tests/test_export_bundle_summary_report.py
docs/EXPORT_BUNDLES.md
```

Recommended report structure:

```markdown
# Export Bundle Summary

## Generation Summary
## Tracker Summary
## Generated Artifacts
## Completeness
## Validation Issues
## Skipped Items
## Safety Boundary
```

The Safety Boundary section must state that Pharabius generated repository-local export files only and did not call external tracker APIs or create issues.

## Tests

Add tests that the summary report is generated, includes all four trackers, artifact paths, completeness statuses, validation warnings/errors, skipped items, the no-API-write statement, deterministic output for stable input, and no canonical mutation.

## Targeted Verification

```bash
pytest tests/test_export_bundle_summary_report.py
python -m pharabius.cli export --help
```

## Expected Behavior

After export bundle generation, users can open `.ai-debt/reports/export-bundle-summary.md` to understand what was generated and whether each tracker bundle is ready for import review.

## Acceptance Criteria

- Summary report is generated when export bundles are generated.
- Report is human-readable and deterministic.
- Report includes validation and completeness data.
- Report includes explicit no-API-write language.
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

