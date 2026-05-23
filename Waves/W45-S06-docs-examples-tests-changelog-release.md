# Wave 45 — v1.8.0 Portfolio Summary Foundation

Goal: Add repository-local portfolio summary artifacts that consolidate one or more Pharabius runs into a lightweight portfolio view, without adding a server, dashboard, scheduler, database, remote repository crawler, or external integration.

Release target: `v1.8.0`  
Branch target: `roadmap/v1.8.0-portfolio-summary`  
Boundary: File-based, repository-local or workspace-local portfolio summaries only.

# W45-S06 — Docs, Examples, Tests, Changelog, Release

Risk: Low  
Slice type: Release finalization  
Artifact impact: Version, docs, examples, changelog, roadmap

## Scope

Finalize v1.8.0 release documentation, examples, version metadata, changelog, roadmap, known limitations, and release notes.

This slice should not add new runtime behavior beyond final wiring or documentation corrections required by earlier slices.

## Goals

- Bump version to `1.8.0`.
- Add or finalize `docs/PORTFOLIO.md`.
- Add portfolio examples.
- Update CLI documentation.
- Update `CHANGELOG.md`.
- Update `ROADMAP.md`.
- Update `KNOWN_LIMITATIONS.md`.
- Confirm build artifact uses version `1.8.0`.
- Confirm all 7 gates pass.
- Prepare release notes.

## Patch Set

Expected files:

```text
pyproject.toml
CHANGELOG.md
ROADMAP.md
KNOWN_LIMITATIONS.md
docs/PORTFOLIO.md
docs/examples/portfolio/portfolio-summary.example.json
docs/examples/portfolio/portfolio-summary.example.md
docs/examples/portfolio/repository-index.example.json
docs/examples/portfolio/validation-rollup.example.md
```

Recommended docs structure:

```markdown
# Portfolio Summary

## Purpose
## Safety boundary
## Artifact layout
## Generating a portfolio summary
## Single-repository mode
## Multi-repository mode
## Reading portfolio risk rollups
## Reading readiness rollups
## Known limitations
## What Pharabius intentionally does not do
```

Recommended changelog entry:

```markdown
## v1.8.0

### Added
- Repository-local portfolio summary artifacts.
- Portfolio repository index.
- Portfolio risk and category rollups.
- Portfolio readiness and validation rollups.
- `ai-debt portfolio` command.
- Portfolio examples and documentation.

### Safety
- No server, dashboard, scheduler, database, remote repository crawling, or external API calls.
- No canonical debt register or work package mutation.
- No scoring behavior changes.
```

## Tests

No new feature tests required unless examples/docs require validation tests.

Recommended example tests:

- Example JSON files parse.
- Example Markdown files exist.
- Docs mention no remote crawling or API calls.
- CLI docs include `ai-debt portfolio`.

## Targeted Verification

```bash
python -m build
grep -R "v1.8.0" CHANGELOG.md ROADMAP.md
grep -R "ai-debt portfolio" docs README.md || true
pytest
```

## Expected Behavior

The release is ready for PR, CI, merge, tag, and GitHub Release.

Expected release line:

```text
Pharabius v1.8.0 adds repository-local portfolio summary artifacts and an `ai-debt portfolio` command for consolidating technical debt risk and readiness across analyzed repositories.
```

## Acceptance Criteria

- Version is `1.8.0`.
- Build output is `pharabius-1.8.0`.
- Portfolio docs exist and are linked coherently.
- Changelog, roadmap, and known limitations are updated.
- Portfolio examples are present and parseable.
- All 7 local gates pass.
- No new runtime scope beyond approved Wave 45 slices.
- No external API calls.
- No canonical artifact mutation.
- No scoring behavior changes.
## Guardrails

- Do not add a dashboard, web server, API server, scheduler, queue, or persistent database.
- Do not crawl remote repositories or organizations.
- Do not call GitHub, GitLab, Bitbucket, Jira, Linear, Azure DevOps, or other external APIs.
- Do not create or modify external issues.
- Do not mutate source repositories outside Pharabius output directories.
- Do not mutate source `.ai-debt/debt-register.json` files during aggregation.
- Do not change risk scoring behavior.
- Do not let review sidecar decisions influence scores.
- Do not introduce autonomous remediation or code modification.
- Treat portfolio output as a read-only rollup over existing Pharabius artifacts.

## Verification Commands

Run the full local gate suite:

```bash
ruff format --check .
ruff check .
mypy src
lint-imports
pytest
python -m build
python scripts/validate_repo.py .
```

Additional targeted checks for this slice are listed below.

