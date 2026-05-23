# Wave 44 — v1.7.1 Export Bundle Polish & Validation

Goal: Improve export-bundle validation, examples, and adoption documentation while preserving the no-API-write boundary.

Release target: `v1.7.1`  
Branch target: `roadmap/v1.7.1-export-bundle-polish`  
Boundary: Repository-local export artifacts only. No Jira, Linear, GitHub Issues, Azure DevOps, or other external API writes.

# W44-S06 — Docs, Changelog, Release

Risk: Low  
Slice type: Release finalization  
Artifact impact: Version, docs, changelog, roadmap

## Scope

Finalize v1.7.1 release documentation, version metadata, examples linkage, known limitations, and release notes. This slice must not add new runtime behavior beyond final wiring or documentation corrections required by earlier slices.

## Goals

- Bump version to `1.7.1`.
- Update `CHANGELOG.md`.
- Update `ROADMAP.md`.
- Update `KNOWN_LIMITATIONS.md`.
- Link export-bundle polish docs coherently.
- Confirm examples are referenced from docs.
- Confirm build artifacts use version `1.7.1`.
- Confirm all 7 gates pass.
- Prepare concise release notes.

## Patch Set

Expected files:

```text
pyproject.toml
CHANGELOG.md
ROADMAP.md
KNOWN_LIMITATIONS.md
docs/EXPORT_BUNDLES.md
docs/TRACKER_EXPORT_WORKFLOW.md
docs/examples/export-bundles/*
```

Recommended changelog entry:

```markdown
## v1.7.1

### Added
- Export bundle manifest validation.
- Tracker bundle completeness checks.
- Export bundle summary report.
- Tracker import workflow adoption guide.
- Richer tracker-specific export examples.

### Changed
- Improved export-bundle documentation and examples.

### Safety
- No external tracker APIs are called.
- No issues are created automatically.
- No canonical debt register or work package artifacts are mutated.
```

## Tests

No new product tests required unless final docs/examples introduce validation failures. Run all tests and confirm total count.

## Targeted Verification

```bash
python -m build
python - <<'PY'
from importlib.metadata import version
print(version("pharabius"))
PY
grep -R "v1.7.1" CHANGELOG.md ROADMAP.md
```

## Expected Behavior

The release is ready for PR, CI, merge, tag, and GitHub Release. Release line: “Pharabius v1.7.1 improves export-bundle validation, completeness checks, examples, and tracker import workflow documentation while preserving the no-API-write boundary.”

## Acceptance Criteria

- Version is `1.7.1`.
- Build output is `pharabius-1.7.1`.
- Changelog, roadmap, and known limitations are updated.
- Export bundle docs and tracker workflow docs are linked coherently.
- All examples validate.
- All 7 gates pass.
- No new runtime scope beyond approved Wave 44 slices.
- No external API writes.
- No canonical artifact mutation.
- No scoring behavior changes.

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

