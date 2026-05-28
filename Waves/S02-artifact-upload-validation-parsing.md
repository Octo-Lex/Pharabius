# v2.2 — Hosted Platform Foundation + CI Ingestion

Goal: Build the first hosted Pharabius platform for artifact ingestion, repository/portfolio visibility, trend review, claims/gaps inspection, and CI upload — without source-code storage, repository cloning, tracker writes, PR comments, issue creation, or remediation.

Release target: `v2.2.0`  
Branch target: `roadmap/v2.2.0-hosted-platform-foundation`  
Posture: Large release, category change, strict MVP boundary.

Primary product loop:

```text
Run Pharabius locally or in CI
→ generate .ai-debt artifacts
→ upload artifact bundle
→ validate artifact contract
→ parse normalized records
→ view repository dashboard
→ view portfolio dashboard
→ inspect findings, trends, claims, gaps, gates, and readiness
```


# S02 — Artifact Upload API, Validation, and Parsing Pipeline

Risk: High  
Slice type: Ingestion / security-sensitive upload processing  
Artifact impact: Hosted storage and normalized records only

## Scope

Implement manual `.ai-debt` artifact bundle upload, validation, and parsing into normalized hosted-platform records.

This slice is the critical ingestion foundation. It must be secure, bounded, and honest about unsupported artifacts.

## Goals

- Add artifact bundle upload endpoint.
- Support `.zip` upload containing `.ai-debt/` artifacts.
- Add file size limits.
- Add content-type and extension checks.
- Add zip safety checks.
- Validate artifact contract using existing Pharabius artifact-contract logic.
- Parse core artifacts into hosted entities.
- Store raw uploaded bundle in controlled storage path.
- Emit structured ingestion errors and warnings.
- Preserve no-source-code-storage-by-default posture.

## Patch Set

Expected files/modules:

```text
src/pharabius_platform/uploads.py
src/pharabius_platform/ingestion.py
src/pharabius_platform/artifact_parser.py
src/pharabius_platform/storage.py
src/pharabius_platform/security_uploads.py
tests/platform/test_artifact_upload_api.py
tests/platform/test_artifact_validation.py
tests/platform/test_artifact_parsing.py
tests/fixtures/platform/bundles/
```

Recommended upload endpoint:

```http
POST /api/v1/repositories/{repository_id}/artifact-bundles
Content-Type: multipart/form-data
file=.ai-debt-bundle.zip
```

Recommended validation controls:

| Control | Required |
|---|---|
| Max upload size | Yes |
| Zip bomb prevention | Yes |
| Path traversal prevention | Yes |
| Reject absolute paths | Yes |
| Reject `..` paths | Yes |
| Require `.ai-debt/` root or equivalent | Yes |
| Validate required artifacts | Yes |
| Warn on optional missing artifacts | Yes |
| Store ingestion warnings | Yes |

Recommended parsed artifacts:

```text
debt-register.json → Finding records + run summary
reports/quality-gate.md → gate result if parseable
trends/trend-summary.json → TrendPoint records
claims/operational-claims.json → OperationalClaim records
claims/gaps.md or structured gap data → Gap records when parseable
reports/v1-readiness or readiness output → ReadinessSnapshot if available
```

If data is not structured, store an `insufficient_data` or warning state rather than fabricating it.

## Tests

Add tests for:

- Valid bundle upload succeeds.
- Missing `.ai-debt` bundle fails gracefully.
- Oversized upload rejected.
- Zip path traversal rejected.
- Absolute path in zip rejected.
- Missing required artifact produces validation error.
- Missing optional artifact produces warning.
- Debt register parsed into findings.
- Trend summary parsed when present.
- Operational claims parsed when present.
- Gate status parsed only if supported.
- Upload does not require source-code files.
- Raw source files in bundle are ignored or flagged depending policy.

## Targeted Verification

```bash
pytest tests/platform/test_artifact_upload_api.py
pytest tests/platform/test_artifact_validation.py
pytest tests/platform/test_artifact_parsing.py
```

## Expected Behavior

A user can upload an `.ai-debt` bundle and see a validated ingestion record.

The platform stores artifact-derived records, not repository source code.

## Acceptance Criteria

- Upload endpoint exists and is test-covered.
- Unsafe zip inputs are rejected.
- Artifact contract validation is reused or mirrored from existing logic.
- Core records are parsed deterministically.
- Missing data becomes warnings or insufficient-data states.
- No external API calls occur.
- No tracker writes occur.
- No source-code upload is required.
- All local and platform tests pass.
## Guardrails

- Do not require source-code upload.
- Do not clone repositories.
- Do not store full source files by default.
- Do not create issues, PR comments, tracker items, or external writes.
- Do not call Jira, Linear, GitHub Issues, Azure DevOps, GitHub, GitLab, or other external write APIs.
- Do not upload SARIF to code scanning by default.
- Do not perform autonomous remediation.
- Do not generate patches.
- Do not modify production code.
- Treat uploaded `.ai-debt` bundles as analysis artifacts, not as implementation authority.
- Keep v2.2 hosted behavior read-only with respect to source systems.


## Verification Commands

Minimum local verification:

```bash
ruff format --check .
ruff check .
mypy src
lint-imports
pytest
python -m build
python scripts/validate_repo.py .
```

Hosted-platform verification should additionally include the new platform checks introduced in this release, such as API tests, database migration checks, frontend checks, and Docker Compose smoke tests.
