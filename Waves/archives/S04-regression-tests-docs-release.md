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


# S04 — Regression Tests, Docs, Changelog, Release

Risk: Low  
Slice type: release finalization  
Artifact impact: tests, docs, changelog, version

## Scope

Finalize the repository identity patch with regression coverage, documentation, limitations updates, changelog, and release notes.

## Goals

- Bump version to `2.2.4`.
- Add regression tests for repository-name handling.
- Update platform upload docs.
- Update CLI docs for `ai-debt upload --repository-name`.
- Update frontend docs.
- Update changelog and roadmap.
- Document fallback behavior honestly.
- Verify all standard gates pass.

## Patch Set

Expected files:

```text
CHANGELOG.md
docs/ROADMAP.md
KNOWN_LIMITATIONS.md
docs/CLI.md
platform/docs/README.md
platform/docs/frontend-mvp.md
platform/docs/upload.md
platform/frontend/README.md
```

Recommended changelog entry:

```markdown
## v2.2.4

### Fixed
- Preserved human-readable repository names during platform uploads.
- Added `ai-debt upload --repository-name`.
- Defaulted CLI upload repository name to the current directory name when no explicit name is provided.
- Updated frontend upload page to collect repository names.
- Labeled content-hash repository fallback as unknown/fallback.

### Safety
- No OAuth, RBAC, policy engine, tracker writes, PR comments, or remediation were added.
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

Optional runtime verification:

```bash
platform/scripts/smoke_docker_compose.sh
```

## Expected Behavior

v2.2.4 is ready for PR, CI, merge, tag, and release.

## Acceptance Criteria

- Version is `2.2.4`.
- Docs explain repository-name priority.
- Tests cover explicit name, CLI default, artifact-derived name, and hash fallback.
- Frontend build passes.
- Backend tests pass.
- CLI tests pass.
- Release notes do not overclaim broader platform maturity.

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
