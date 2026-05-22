# W40-S01 — Scoring Validation Evidence Pack Format

**Wave:** Wave 40 — v1.5.1 Scoring Calibration & Evidence Pack  
**Slice:** W40-S01  
**Title:** Scoring validation evidence pack format  
**Risk:** Low  
**Impact class:** Sidecar/docs only  
**Release target:** v1.5.1  
**Implementation unit:** Atomic slice; may be merged independently

---

## 1. Scope

Define the canonical format for a scoring validation evidence pack that summarizes how enhanced scoring behaves across validation repositories.

This slice defines the artifact contract only. It does **not** change scoring behavior, thresholds, canonical finding scores, priority bands, exports, or CLI semantics.

### In scope

- Define the evidence pack artifact shape.
- Define required fields for scoring calibration evidence.
- Define sidecar output path conventions.
- Add examples that future validation scripts can emit.
- Document how Product Engineering Teams and maintainers should read the evidence pack.

### Out of scope

- No changes to `risk_score` calculation.
- No changes to `architecture_centrality` thresholds.
- No changes to `change_frequency` thresholds.
- No changes to canonical `.ai-debt/debt-register.json`.
- No new CLI command.
- No field validation runner implementation.
- No release version bump unless this slice is merged as part of the final v1.5.1 release branch.

---

## 2. Goals

1. Establish a stable sidecar format for scoring calibration evidence.
2. Make validation evidence reviewable without inspecting raw debt registers manually.
3. Support later slices that generate, compare, and summarize scoring deltas.
4. Keep the artifact non-canonical and safe by default.
5. Preserve the v1.5.0 enhanced scoring contract: opt-in, deterministic, provenance-backed.

---

## 3. Proposed artifact paths

Future validation tooling should emit these files:

```text
.ai-debt/reports/scoring-evidence-pack.json
.ai-debt/reports/scoring-evidence-pack.md
```

The JSON file is intended for machines and regression tests. The Markdown file is intended for reviewers.

This slice only documents and examples those artifacts. It does not generate them.

---

## 4. Patch set

### 4.1 Add `docs/SCORING_EVIDENCE_PACK.md`

Create a new document with the following structure:

```markdown
# Scoring Evidence Pack

## Purpose
The scoring evidence pack is a non-canonical validation sidecar used to evaluate enhanced risk scoring behavior across repositories.

## Artifact status
- Non-canonical
- Does not affect debt-register scoring
- Does not affect work package ordering
- Does not affect review sidecar decisions
- Safe to regenerate

## Output files
- `.ai-debt/reports/scoring-evidence-pack.json`
- `.ai-debt/reports/scoring-evidence-pack.md`

## Required JSON fields
...

## Interpretation guide
...

## Calibration rules
...
```

### 4.2 Add `docs/examples/scoring-evidence-pack.example.json`

Create a representative example:

```json
{
  "schema_version": "1.0",
  "tool_version": "1.5.1-dev",
  "generated_at": "2026-05-22T00:00:00Z",
  "analysis_mode": "enhanced_scoring_validation",
  "repositories": [
    {
      "name": "example-service",
      "path": "../example-service",
      "commit": "abc1234",
      "default_findings": 4,
      "enhanced_findings": 4,
      "finding_ids_stable": true,
      "evidence_ids_stable": true,
      "canonical_mutation_in_preview": false,
      "score_changes": [
        {
          "finding_id": "TD-ARCH-001",
          "title": "Central module has high dependency fan-in",
          "category": "TD-ARCH",
          "before_score": 18,
          "after_score": 22,
          "before_priority": "Medium",
          "after_priority": "High",
          "changed_factors": [
            {
              "factor": "architecture_centrality",
              "before_level": "Low",
              "after_level": "High",
              "before_value": 1,
              "after_value": 5,
              "source": "architecture-graph.json",
              "reason": "fan_in=8; top_10_percent_hub=true; cycle_participation=false"
            }
          ]
        }
      ],
      "warnings": [],
      "runtime_seconds": {
        "default": 1.42,
        "enhanced": 2.10,
        "preview": 2.05
      }
    }
  ],
  "summary": {
    "repositories_checked": 1,
    "repositories_passed": 1,
    "score_changes_total": 1,
    "priority_changes_total": 1,
    "preview_mutation_failures": 0,
    "id_stability_failures": 0
  }
}
```

### 4.3 Add `docs/examples/scoring-evidence-pack.example.md`

Create a human-readable equivalent:

```markdown
# Scoring Evidence Pack

## Summary

| Metric | Value |
|---|---:|
| Repositories checked | 1 |
| Repositories passed | 1 |
| Score changes | 1 |
| Priority changes | 1 |
| Preview mutation failures | 0 |
| ID stability failures | 0 |

## Repository: example-service

| Check | Result |
|---|---|
| Finding IDs stable | PASS |
| Evidence IDs stable | PASS |
| Preview mode mutation | PASS — no mutation |
| Default findings | 4 |
| Enhanced findings | 4 |

## Score Changes

| Finding | Category | Score | Priority | Changed Factors |
|---|---|---:|---|---|
| TD-ARCH-001 | TD-ARCH | 18 → 22 | Medium → High | architecture_centrality |
```

### 4.4 Optional: link from `docs/SCORING.md`

Add a short section:

```markdown
## Scoring validation evidence pack

For release calibration and field validation, Pharabius may produce a non-canonical scoring evidence pack. This sidecar summarizes score changes, priority changes, provenance, runtime, warnings, and stability checks across validation repositories.

See `docs/SCORING_EVIDENCE_PACK.md`.
```

---

## 5. Tests

This slice is documentation and example-artifact only.

Recommended lightweight tests:

1. Validate the example JSON is syntactically valid.
2. Validate required top-level fields exist.
3. Ensure docs links are not broken if the project has a docs-link checker.

### Suggested test file

```text
tests/test_scoring_evidence_pack_examples.py
```

### Suggested test cases

```python
def test_scoring_evidence_pack_example_json_is_valid():
    ...


def test_scoring_evidence_pack_example_has_required_fields():
    ...
```

---

## 6. Verification commands

```bash
python -m json.tool docs/examples/scoring-evidence-pack.example.json >/dev/null
ruff format --check .
ruff check .
mypy src
pytest tests/test_scoring_evidence_pack_examples.py
python -m build
python scripts/validate_repo.py .
```

For full gate verification:

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

- Maintainers have a documented evidence-pack format.
- No canonical artifact changes occur.
- No scoring behavior changes occur.
- No CLI behavior changes occur.
- Future validation tooling has a stable target artifact shape.

---

## 8. Acceptance criteria

- [ ] `docs/SCORING_EVIDENCE_PACK.md` exists.
- [ ] Example JSON exists and is valid JSON.
- [ ] Example Markdown exists and is readable.
- [ ] Example fields include repository identity, commit, score changes, priority changes, provenance, warnings, runtime, preview mutation status, and ID stability.
- [ ] No production code changes are required.
- [ ] No canonical `.ai-debt/debt-register.json` behavior changes.
- [ ] All local quality gates pass.

---

## 9. Rollback plan

Revert the added docs/example files. No runtime behavior or canonical artifact behavior is affected.
