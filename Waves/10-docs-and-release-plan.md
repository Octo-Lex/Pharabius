# Pharabius v2.0 — Local CI Quality Gate

Product thesis: Pharabius v2.0 enters developer workflow through a local, deterministic CI quality gate without becoming infrastructure.

Core boundary:
- No server
- No database requirement
- No dashboard service
- No remote repository crawling
- No external API writes
- No issue creation
- No autonomous remediation
- No production code modification

Primary command target:

```bash
ai-debt gate
```

Primary outputs:

```text
.ai-debt/reports/quality-gate.json
.ai-debt/reports/quality-gate.md
```

## Documentation files

Recommended docs:

```text
docs/QUALITY_GATE.md
docs/ci/github-actions.md
docs/ci/gitlab-ci.md
docs/ci/azure-pipelines.md
docs/ci/jenkins.md
docs/ci/portable-shell.md
docs/CLI.md
docs/V2_ROADMAP.md
CHANGELOG.md
ROADMAP.md
KNOWN_LIMITATIONS.md
```

## `docs/QUALITY_GATE.md` structure

```markdown
# Local CI Quality Gate

## Purpose
## Safety boundary
## Quick start
## Command reference
## Result model
## Exit codes
## Configuration
## Rules
## Reports
## CI examples
## Troubleshooting
## Known limitations
```

## Changelog entry

```markdown
## v2.0.0

### Added
- `ai-debt gate` local CI quality gate command.
- Quality gate JSON and Markdown reports.
- Configurable gate thresholds and rule behavior.
- CI examples for GitHub Actions, GitLab CI, Azure Pipelines, Jenkins, and portable shell.

### Safety
- The quality gate is local-only and read-only with respect to canonical Pharabius artifacts.
- No external APIs are called.
- No issues, PR comments, or tracker items are created.
- No production code is modified.
```

## Release checklist

- Version is `2.0.0`.
- Build artifact is `pharabius-2.0.0`.
- CLI help includes `gate`.
- `docs/QUALITY_GATE.md` exists.
- CI examples exist.
- All quality gate tests pass.
- All 7 local gates pass.
- Release consistency script passes.
- Packaging validation passes.
- v1 safety boundaries are not weakened.
- v2 roadmap docs amended to CI-gate-first.

## Acceptance criteria

- Docs make the quality gate easy to adopt.
- Docs distinguish result from exit code.
- Docs distinguish quality gate from external integration.
- Docs include no-credentials CI examples.
- Release notes position v2.0 as workflow insertion without infrastructure.
