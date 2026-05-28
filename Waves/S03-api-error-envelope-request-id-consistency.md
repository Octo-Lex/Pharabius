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


# S03 — API Error Envelope Consistency and Request ID Propagation

Risk: Medium  
Slice type: API consistency / diagnostics  
Artifact impact: API middleware, error responses, tests

## Scope

Ensure every platform API error returns the standard error envelope introduced in v2.2.0 and includes a request ID that is propagated through responses and logs.

## Goals

- Add or harden request ID middleware.
- Return `X-Request-ID` response header for all API responses.
- Preserve incoming `X-Request-ID` when valid, otherwise generate one.
- Ensure validation errors use the standard error envelope.
- Ensure authentication errors use the standard error envelope.
- Ensure upload errors use the standard error envelope.
- Ensure unexpected exceptions are converted to safe 500 envelopes.

## Patch Set

Expected files/modules:

```text
platform/backend/src/pharabius_platform/middleware/request_id.py
platform/backend/src/pharabius_platform/middleware/errors.py
platform/backend/src/pharabius_platform/schemas/errors.py
platform/backend/src/pharabius_platform/main.py
platform/backend/tests/test_error_envelope_consistency.py
```

Standard error response:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Request validation failed.",
    "details": {},
    "request_id": "req_..."
  }
}
```

Recommended error codes:

| Code | Status |
|---|---:|
| `unauthorized` | 401 |
| `forbidden` | 403 |
| `not_found` | 404 |
| `validation_error` | 422 |
| `artifact_validation_failed` | 400 or 200 with validation status, depending on case |
| `upload_too_large` | 413 |
| `unsupported_media_type` | 415 |
| `internal_error` | 500 |

## Tests

Add tests for:

- 401 response uses error envelope.
- 404 response uses error envelope.
- 422 validation error uses error envelope.
- Oversized upload uses error envelope.
- Path traversal upload uses error envelope.
- Unexpected exception uses safe error envelope.
- `X-Request-ID` header appears on success and error responses.
- Provided request ID is propagated when safe.
- Request ID appears in error body.
- Error body never includes raw stack trace or secrets.

## Targeted Verification

```bash
pytest platform/backend/tests/test_error_envelope_consistency.py
```

## Expected Behavior

API consumers, CI upload users, and operators can consistently correlate API errors to request IDs and logs.

## Acceptance Criteria

- All API error paths use the standard envelope.
- Request ID is propagated on success and failure.
- Error responses are safe and non-leaky.
- Existing API clients still receive useful status codes.
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
