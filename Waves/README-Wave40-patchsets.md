# Wave 40 — v1.5.1 Scoring Calibration & Evidence Pack — Patch Set Index

This folder contains standalone Markdown patch-set files for Wave 40.

## Operating model

```text
Wave = planning and acceptance container
Slice = atomic implementation unit
Gate = objective safety checkpoint
```

Each slice is designed to be reviewed, implemented, tested, and reverted independently.

## Patch sets

| Slice | Title | Risk | File |
|---|---|---|---|
| W40-S01 | Scoring validation evidence pack format | Low | `W40-S01-scoring-validation-evidence-pack-format.md` |
| W40-S02 | Improve `scoring-delta.md` readability | Low-medium | `W40-S02-improve-scoring-delta-readability.md` |
| W40-S03 | Add threshold calibration fixtures | Medium | `W40-S03-threshold-calibration-fixtures.md` |
| W40-S04 | Add field validation summary command/script | Medium | `W40-S04-field-validation-summary-script.md` |
| W40-S05 | Tune thresholds only if evidence supports it | High, optional | `W40-S05-threshold-tuning-conditional.md` |
| W40-S06 | Documentation and changelog | Low | `W40-S06-documentation-and-changelog.md` |

## Recommended execution order

```text
W40-S01 → W40-S02 → W40-S03 → W40-S04 → W40-S05 optional/no-op → W40-S06
```

## Wave-level stop conditions

Stop the wave and reassess if any slice causes:

- default scoring behavior to change unexpectedly;
- preview mode to mutate canonical artifacts;
- finding IDs or evidence IDs to become unstable;
- canonical score changes outside explicitly approved enhanced-scoring behavior;
- governance or review sidecar state to influence scoring;
- any movement toward autonomous remediation.

## Wave-level release gate

Before v1.5.1 release:

```bash
ruff format --check .
ruff check .
mypy src
lint-imports
pytest
python -m build
python scripts/validate_repo.py .
```
