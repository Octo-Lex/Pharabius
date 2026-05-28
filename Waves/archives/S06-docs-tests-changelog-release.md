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


# S06 — Docs, Tests, Changelog, Release

Risk: Low  
Slice type: Release finalization  
Artifact impact: version, changelog, docs, roadmap

## Scope

Finalize the v2.2.1 patch release with accurate documentation, tests, changelog, roadmap updates, and release notes.

No new runtime behavior should be added in this slice beyond final wiring or documentation corrections required by earlier slices.

## Goals

- Bump version to `2.2.1`.
- Update `CHANGELOG.md`.
- Update `ROADMAP.md` or `docs/ROADMAP.md` as appropriate.
- Update hosted platform docs index.
- Confirm platform docs link coherently.
- Confirm CLI docs mention `ai-debt upload` accurately.
- Confirm all CLI tests still pass.
- Confirm all platform backend tests pass.
- Confirm frontend build passes.
- Confirm Docker Compose config validates.
- Prepare GitHub Release notes.

## Patch Set

Expected files:

```text
pyproject.toml
platform/backend/pyproject.toml
platform/frontend/package.json                 # only if version tracked here
CHANGELOG.md
docs/ROADMAP.md
platform/docs/README.md
platform/docs/deployment.md
platform/docs/backup-restore.md
platform/docs/security-checklist.md
```

Recommended changelog entry:

```markdown
## v2.2.1

### Improved
- Upload diagnostics and validation report readability.
- Platform health/readiness and storage checks.
- API error envelope consistency and request ID propagation.
- Frontend empty/loading/error states.
- Docker Compose, deployment, storage, and backup documentation.

### Safety
- No GitHub OAuth, tracker writes, PR comments, repository cloning, policy engine, or remediation added.
- Uploaded `.ai-debt` bundles remain treated as potentially sensitive source-derived artifacts.
```

## Tests

Run all tests and platform checks.

Recommended final verification:

```bash
pytest
cd platform/backend && pytest
cd ../frontend && npm run build
cd .. && docker compose config
python -m build
python scripts/validate_repo.py .
```

## Expected Behavior

v2.2.1 is ready for PR, CI, merge, tag, and GitHub Release as a hosted-platform hardening patch.

## Acceptance Criteria

- Version is `2.2.1`.
- Changelog and roadmap are updated.
- Hosted platform docs are coherent.
- All platform and CLI tests pass.
- Frontend build passes.
- Docker Compose config validates.
- No new product capability beyond hardening/polish.
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
