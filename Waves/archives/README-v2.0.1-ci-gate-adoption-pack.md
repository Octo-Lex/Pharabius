# v2.0.1 — CI Gate Adoption & SARIF Polish

Goal: Harden v2.0.0 for real CI adoption by improving quality-gate usability, SARIF validation, GitHub Action documentation, failure-mode guidance, and report readability without adding new product capability.

Release posture: patch release, not feature release.

Core boundary:
- No external SARIF upload by default
- No PR comments
- No GitHub Checks API integration
- No tracker writes
- No issue creation
- No dashboard
- No database
- No server
- No autonomous remediation
- No source code modification


## Pack contents

| File | Purpose |
|---|---|
| `S01-ci-example-validation-and-fixtures.md` | Validate CI examples and add fixtures |
| `S02-github-action-usage-polish.md` | Polish GitHub Action metadata, docs, and safe defaults |
| `S03-quality-gate-report-readability.md` | Improve gate report readability without changing decisions |
| `S04-sarif-fixture-validation-and-docs.md` | Validate SARIF fixtures and clarify local-only SARIF behavior |
| `S05-failure-mode-and-troubleshooting-guide.md` | Add failure-mode documentation and diagnostics |
| `S06-docs-changelog-release.md` | Release finalization |

## Recommended branch

```text
roadmap/v2.0.1-ci-gate-adoption-sarif-polish
```

## Recommended release headline

```text
Pharabius v2.0.1 improves CI gate adoption, SARIF validation, GitHub Action documentation, troubleshooting, and report readability while preserving local-only, no-external-write behavior.
```

## Wave-level acceptance criteria

- v2.0.1 remains a patch release.
- No new product capability is added.
- CI examples are validated and safe by default.
- GitHub Action wrapper remains local-only by default.
- Quality gate reports are easier to read.
- SARIF remains local artifact generation only unless users explicitly configure upload in their own workflow.
- Troubleshooting docs help users recover without bypassing safety boundaries.
- All 7 gates pass.
