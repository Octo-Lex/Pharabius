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


# S05 — Claims/Gaps/Readiness Views and CI Upload Token Flow

Risk: High  
Slice type: Hosted review visibility + CI ingestion auth  
Artifact impact: Read-only UI plus upload-token credentials

## Scope

Add hosted views for operational claims, gaps, questions, readiness, and introduce scoped CI upload tokens for artifact-bundle upload.

This slice adds the first credential-bearing workflow. It must remain narrow: upload tokens permit artifact upload only, not repository access, tracker writes, or administrative actions.

## Goals

- Add claims browser.
- Add gaps/questions browser.
- Add readiness view.
- Add CI upload token model.
- Add token creation/revocation endpoint.
- Add token-authenticated upload endpoint or upload mode.
- Ensure tokens are scoped to organization/project/repository.
- Hash tokens at rest.
- Show token only once on creation.
- Add audit event for token creation/revocation/upload.
- Preserve read-only artifact ingestion behavior.

## Patch Set

Expected files/modules:

```text
src/pharabius_platform/api/claims.py
src/pharabius_platform/api/readiness.py
src/pharabius_platform/api/upload_tokens.py
src/pharabius_platform/security_tokens.py
src/pharabius_platform/models.py
src/pharabius_platform/audit.py
tests/platform/test_claims_gaps_api.py
tests/platform/test_readiness_api.py
tests/platform/test_upload_tokens.py
tests/platform/test_ci_upload_auth.py
```

Recommended token permissions:

```text
artifact_bundle:upload
artifact_bundle:read_status
```

Not allowed:

```text
repository:clone
tracker:write
issue:create
policy:write
user:admin
```

Recommended token fields:

```python
UploadToken:
  id
  repository_id
  name
  token_hash
  created_at
  revoked_at
  last_used_at
  expires_at
  scopes
```

Recommended views:

```text
Claims:
  confirmed / inferred / gap filters
  confidence filters
  linked findings
  evidence references

Gaps:
  blocking / non-blocking
  linked claims/findings/work packages
  validation question

Readiness:
  latest readiness state
  missing artifacts
  recommended actions
```

## Tests

Add tests for:

- Claims browser API returns claims.
- Gaps browser API returns blocking/non-blocking gaps.
- Readiness API handles unknown status.
- Token creation returns secret once.
- Token secret is hashed at rest.
- Revoked token cannot upload.
- Expired token cannot upload.
- Token without upload scope cannot upload.
- Token upload cannot access other repository.
- CI upload still validates artifact contract.
- Audit event is recorded for upload.

## Targeted Verification

```bash
pytest tests/platform/test_claims_gaps_api.py
pytest tests/platform/test_readiness_api.py
pytest tests/platform/test_upload_tokens.py
pytest tests/platform/test_ci_upload_auth.py
```

## Expected Behavior

CI can upload `.ai-debt` bundles using a scoped upload token. Users can inspect claims, gaps, questions, and readiness in the hosted platform.

## Acceptance Criteria

- Claims/gaps/readiness views exist.
- Upload tokens are scoped and hashed.
- Token creation/revocation is tested.
- CI upload uses upload-only permission.
- Tokens cannot perform external writes.
- Upload endpoint remains artifact-only.
- Audit events exist for token lifecycle and uploads.
- All tests pass.
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
