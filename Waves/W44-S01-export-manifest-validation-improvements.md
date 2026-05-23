# Wave 44 — v1.7.1 Export Bundle Polish & Validation

Goal: Improve export-bundle validation, examples, and adoption documentation while preserving the no-API-write boundary.

Release target: `v1.7.1`  
Branch target: `roadmap/v1.7.1-export-bundle-polish`  
Boundary: Repository-local export artifacts only. No Jira, Linear, GitHub Issues, Azure DevOps, or other external API writes.

# W44-S01 — Export Manifest Validation Improvements

Risk: Medium  
Slice type: Validation / schema hardening  
Artifact impact: Sidecar/export-bundle validation only

## Scope

Strengthen validation for `.ai-debt/export-bundles/manifest.json` so malformed, incomplete, inconsistent, or stale export bundle manifests are detected and reported clearly. This slice should validate the manifest after generation and should also support validation of an existing manifest without regenerating exports.

## Goals

- Add deterministic manifest validation.
- Detect missing tracker bundle entries.
- Detect missing artifact files referenced by the manifest.
- Detect unsupported tracker names or artifact types.
- Detect mismatched artifact counts.
- Detect duplicate artifact IDs or paths.
- Preserve graceful degradation: validation warnings should not crash generation unless a hard invariant is violated.
- Keep validation repository-local and offline.

## Patch Set

Expected files/modules:

```text
src/pharabius/schemas/export_bundles.py
src/pharabius/core/export_bundles.py
src/pharabius/core/export_bundle_validation.py      # new, if useful
tests/test_export_bundle_validation.py             # new
docs/EXPORT_BUNDLES.md                             # light reference update if needed
```

Recommended schema additions:

```python
class ExportBundleValidationIssue(BaseModel):
    severity: Literal["error", "warning"]
    code: str
    message: str
    tracker: str | None = None
    artifact_path: str | None = None

class ExportBundleValidationResult(BaseModel):
    valid: bool
    errors: list[ExportBundleValidationIssue] = []
    warnings: list[ExportBundleValidationIssue] = []
```

Recommended validation rules:

| Rule | Severity |
|---|---|
| Missing `manifest.json` | Error |
| Invalid manifest schema | Error |
| Unsupported tracker key | Error |
| Referenced artifact file missing | Error |
| Duplicate artifact path | Error |
| Empty tracker bundle when tracker requested | Warning |
| Artifact count mismatch | Warning |
| README missing from tracker bundle | Warning |

## Tests

Add tests for valid manifest, missing manifest, missing referenced artifact, duplicate artifact path, unsupported tracker name, artifact count mismatch, empty requested tracker bundle, deterministic validation output, and no external API calls.

## Targeted Verification

```bash
pytest tests/test_export_bundle_validation.py
python -m pharabius.cli tickets --help
python -m pharabius.cli export --help
```

## Expected Behavior

After export bundle generation, Pharabius can produce a validation result showing whether the manifest is internally consistent. Invalid manifests produce structured, actionable errors and warnings.

## Acceptance Criteria

- Manifest validation exists and is covered by tests.
- Valid manifests pass with zero errors.
- Invalid manifests fail with structured, actionable issues.
- Warnings are distinguished from errors.
- No canonical artifacts are mutated.
- No scoring behavior changes.
- No external tracker API behavior is introduced.
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

