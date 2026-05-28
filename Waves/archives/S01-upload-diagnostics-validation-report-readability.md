# v2.2.1 — Hosted Platform Hardening & UX Polish

Goal: Harden the hosted platform after the v2.2.0 category shift by improving upload diagnostics, platform health checks, API error consistency, frontend empty/error states, Docker/deployment documentation, and storage safety.

Release posture: patch release, not feature release.

Core boundary:
- No new product capability beyond hosted-platform hardening
- No GitHub OAuth
- No RBAC/user-account expansion
- No policy engine
- No tracker writes
- No PR comments
- No issue creation
- No SARIF upload
- No repository cloning
- No remediation
- No source-code modification


# S01 — Upload Diagnostics and Validation Report Readability

Risk: Medium  
Slice type: Upload diagnostics / report polish  
Artifact impact: API responses, platform validation reports, tests

## Scope

Improve the hosted platform upload flow so users can understand exactly what happened when a `.ai-debt` bundle is accepted, partially parsed, rejected, deduplicated, or marked invalid.

This slice should not change ingestion semantics except to make validation output clearer and more structured.

## Goals

- Return structured upload diagnostics from `POST /api/v1/bundles`.
- Improve validation report readability for missing, malformed, optional, and conditional artifacts.
- Clearly distinguish upload-level errors from artifact-validation warnings.
- Add parser diagnostics for skipped artifacts.
- Add duplicate-bundle diagnostics when SHA-256 already exists.
- Ensure `ai-debt upload` prints useful validation feedback.

## Patch Set

Expected files/modules:

```text
platform/backend/src/pharabius_platform/api/upload.py
platform/backend/src/pharabius_platform/services/validator.py
platform/backend/src/pharabius_platform/services/parser.py
platform/backend/src/pharabius_platform/schemas/upload.py
pharabius/src/pharabius/core/uploader.py
platform/backend/tests/test_upload_diagnostics.py
pharabius/tests/test_upload_cli.py
```

Recommended response shape:

```json
{
  "bundle_id": "uuid",
  "repository_id": "uuid",
  "content_hash": "sha256...",
  "stored": true,
  "duplicate": false,
  "validation": {
    "status": "valid | partial | invalid",
    "errors": [],
    "warnings": [],
    "missing_required": [],
    "missing_optional": [],
    "parsed_artifacts": [],
    "skipped_artifacts": []
  },
  "diagnostics": [
    "Bundle stored under content-addressed path.",
    "Parsed debt-register.json with 6 findings."
  ]
}
```

Recommended validation issue shape:

```python
class UploadValidationIssue(BaseModel):
    severity: Literal["error", "warning", "info"]
    code: str
    message: str
    artifact_path: str | None = None
    recommended_action: str | None = None
```

## Tests

Add tests for:

- Valid bundle returns readable diagnostics.
- Invalid bundle returns structured validation errors.
- Partial bundle returns warnings but stores bundle.
- Duplicate bundle returns `duplicate=true` and does not re-store file.
- Malformed artifact produces skipped-artifact diagnostic.
- Missing required artifact appears in `missing_required`.
- Missing optional artifact appears in `missing_optional`.
- CLI `ai-debt upload` prints bundle ID, status, warnings, and recommended actions.
- No raw token or sensitive header is included in diagnostics.

## Targeted Verification

```bash
pytest platform/backend/tests/test_upload_diagnostics.py
pytest pharabius/tests/test_upload_cli.py
```

## Expected Behavior

Users can diagnose upload results without reading backend logs.

Example CLI output:

```text
Upload complete: partial
Bundle: 7f3c...
Repository: service-a
Warnings: 2
- missing_optional: .ai-debt/trends/trend-summary.json not found
- skipped_artifact: claims file malformed; skipped claims projection
Reports parsed: debt-register.json, run metadata
```

## Acceptance Criteria

- Upload diagnostics are structured and test-covered.
- CLI upload output is actionable.
- Duplicate bundle handling is visible.
- Parser skips are visible.
- No secrets appear in upload diagnostics.
- No ingestion semantics are broadened beyond v2.2.0.
- All gates pass.

## Guardrails

- Preserve v2.2.0 architecture and product boundaries.
- Do not add external writes.
- Do not add repository cloning.
- Do not add OAuth or full user management.
- Do not add policy engine behavior.
- Do not add tracker integrations.
- Do not add background workers unless explicitly required for reliability; default is synchronous parsing.
- Do not mutate uploaded bundles after storage.
- Do not store raw API keys.
- Treat uploaded `.ai-debt` bundles as potentially sensitive source-derived artifacts.
- Keep all changes focused on diagnostics, safety, deployment readiness, and UX polish.


## Verification Commands

Run the full local gate suite for the CLI and platform:

```bash
ruff format --check .
ruff check .
mypy src
lint-imports
pytest
python -m build
python scripts/validate_repo.py .
```

Platform-specific verification should also run where available:

```bash
cd platform
# backend tests
cd backend && pytest
# frontend checks
cd ../frontend && npm test -- --run || true
cd ../frontend && npm run build
# docker smoke
cd .. && docker compose config
```
