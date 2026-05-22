# W40-S03 — Add Threshold Calibration Fixtures

**Wave:** Wave 40 — v1.5.1 Scoring Calibration & Evidence Pack  
**Slice:** W40-S03  
**Title:** Add threshold calibration fixtures  
**Risk:** Medium  
**Impact class:** Tests/validation only  
**Release target:** v1.5.1  
**Implementation unit:** Atomic slice; should land before any threshold tuning

---

## 1. Scope

Add synthetic and repository-derived calibration fixtures for enhanced scoring thresholds. This slice creates the evidence base needed to decide whether threshold tuning is justified.

This slice must not change production scoring behavior.

### In scope

- Add fixture files for architecture centrality threshold cases.
- Add fixture files for change frequency threshold cases.
- Add expected scoring outcomes for boundary cases.
- Add tests that lock current v1.5.0 behavior.
- Add calibration case documentation.

### Out of scope

- No threshold changes.
- No canonical artifact mutation changes.
- No CLI changes.
- No report renderer changes except references to fixtures if needed.
- No field validation runner implementation.

---

## 2. Goals

1. Capture current threshold behavior as executable tests.
2. Make future threshold changes evidence-driven.
3. Cover boundary cases around Low/Medium/High transitions.
4. Prevent accidental scoring drift.
5. Provide regression fixtures before W40-S05.

---

## 3. Calibration fixture design

Add fixtures under:

```text
tests/fixtures/scoring_calibration/
  architecture_centrality/
    low_peripheral_node.json
    medium_fan_in_boundary.json
    high_fan_in_boundary.json
    high_cycle_participation.json
    missing_node.json
    empty_graph.json
  change_frequency/
    low_zero_commits.json
    low_two_commits_boundary.json
    medium_three_commits_boundary.json
    medium_ten_commits_boundary.json
    high_eleven_commits_boundary.json
    non_git_repo.json
    shallow_clone.json
  expected/
    calibration_expectations.json
```

### Architecture centrality fixture shape

```json
{
  "case_id": "arch-high-fan-in-boundary",
  "description": "Node with fan-in above high threshold should score High.",
  "finding_locations": [
    {"file": "src/core/service.py"}
  ],
  "architecture_graph": {
    "schema_version": "1.0",
    "nodes": [
      {"id": "src/core/service.py", "path": "src/core/service.py", "type": "python"}
    ],
    "edges": [
      {"source": "src/a.py", "target": "src/core/service.py", "edge_type": "import"}
    ],
    "metrics": {
      "node_count": 7,
      "edge_count": 6,
      "cycle_count": 0
    }
  },
  "expected": {
    "architecture_centrality": {
      "level": "High",
      "value": 5
    }
  }
}
```

### Change frequency fixture shape

```json
{
  "case_id": "freq-medium-three-commits-boundary",
  "description": "Three commits should map to Medium.",
  "finding_locations": [
    {"file": "src/core/service.py"}
  ],
  "git_history": {
    "is_git_repo": true,
    "is_shallow": false,
    "commit_counts_by_path": {
      "src/core/service.py": 3
    }
  },
  "expected": {
    "change_frequency": {
      "level": "Medium",
      "value": 3
    }
  }
}
```

---

## 4. Patch set

### 4.1 Add fixture directory

Create:

```text
tests/fixtures/scoring_calibration/
```

Include JSON fixtures for boundary and fallback cases.

### 4.2 Add fixture loader

Add helper functions in the test suite, not production code:

```text
tests/helpers/scoring_calibration.py
```

Suggested helpers:

```python
def load_calibration_case(path: Path) -> dict[str, Any]:
    ...


def iter_architecture_centrality_cases() -> Iterator[dict[str, Any]]:
    ...


def iter_change_frequency_cases() -> Iterator[dict[str, Any]]:
    ...
```

### 4.3 Add calibration tests

Create:

```text
tests/test_scoring_calibration_fixtures.py
```

Required tests:

```python
def test_architecture_centrality_calibration_cases():
    ...


def test_change_frequency_calibration_cases():
    ...


def test_calibration_fixtures_are_valid_json():
    ...


def test_calibration_cases_have_expected_fields():
    ...
```

### 4.4 Optional: add fixture README

Create:

```text
tests/fixtures/scoring_calibration/README.md
```

Include:

- Purpose
- Case naming convention
- Current thresholds
- How to add a new case
- Rule: update expectations only in explicit threshold-tuning slices

---

## 5. Tests

### Required fixture coverage

Architecture centrality:

| Case | Expected |
|---|---|
| Missing graph | Low (1) |
| Empty graph | Low (1) |
| Node not found | Low (1) |
| Fan-in ≤ 2 and no cycle | Low (1) |
| Fan-in 3–5 | Medium (3) |
| Fan-in > 5 | High (5) |
| Cycle with >2 nodes | High (5) |
| Top-10% hub | High (5) |

Change frequency:

| Case | Expected |
|---|---|
| Not git repo | Low (1) |
| Shallow clone | Low (1) |
| No locations | Low (1) |
| 0 commits | Low (1) |
| 2 commits | Low (1) |
| 3 commits | Medium (3) |
| 10 commits | Medium (3) |
| 11 commits | High (5) |

---

## 6. Verification commands

```bash
python -m json.tool tests/fixtures/scoring_calibration/expected/calibration_expectations.json >/dev/null
ruff format --check .
ruff check .
mypy src
pytest tests/test_scoring_calibration_fixtures.py
python -m build
python scripts/validate_repo.py .
```

Full quality gates:

```bash
ruff format --check .
ruff check .
mypy src
lint-imports
pytest
python -m build
python scripts/validate_repo.py .
```

---

## 7. Expected behavior

After this slice:

- Current v1.5.0 scoring thresholds are represented as fixtures.
- Boundary behavior is protected by tests.
- Future threshold changes require intentional fixture expectation updates.
- No runtime behavior changes occur.

---

## 8. Acceptance criteria

- [ ] Calibration fixture directory exists.
- [ ] Architecture centrality boundary cases are covered.
- [ ] Change frequency boundary cases are covered.
- [ ] Fallback cases are covered.
- [ ] Fixture loader is test-only.
- [ ] Tests pass with existing v1.5.0 thresholds.
- [ ] Production scoring code is not changed.
- [ ] All 7 gates pass.

---

## 9. Rollback plan

Revert fixture files and fixture tests. No runtime behavior is affected.
