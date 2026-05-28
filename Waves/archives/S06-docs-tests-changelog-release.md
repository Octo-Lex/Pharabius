# v2.3.0 — Human Validation Workflow

Goal: Turn findings, claims, gaps, readiness, and work packages into a hosted human-review workflow with review states, comments, audit history, and sign-off, without external writes or remediation.

Release posture: major hosted-platform workflow release. This release adds human review state and auditability inside the Pharabius platform, but must not create external issues, post PR comments, modify repositories, or perform remediation.

Core boundaries:
- No OAuth / RBAC
- No policy engine
- No tracker writes
- No PR comments
- No GitHub Checks API
- No external integrations
- No autonomous remediation
- No source-code modification
- No approval automation
- No replacement for Product Engineering Team responsibility


# S06 — Docs, Tests, Changelog, Release

Risk: Low  
Slice type: release finalization  
Artifact impact: docs, changelog, roadmap, version

## Scope

Finalize v2.3.0 documentation, tests, limitations, changelog, roadmap, and release notes.

This slice should clearly explain that review decisions are hosted human workflow state, not canonical analyzer truth.

## Goals

- Bump version to `2.3.0`.
- Update changelog.
- Update roadmap.
- Add human validation workflow documentation.
- Update platform docs/navigation.
- Update known limitations.
- Document review statuses and state transitions.
- Document audit history behavior.
- Document no-external-write boundary.
- Verify all backend/frontend/CLI gates pass.

## Patch Set

Expected files:

```text
CHANGELOG.md
docs/ROADMAP.md
KNOWN_LIMITATIONS.md
platform/docs/human-validation.md
platform/docs/review-state-machine.md
platform/docs/audit-history.md
platform/docs/README.md
platform/frontend/README.md
```

Required documentation statements:

```text
Review decisions do not mutate uploaded .ai-debt artifacts.
Review decisions do not change canonical findings, risk scores, evidence, or operational claims.
Review decisions are hosted platform workflow state.
The platform does not create external issues, PR comments, tracker items, or remediation patches.
```

Recommended changelog entry:

```markdown
## v2.3.0

### Added
- Hosted human validation workflow for findings, claims, gaps, readiness, and work packages where available.
- Review status model with accepted, rejected, needs_clarification, blocked, and validated states.
- Review comments and audit history.
- Review summary APIs and UI.

### Safety
- Review decisions are hosted platform workflow state and do not mutate uploaded Pharabius artifacts.
- No tracker writes, PR comments, policy engine, OAuth/RBAC, or remediation were added.
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

Optional runtime validation:

```bash
platform/scripts/smoke_docker_compose.sh
```

## Acceptance Criteria

- Version is `2.3.0`.
- Docs explain review workflow and boundaries.
- Backend review tests pass.
- Frontend build passes.
- CLI tests continue passing.
- Release notes do not overclaim governance automation.
- No external writes or remediation exist.


## Guardrails

- Review state is hosted platform state, not canonical analyzer truth.
- Do not mutate uploaded `.ai-debt` bundles.
- Do not mutate local Pharabius artifacts.
- Do not change scoring semantics.
- Do not let review decisions change canonical finding severity, risk score, evidence, or claim content.
- Do not create tickets, issues, PR comments, or tracker items.
- Do not add OAuth/RBAC in this release.
- Use admin token / existing platform auth model only.
- Preserve audit history for review changes.
- Keep all sign-off language human-owned, not automated approval.


## Verification Commands

Run the standard gates plus platform/frontend checks:

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

Optional runtime validation:

```bash
platform/scripts/smoke_docker_compose.sh
```
