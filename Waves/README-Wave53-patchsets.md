# Wave 53 — v2.0 Local CI Quality Gate

Goal: Close the #1 competitive gap — get Pharabius into CI/CD pipelines with quality gate enforcement, PR feedback, and temporal diff capability. This is the first v2 feature wave.

Release target: `v2.0.0`  
Branch target: `roadmap/v2.0-local-ci-quality-gate`  
Boundary: CI integration, quality gates, temporal diff, and GitHub Action only. No external API writes, no server, no dashboard, no code modification.

# Wave 53 Patch-Set Index

| Slice | Title | Risk | File |
|---|---|---|---|
| W53-S01 | Quality gate schema and threshold model | Medium | `W53-S01-quality-gate-schema-and-threshold-model.md` |
| W53-S02 | `ai-debt gate` command with pass/fail exit codes | Medium | `W53-S02-ai-debt-gate-command.md` |
| W53-S03 | Temporal diff between runs | Medium | `W53-S03-temporal-diff-between-runs.md` |
| W53-S04 | SARIF enhancement for GitHub Code Scanning | Low-medium | `W53-S04-sarif-enhancement-for-github-code-scanning.md` |
| W53-S05 | GitHub Action for CI integration | Low-medium | `W53-S05-github-action-for-ci-integration.md` |
| W53-S06 | Docs, changelog, release | Low | `W53-S06-docs-changelog-release.md` |

## Wave-Level Acceptance Criteria

- Quality gate command exists with configurable thresholds.
- Quality gate produces clear pass/fail exit codes for CI consumption.
- Temporal diff shows what changed between two runs.
- SARIF output is valid for GitHub Code Scanning upload.
- GitHub Action allows `ai-debt` to run in CI with zero configuration.
- All v1 commands, artifacts, schemas, and safety boundaries remain intact.
- No external API writes, no server, no network dependency.
- All 7 local gates pass.
