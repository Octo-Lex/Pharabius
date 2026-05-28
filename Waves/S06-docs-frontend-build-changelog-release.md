# v2.2.3 — Frontend MVP & Upload UX

Goal: Replace the static frontend scaffold with a minimal usable UI for upload, repository browsing, findings, and portfolio summary, using the now-runtime-validated backend APIs.

Release posture: hosted-platform frontend MVP release. This release should make the platform usable through the browser, but it must not add OAuth, RBAC, policy engine, tracker writes, PR comments, background workers, or remediation.

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
- Backend changes limited to API shape fixes required by the frontend


# S06 — Docs, Frontend Build Validation, Changelog, Release

Risk: Low  
Slice type: release finalization  
Artifact impact: docs, changelog, roadmap, version

## Scope

Finalize v2.2.3 documentation, frontend build validation, changelog, roadmap updates, limitations, and release notes.

This slice must accurately distinguish what is now browser-usable from what remains deferred.

## Goals

- Bump version to `2.2.3`.
- Update changelog and roadmap.
- Document frontend MVP usage.
- Document upload warning and artifact sensitivity.
- Document API base URL configuration.
- Document frontend build command.
- Update known limitations.
- Confirm backend tests, CLI tests, and frontend build pass.

## Patch Set

Expected files:

```text
CHANGELOG.md
docs/ROADMAP.md
KNOWN_LIMITATIONS.md
platform/docs/README.md
platform/docs/frontend-mvp.md
platform/docs/troubleshooting.md
platform/frontend/README.md
```

Required limitation notes:

```text
No GitHub OAuth/RBAC
No policy engine
No tracker writes
No background workers
No mobile-first UX
No formal browser E2E suite unless added
Frontend is MVP-quality
```

Recommended changelog entry:

```markdown
## v2.2.3

### Improved
- Replaced static platform frontend scaffold with a minimal routed React/Vite UI.
- Added repository list and repository dashboard screens.
- Added findings table with basic filters.
- Added manual artifact upload page with validation feedback.
- Added portfolio summary screen.
- Added shared empty/loading/error states.

### Safety
- The platform still ingests Pharabius artifacts, not repositories.
- Upload UI warns that `.ai-debt` bundles may contain source-derived evidence snippets, file paths, hashes, and analysis metadata.
- No OAuth, RBAC, policy engine, tracker writes, PR comments, or remediation were added.
```

## Tests

Final verification:

```bash
pytest
pytest platform/backend/tests
npm --prefix platform/frontend install
npm --prefix platform/frontend run build
python -m build
python scripts/validate_repo.py .
```

Optional runtime verification:

```bash
platform/scripts/smoke_docker_compose.sh
```

## Expected Behavior

v2.2.3 is ready for PR, CI, merge, tag, and release.

## Acceptance Criteria

- Version is `2.2.3`.
- Frontend build passes.
- Docs accurately describe frontend MVP.
- Known limitations are updated.
- Backend tests continue passing.
- CLI tests continue passing.
- Release notes do not overclaim production maturity.

## Guardrails

- Preserve the v2.2.2 runtime-validated backend path.
- Do not introduce new backend product capability except minor API response-shape fixes needed by the UI.
- Do not add external writes.
- Do not add repository cloning or source-code upload.
- Do not add OAuth, RBAC, policy engine, tracker writes, PR comments, or remediation.
- Keep frontend MVP desktop-oriented.
- Keep charts optional; tables and summary cards are sufficient.
- Make empty/loading/error states explicit and useful.
- Keep source-derived artifact warning visible on upload.


## Verification Commands

Run the standard gates plus frontend-specific checks:

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
```

Optional runtime verification when Docker is available:

```bash
platform/scripts/smoke_docker_compose.sh
```
