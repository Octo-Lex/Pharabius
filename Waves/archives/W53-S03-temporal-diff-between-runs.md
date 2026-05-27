# W53-S03 — Temporal Diff Between Runs

Risk: Medium  
Slice type: Analysis feature

## Scope

Add `ai-debt diff` command that compares two analysis runs and shows what changed: new findings, resolved findings, changed severity, changed confidence.

## Goals

- `ai-debt diff` compares two run metadata files or two debt-register snapshots.
- Shows new findings, resolved findings, severity changes, confidence changes.
- Supports JSON and human-readable Markdown output.
- Works purely on local artifacts — no network access.
- Does not modify any files.

## Patch Set

```text
src/pharabius/schemas/run_diff.py         # new
src/pharabius/core/differ.py              # new
src/pharabius/cli.py                       # add diff command
tests/test_run_diff_schema.py             # new
tests/test_run_diff_engine.py             # new
tests/test_cli_diff.py                    # new
```

## CLI Interface

```bash
ai-debt diff --before .ai-debt/runs/RUN-001.json --after .ai-debt/runs/RUN-002.json
ai-debt diff --before .ai-debt/runs/RUN-001.json --after .ai-debt/runs/RUN-002.json --json
ai-debt diff --latest                      # compare last two runs automatically
```

## Diff Schema

```python
class RunDiff(BaseModel):
    schema_version: str = "1.0"
    before_run_id: str
    after_run_id: str
    new_findings: list[str]          # finding IDs
    resolved_findings: list[str]     # finding IDs
    severity_changes: list[dict]     # {id, from, to}
    confidence_changes: list[dict]   # {id, from, to}
    summary: DiffSummary
```

## Output Examples

Human-readable:
```
Run Diff: RUN-001 → RUN-002
New findings: 3 (+)
  TD-DEP-005: Missing lockfile (Medium)
  TD-ARCH-002: Circular dependency (High)
  TD-TEST-003: Test coverage gap (Low)
Resolved findings: 1 (-)
  TD-DEP-001: Dependency without lockfile (was Medium)
Severity changes: 1 (~)
  TD-ARCH-001: Medium → High
Net change: +2 findings (12 → 14)
```

## Tests

- Diff detects new findings.
- Diff detects resolved findings.
- Diff detects severity changes.
- Diff detects confidence changes.
- Summary counts are accurate.
- No findings on both sides produces empty diff.
- `--latest` finds the two most recent runs.
- Missing run files produce clear error.
- Diff does not modify any files.

## Acceptance Criteria

- `ai-debt diff` command exists.
- Correctly identifies new, resolved, and changed findings.
- JSON and human-readable output work.
- Read-only.
- 7 gates pass.
