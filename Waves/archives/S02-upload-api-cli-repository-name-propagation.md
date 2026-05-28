# v2.2.4 — Repository Identity & Upload UX Patch

Goal: Fix repository identity handling so uploaded bundles produce human-readable repository names across backend persistence, frontend display, and `ai-debt upload`.

Release posture: focused patch release. This release should fix the hash-named repository usability problem without adding new product capability.

Core boundaries:
- No OAuth
- No RBAC
- No API key management UI
- No claims/gaps/readiness UI
- No policy engine
- No tracker writes
- No PR comments
- No repository cloning
- No remediation
- No source-code modification


# S02 — Upload API and CLI Repository-Name Propagation

Risk: Medium  
Slice type: upload API + CLI patch  
Artifact impact: `POST /api/v1/bundles`, `ai-debt upload`

## Scope

Ensure repository names are passed from browser/API/CLI upload into backend persistence.

## Goals

- Confirm `POST /api/v1/bundles` accepts `repository_name` as multipart form field.
- Ensure upload endpoint passes `repository_name` to repository identity resolution.
- Add `ai-debt upload --repository-name`.
- Default CLI repository name to current directory name when flag absent.
- Preserve hash fallback when neither explicit nor derived name is available.
- Print repository name in upload success output.

## Patch Set

Expected files:

```text
platform/backend/src/pharabius_platform/api/upload.py
platform/backend/src/pharabius_platform/services/parser.py
pharabius/src/pharabius/core/uploader.py
pharabius/src/pharabius/cli.py
platform/backend/tests/test_upload_repository_identity.py
tests/test_cli_upload.py
```

Recommended CLI:

```bash
ai-debt upload \
  --url http://localhost:8000 \
  --token "$PHARABIUS_UPLOAD_TOKEN" \
  --repository-name Pharabius
```

Default behavior:

```text
If --repository-name is omitted:
  default to current working directory name.
```

Success output should include:

```text
Uploaded bundle
Repository: Pharabius
Bundle ID: ...
Validation: valid
```

## Tests

Add tests for:

- Upload API receives `repository_name`.
- Upload API persists repository name.
- Upload API uses hash fallback only when name unavailable.
- CLI sends `repository_name` when flag provided.
- CLI defaults repository name to current directory name.
- CLI success output includes repository name.
- CLI error output does not leak token.

## Expected Behavior

Browser upload and `ai-debt upload` both preserve human-readable repository names.

## Acceptance Criteria

- `repository_name` is accepted by upload API.
- `ai-debt upload --repository-name` exists.
- CLI default repository name is useful.
- Backend tests prove persistence.
- Existing upload behavior remains backward-compatible.

## Guardrails

- Keep this patch narrow.
- Do not change the hosted platform’s persistence model beyond repository identity resolution.
- Do not add external writes.
- Do not add authentication UI, OAuth, RBAC, policy engine, tracker writes, or remediation.
- Preserve the content-hash fallback only as a last resort.
- Preserve duplicate bundle handling.
- Keep source-derived artifact warnings intact.


## Verification Commands

Run:

```bash
ruff format --check .
ruff check .
mypy src
lint-imports
pytest
pytest platform/backend/tests
npm --prefix platform/frontend run build
python -m build
python scripts/validate_repo.py .
```

Optional runtime check:

```bash
platform/scripts/smoke_docker_compose.sh
```
