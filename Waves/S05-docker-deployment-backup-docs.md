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


# S05 — Docker Compose, Deployment, and Backup Documentation

Risk: Low-medium  
Slice type: Operational documentation / configuration hardening  
Artifact impact: Docker docs, deployment docs, `.dockerignore`, backup guidance

## Scope

Improve operator-facing documentation and configuration for running the hosted platform safely in Docker Compose and basic self-hosted environments.

## Goals

- Clarify dev vs production Docker Compose usage.
- Document required environment variables.
- Document `ADMIN_TOKEN` and upload token handling.
- Document PostgreSQL backup/restore basics.
- Document bundle storage backup requirements.
- Add storage retention warning.
- Add disk-space guidance.
- Ensure `.dockerignore` prevents large/sensitive build contexts.
- Document that `.ai-debt` bundles may contain source-derived evidence.

## Patch Set

Expected files:

```text
platform/docs/deployment.md
platform/docs/backup-restore.md
platform/docs/storage.md
platform/docs/security-checklist.md
platform/docker-compose.yml
platform/backend/.dockerignore
platform/frontend/.dockerignore
```

Recommended docs sections:

```markdown
# Deployment
## Local development
## Production warning
## Required environment variables
## Database setup
## Bundle storage
## Backups
## Restore
## Disk space
## Security checklist
## What the platform does not do
```

Required warnings:

```text
Uploaded .ai-debt bundles may contain source-derived evidence, file paths, hashes, analysis metadata, operational claims, and generated reports.
Back up PostgreSQL and bundle storage together.
Do not use the default development ADMIN_TOKEN in production.
```

## Tests / Static Checks

Add tests or static checks for:

- `.dockerignore` exists for backend and frontend.
- Deployment docs mention `ADMIN_TOKEN`.
- Backup docs mention database and bundle storage.
- Docs mention `.ai-debt` bundles may contain source-derived evidence.
- Docker Compose config validates.

## Targeted Verification

```bash
cd platform && docker compose config
pytest platform/backend/tests/test_platform_docs_static.py
```

## Expected Behavior

Operators understand how to deploy, back up, and secure the platform at a basic level.

## Acceptance Criteria

- Deployment docs are coherent.
- Backup/restore docs exist.
- Storage docs exist.
- `.dockerignore` files exist and exclude obvious heavy/sensitive paths.
- Production warnings are explicit.
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
