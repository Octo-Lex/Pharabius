# v2.2.2 — Platform Runtime Validation & Frontend MVP

Goal: Verify the hosted platform against a real PostgreSQL/Docker runtime and replace the static frontend scaffold with a minimal usable UI for upload, repository view, findings, and portfolio summary.

Release posture: hosted-platform hardening release. This release should make the v2.2 platform demonstrably runnable and minimally usable, without adding governance, tracker, remediation, or automation scope.

Core boundaries:
- No GitHub OAuth
- No RBAC
- No policy engine
- No tracker writes
- No PR comments
- No background workers
- No source-code upload by default
- No autonomous remediation
- No production code modification


# S06 — Docs, Limitations, Changelog, Release

Risk: Low  
Slice type: release finalization  
Artifact impact: docs, changelog, roadmap, version

## Scope

Finalize v2.2.2 documentation, limitations, validation instructions, changelog, and release notes.

This slice must be honest about what is now verified and what remains unverified.

## Goals

- Bump version to `2.2.2`.
- Update changelog and roadmap.
- Document Docker runtime validation.
- Document PostgreSQL integration test path.
- Document frontend MVP usage.
- Update platform known limitations.
- Add runtime troubleshooting.
- Confirm CLI tests and platform tests pass.
- Confirm build artifacts are produced.

## Patch Set

Expected files:

```text
CHANGELOG.md
docs/ROADMAP.md
KNOWN_LIMITATIONS.md
platform/docs/README.md
platform/docs/runtime-validation.md
platform/docs/postgres-testing.md
platform/docs/frontend-mvp.md
platform/docs/troubleshooting.md
```

Required limitation notes:

- Frontend is MVP-quality, not full UX.
- Browser E2E testing remains limited or deferred unless implemented.
- No GitHub OAuth/RBAC.
- No policy engine.
- No tracker writes.
- No background workers.
- No load testing.
- Docker runtime smoke test may require local Docker availability.

Recommended changelog entry:

```markdown
## v2.2.2

### Improved
- Added Docker Compose runtime smoke validation path.
- Added real PostgreSQL integration test path.
- Replaced static frontend scaffold with minimal routed UI.
- Added upload, repository, findings, and portfolio frontend screens.
- Added frontend empty/loading/error states.

### Safety
- The platform still ingests Pharabius artifacts, not repositories.
- No tracker writes, PR comments, policy engine, RBAC, OAuth, or remediation were added.
```

## Tests

Final verification:

```bash
pytest
pytest platform/backend/tests
npm --prefix platform/frontend run build
python -m build
python scripts/validate_repo.py .
```

Optional Docker verification:

```bash
platform/scripts/smoke_docker_compose.sh
```

## Acceptance Criteria

- Version is `2.2.2`.
- Build output reflects `2.2.2`.
- Docs accurately describe verified runtime behavior.
- Platform limitations are updated.
- All CLI tests pass.
- Platform backend tests pass.
- Frontend build passes.
- Docker smoke path exists and is documented.

## Guardrails

- Preserve the v2.2.1 platform persistence model.
- Do not add external tracker writes.
- Do not add PR comments, GitHub Checks API, or issue creation.
- Do not add repository cloning.
- Do not require source-code upload.
- Do not introduce policy engine behavior.
- Do not add remediation or patch generation.
- Keep frontend MVP focused on upload, repository summary, findings, and portfolio state.
- Keep Docker/PostgreSQL validation practical and repeatable.


## Verification Commands

Run the standard gates plus platform-specific checks:

```bash
ruff format --check .
ruff check .
mypy src
lint-imports
pytest
python -m build
python scripts/validate_repo.py .
pytest platform/backend/tests
npm --prefix platform/frontend install
npm --prefix platform/frontend run build
docker compose -f platform/docker-compose.yml config
```

When Docker is available for runtime validation:

```bash
docker compose -f platform/docker-compose.yml up --build -d
curl -f http://localhost:8000/api/v1/health
curl -f http://localhost:3000/
docker compose -f platform/docker-compose.yml down -v
```
