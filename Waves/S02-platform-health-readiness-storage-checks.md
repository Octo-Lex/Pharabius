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


# S02 — Platform Health, Readiness, and Storage Checks

Risk: Medium  
Slice type: Operational hardening  
Artifact impact: health/readiness endpoints, storage checks, tests

## Scope

Strengthen hosted platform health and readiness diagnostics so operators can distinguish process liveness, database connectivity, storage availability, and upload readiness.

## Goals

- Keep `GET /api/v1/health` lightweight and liveness-oriented.
- Add `GET /api/v1/readiness` for dependency checks.
- Add storage path checks.
- Add database connectivity checks.
- Add bundle storage writability checks.
- Add optional disk-space warning if available.
- Document how Docker and operators should use these endpoints.

## Patch Set

Expected files/modules:

```text
platform/backend/src/pharabius_platform/api/health.py
platform/backend/src/pharabius_platform/services/storage.py
platform/backend/src/pharabius_platform/schemas/health.py
platform/backend/tests/test_platform_health_readiness.py
platform/docker-compose.yml
platform/docs/deployment.md
```

Recommended endpoint behavior:

| Endpoint | Purpose | Should fail if DB down? |
|---|---|---|
| `/api/v1/health` | process liveness | No |
| `/api/v1/readiness` | service readiness | Yes |
| `/api/v1/storage` or readiness section | storage diagnostics | Yes if required storage unavailable |

Recommended readiness response:

```json
{
  "status": "ready | degraded | not_ready",
  "checks": [
    {"name": "database", "status": "pass", "message": "Connected"},
    {"name": "bundle_storage", "status": "pass", "message": "Writable"},
    {"name": "migrations", "status": "pass", "message": "Up to date"}
  ]
}
```

## Tests

Add tests for:

- Health returns 200 without requiring DB interaction.
- Readiness passes when DB/storage are available.
- Readiness reports failure when storage path is missing.
- Readiness reports failure when storage path is not writable.
- Readiness response uses standard shape.
- Docker Compose healthcheck uses correct endpoint.
- No sensitive environment variables appear in health/readiness output.

## Targeted Verification

```bash
pytest platform/backend/tests/test_platform_health_readiness.py
cd platform && docker compose config
```

## Expected Behavior

Operators can quickly determine whether the platform process is alive and whether it can actually ingest artifact bundles.

## Acceptance Criteria

- Health and readiness endpoints have distinct semantics.
- Storage and database status are visible.
- Docker Compose uses health/readiness appropriately.
- No secrets are exposed.
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
