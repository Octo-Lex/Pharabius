# Wave 44 — v1.7.1 Export Bundle Polish & Validation

Goal: Improve export-bundle validation, examples, and adoption documentation while preserving the no-API-write boundary.

Release target: `v1.7.1`  
Branch target: `roadmap/v1.7.1-export-bundle-polish`  
Boundary: Repository-local export artifacts only. No Jira, Linear, GitHub Issues, Azure DevOps, or other external API writes.

# W44-S04 — Add Adoption Guide for Tracker Import Workflows

Risk: Low  
Slice type: Documentation / adoption  
Artifact impact: Docs only

## Scope

Add a practical adoption guide explaining how Product Engineering Teams can use Pharabius export bundles with Jira, Linear, GitHub Issues, and Azure DevOps without giving Pharabius tracker credentials or API access.

## Goals

- Explain the safe handoff workflow.
- Clarify the difference between export bundles and tracker integrations.
- Provide tracker-specific manual import guidance.
- Document review checkpoints before importing.
- Provide recommended team policy for assignees, labels, milestones, area paths, and iterations.
- Keep all instructions credential-free and non-automated.

## Patch Set

Expected files:

```text
docs/TRACKER_EXPORT_WORKFLOW.md
docs/EXPORT_BUNDLES.md
README.md                         # optional link only
```

Recommended guide structure:

```markdown
# Tracker Export Workflow

## Purpose
## Safety boundary
## Recommended PET workflow
## Pre-import checklist
## Jira import notes
## Linear import notes
## GitHub Issues import notes
## Azure DevOps import notes
## What Pharabius intentionally does not do
## Troubleshooting
```

Recommended pre-import checklist includes accepted-review confirmation, false-positive exclusion, priority validation, no auto-assignees, label review, sensitive-information check, and target project/repository confirmation.

## Tests

Documentation-only slice. Add docs link checks only if the project already has docs validation utilities. Optional: verify `docs/TRACKER_EXPORT_WORKFLOW.md` is linked from `docs/EXPORT_BUNDLES.md`.

## Targeted Verification

```bash
grep -R "does not call API" docs/EXPORT_BUNDLES.md docs/TRACKER_EXPORT_WORKFLOW.md
grep -R "does not create issues" docs/EXPORT_BUNDLES.md docs/TRACKER_EXPORT_WORKFLOW.md
```

## Expected Behavior

Users have clear instructions for using repository-local export bundles as manual import preparation artifacts. The docs must not imply that Pharabius creates issues, authenticates with trackers, syncs status, or manages assignments.

## Acceptance Criteria

- `docs/TRACKER_EXPORT_WORKFLOW.md` exists.
- The guide covers Jira, Linear, GitHub Issues, and Azure DevOps.
- The guide includes a pre-import checklist.
- The no-API-write boundary is explicit.
- Docs are linked coherently.
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

