# v2.3.1 — Review Workflow Polish & Evidence Linking

Goal: Improve finding-review usability by surfacing review filters, audit details, evidence links, decision completeness, and review summary clarity without expanding into claims/gaps/readiness review.

Release posture: patch release for the hosted finding-review workflow.

Core boundaries:
- No claim review, gap closure tracking, readiness sign-off, or work-package review expansion
- No OAuth / RBAC
- No policy engine
- No tracker writes, PR comments, notifications, or webhooks
- No autonomous remediation or source-code modification
- Review decisions remain hosted workflow state, not canonical analyzer truth

Guardrails:
- Do not mutate uploaded `.ai-debt` bundles.
- Do not mutate canonical finding records.
- Do not change finding severity, risk score, evidence, category, or source content.
- Preserve soft-delete and audit history from v2.3.0.
- Keep the scope limited to finding-review usability.


# S06 — Docs, Tests, Changelog, Release

Risk: Low

## Scope

Finalize v2.3.1 documentation, tests, limitations, changelog, roadmap, and release notes.

This slice must state clearly that v2.3.1 improves finding-review usability only and does not expand into claims/gaps/readiness review.

## Goals

- Bump version to `2.3.1`.
- Update changelog.
- Update roadmap.
- Update platform review docs.
- Update known limitations.
- Verify frontend build.
- Verify backend/platform tests.
- Verify CLI tests unchanged.
- Prepare release notes.

## Patch Set

Expected files:

```text
CHANGELOG.md
docs/ROADMAP.md
KNOWN_LIMITATIONS.md
platform/docs/review-workflow.md
platform/docs/review-statuses.md
platform/docs/audit-history.md
platform/docs/review-summary.md
platform/docs/README.md
platform/frontend/README.md
```

Required limitation statements:

```text
v2.3.1 does not add claim review.
v2.3.1 does not add gap closure tracking.
v2.3.1 does not add readiness sign-off.
v2.3.1 does not add work-package review expansion.
v2.3.1 does not add OAuth/RBAC, policy engine, tracker writes, PR comments, or remediation.
```

Recommended changelog entry:

```markdown
## v2.3.1

### Improved
- Added review filters for decided, undecided, and status-specific finding views.
- Added finding and evidence context to the review modal.
- Improved review audit timeline readability.
- Added review completeness and summary metrics.
- Added documentation for finding-review workflow and audit semantics.

### Safety
- Review decisions remain hosted workflow state and do not mutate uploaded Pharabius artifacts or canonical finding records.
- No claim review, gap closure, readiness sign-off, policy engine, tracker writes, PR comments, or remediation were added.
```

## Acceptance Criteria

- Version is `2.3.1`.
- Changelog and roadmap are updated.
- Docs clearly describe finding-review scope.
- Backend tests pass.
- Frontend build passes.
- CLI tests pass.
- Release notes do not overclaim broader human validation.

## Verification Commands

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
