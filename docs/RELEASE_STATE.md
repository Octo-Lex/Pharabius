# Release State — v3.0.0 Public Baseline

> **Date:** 2026-06-04

## Public Baselines

| Version | Tag | Commit | Date |
|---|---|---|---|
| v2.5.0 (previous) | `v2.5.0` | `e709872` | Published to GitHub |
| v3.0.0 (current) | `v3.0.0` | To be tagged at merge commit | This release |

## Internal Waves (Local Only)

16 internal wave tags exist locally but are NOT pushed to GitHub:

```
v3.0.0, v3.1.0, v3.2.0, v3.3.0, v3.4.0, v3.5.0, v3.6.0,
v3.7.0, v3.8.0, v3.9.0, v3.10.0, v3.11.0, v3.12.0,
v3.13.0, v3.14.0, v3.15.0
```

These are internal development markers. The v3.16.0–v3.26.0 governance arc milestones are embedded in commit history but were not tagged separately.

## Tag Safety

- `git push --tags` and `git push --follow-tags` are forbidden during this release
- Only `git push origin v3.0.0` is used
- Remote v3.0.0 absence is confirmed before tagging

## Validation Snapshot

| Check | Result |
|---|---|
| CLI tests | 2,970 passed, 7 skipped |
| Platform backend tests | 276 passed, 5 skipped |
| Frontend tests | 28 passed, 5 TS mock errors (pre-existing) |
| Frontend build | Succeeds (5 pre-existing TS errors in test mocks) |
| `ruff format` | All governance arc files formatted |
| `ruff check` | Warnings only (pre-existing, cosmetic) |
| `pyproject.toml` version | `3.0.0` |
| master is ancestor of branch | YES |

## Branch Structure

```
master (e709872 = GitHub v2.5.0)
  └── roadmap/v3.0.0-run-comparison-traceability-delta (24 commits)
        └── sync/public-v3-catchup (24 commits + public prep)
              └── → GitHub PR → master merge → v3.0.0 tag
```

## Post-Merge

After v3.0.0 is tagged and pushed:
- Record merge commit hash here
- Record CI result
- Publish GitHub release
- Future public releases continue from v3.0.0

## PR Merge Checkpoint

_(To be filled after merge)_

```
PR branch head: <commit>
GitHub CI result: <pass/fail/link>
Merge commit: <commit>
v3.0.0 tag commit: <commit>
```
