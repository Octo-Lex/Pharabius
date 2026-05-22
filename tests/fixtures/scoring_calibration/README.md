# Scoring Calibration Fixtures

## Purpose

These fixtures lock the current v1.5.0 scoring threshold behavior as executable tests.
Any future threshold change must update the corresponding fixture expectations.

## Case naming convention

```text
{factor}_{boundary_description}.json
```

Examples: `high_fan_in_boundary.json`, `three_commits_boundary.json`

## Current thresholds (v1.5.0)

### Architecture centrality

| Level | Condition | Value |
|---|---|---|
| Low | fan_in ≤ 2 AND not in cycle | 1 |
| Medium | fan_in 3–5 AND not in cycle | 3 |
| High | fan_in > 5 OR in cycle with 2+ nodes OR top-10% hub | 5 |

### Change frequency

| Level | Condition | Value |
|---|---|---|
| Low | 0–2 commits, not git repo, or shallow clone | 1 |
| Medium | 3–10 commits | 3 |
| High | > 10 commits | 5 |

## How to add a new case

1. Create a JSON file in the appropriate subdirectory.
2. Include `case_id`, `description`, `finding_locations`, factor-specific data, and `expected`.
3. Add a corresponding test case in `test_scoring_calibration_fixtures.py`.

## Rule

Update expectations **only** in explicit threshold-tuning slices (W40-S05 or later).
Never update expectations as a side effect of unrelated changes.
