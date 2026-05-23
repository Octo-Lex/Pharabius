# Wave 44 — v1.7.1 Export Bundle Polish & Validation

Goal: Improve export-bundle validation, examples, and adoption documentation while preserving the no-API-write boundary.

Release target: `v1.7.1`  
Branch target: `roadmap/v1.7.1-export-bundle-polish`  
Boundary: Repository-local export artifacts only. No Jira, Linear, GitHub Issues, Azure DevOps, or other external API writes.

# W44-S03 — Add Richer Tracker-Specific Examples

Risk: Low  
Slice type: Documentation / examples  
Artifact impact: Docs and examples only

## Scope

Add richer tracker-specific example export bundles for Jira, Linear, GitHub Issues, and Azure DevOps. Examples should show realistic but safe ticket content derived from ticket-draft/work-package style inputs. They must not contain secrets, real customer data, private repository names, or claims of external issue creation.

## Goals

- Improve adoption by showing complete tracker export examples.
- Demonstrate Markdown, CSV, and YAML structures.
- Show safe default fields.
- Show skipped/needs-review examples where applicable.
- Reinforce that files are import-preparation artifacts only.

## Patch Set

Expected files:

```text
docs/examples/export-bundles/manifest.example.json
docs/examples/export-bundles/jira/README.md
docs/examples/export-bundles/jira/jira-export.example.md
docs/examples/export-bundles/jira/jira-export.example.csv
docs/examples/export-bundles/linear/README.md
docs/examples/export-bundles/linear/linear-export.example.md
docs/examples/export-bundles/linear/linear-export.example.csv
docs/examples/export-bundles/github-issues/README.md
docs/examples/export-bundles/github-issues/github-issues-export.example.md
docs/examples/export-bundles/github-issues/issues/ISSUE-001.example.yaml
docs/examples/export-bundles/azure-devops/README.md
docs/examples/export-bundles/azure-devops/azure-devops-export.example.md
docs/examples/export-bundles/azure-devops/azure-devops-export.example.csv
tests/test_export_bundle_examples.py
```

Example content should include one high-priority architecture-debt ticket, one medium-priority test-debt ticket, one skipped/deferred item, one completeness warning example, and safe generic labels/tags.

## Tests

Add lightweight tests that the example manifest is valid JSON, GitHub issue YAML parses successfully, CSV files include required headers, manifest-referenced example paths exist, and examples do not contain external API-write instructions.

## Targeted Verification

```bash
pytest tests/test_export_bundle_examples.py
python - <<'PY'
from pathlib import Path
print(Path("docs/examples/export-bundles").exists())
PY
```

## Expected Behavior

Users can inspect example bundles and understand what generated export files look like, which files can be manually imported, which fields remain intentionally blank, and which operations Pharabius does not perform.

## Acceptance Criteria

- Examples exist for all four supported trackers.
- Examples are parseable and test-covered.
- Examples reinforce no-API-write semantics.
- Examples do not include real secrets, real customer data, or private identifiers.
- No runtime behavior changes are introduced.
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

