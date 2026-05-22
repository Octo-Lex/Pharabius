# W40-S02 — Improve `scoring-delta.md` Readability

**Wave:** Wave 40 — v1.5.1 Scoring Calibration & Evidence Pack  
**Slice:** W40-S02  
**Title:** Improve `scoring-delta.md` readability  
**Risk:** Low-medium  
**Impact class:** Report-only  
**Release target:** v1.5.1  
**Implementation unit:** Atomic slice; may be merged independently after W40-S01

---

## 1. Scope

Improve the human-readable scoring delta report generated when enhanced scoring is active.

This slice changes only report presentation. It must not change risk factor computation, risk scores, priority bands, finding IDs, evidence IDs, exports, or canonical JSON content except for existing timestamp/run metadata that already changes per run.

### In scope

- Improve `.ai-debt/reports/scoring-delta.md` structure.
- Group changes by priority movement and factor.
- Add clearer before/after sections.
- Add provenance text for changed factors.
- Add warning summary for fallback behavior.
- Add reviewer guidance.
- Add tests proving report changes do not mutate scoring semantics.

### Out of scope

- No threshold changes.
- No new scoring factors.
- No canonical debt register schema change.
- No SARIF/CSV/JSONL export changes.
- No changes to `--scoring-preview` semantics beyond readable output if the same renderer is reused.

---

## 2. Goals

1. Make scoring changes understandable during review.
2. Help maintainers identify why a score changed.
3. Separate score changes from priority changes.
4. Surface fallback warnings clearly.
5. Preserve deterministic scoring behavior.

---

## 3. Desired report structure

The updated report should use this shape:

```markdown
# Scoring Delta Report

## Configuration

| Setting | Value |
|---|---|
| Enhanced scoring | enabled |
| Architecture centrality | enabled |
| Change frequency | enabled |
| Git cap | 1000 commits |
| Path cap | 5000 paths |
| Git timeout | 10s |
| Graph timeout | 5s |

## Summary

| Metric | Value |
|---|---:|
| Total findings | 6 |
| Scores changed | 3 |
| Scores unchanged | 3 |
| Priority changes | 1 |
| Warnings | 0 |

## Priority Movement

| Movement | Count |
|---|---:|
| Low → Medium | 0 |
| Medium → High | 1 |
| High → Critical | 0 |
| No priority change | 5 |

## Changed Findings

| Finding | Category | Score | Priority | Changed Factors |
|---|---|---:|---|---|
| TD-ARCH-001 | TD-ARCH | 18 → 22 | Medium → High | architecture_centrality |

## Factor Details

### TD-ARCH-001 — Central module has high dependency fan-in

| Factor | Before | After | Source | Reason |
|---|---|---|---|---|
| architecture_centrality | Low (1) | High (5) | architecture-graph.json | fan_in=8; top_10_percent_hub=true |

## Warnings and Fallbacks

No warnings.

## Reviewer Notes

- Enhanced scoring is opt-in.
- Finding IDs and evidence IDs are expected to remain stable.
- Only risk factors, risk score, and priority may change.
```

---

## 4. Patch set

### 4.1 Update `src/pharabius/core/scoring.py`

Add or refactor a dedicated Markdown renderer, for example:

```python
def render_scoring_delta_markdown(delta: ScoringDeltaReport) -> str:
    """Render a human-readable scoring delta report.

    This function must be presentation-only. It must not mutate findings,
    recompute risk factors, or update canonical artifacts.
    """
```

If a typed model does not yet exist, introduce a narrow internal dataclass:

```python
@dataclass(frozen=True)
class ScoringDeltaRow:
    finding_id: str
    title: str
    category: str
    before_score: int
    after_score: int
    before_priority: str
    after_priority: str
    changed_factors: list[str]
```

Do **not** move factor calculation into the renderer.

### 4.2 Update scoring delta generation call site

Likely files:

```text
src/pharabius/core/analyzer.py
src/pharabius/core/scoring.py
```

Ensure the delta renderer receives already-computed before/after values.

### 4.3 Add tests

Add tests to `tests/test_scoring.py` or a new file:

```text
tests/test_scoring_delta_report.py
```

Required tests:

```python
def test_scoring_delta_report_groups_priority_movement():
    ...


def test_scoring_delta_report_includes_factor_provenance():
    ...


def test_scoring_delta_report_includes_fallback_warnings():
    ...


def test_scoring_delta_report_rendering_does_not_recompute_scores():
    ...
```

### 4.4 Update docs if necessary

If `docs/SCORING.md` already describes the delta report, update only the report layout description.

---

## 5. Tests

### Unit tests

- Renderer emits `# Scoring Delta Report`.
- Renderer includes configuration table.
- Renderer includes summary table.
- Renderer includes priority movement table.
- Renderer includes changed findings table.
- Renderer includes factor provenance: level, value, source, reason.
- Renderer includes warning/fallback section.
- Renderer handles no changes cleanly.
- Renderer handles no warnings cleanly.

### Regression tests

- Enhanced scoring output values remain unchanged before and after this patch.
- Default scoring remains unchanged.
- Preview mode remains non-mutating.

---

## 6. Verification commands

```bash
ruff format --check .
ruff check .
mypy src
pytest tests/test_scoring.py tests/test_scoring_delta_report.py
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

Manual smoke test:

```bash
ai-debt analyze --enhanced-scoring
sed -n '1,220p' .ai-debt/reports/scoring-delta.md
```

Preview smoke test:

```bash
sha256sum .ai-debt/debt-register.json > /tmp/debt-register.before.sha
ai-debt analyze --scoring-preview
sha256sum .ai-debt/debt-register.json > /tmp/debt-register.after.sha
diff /tmp/debt-register.before.sha /tmp/debt-register.after.sha
```

---

## 7. Expected behavior

After this slice:

- `scoring-delta.md` is easier to review.
- Score and priority movements are clearly summarized.
- Changed factors include provenance and reasons.
- Fallback warnings are visible.
- Canonical scoring behavior is unchanged.

---

## 8. Acceptance criteria

- [ ] Report includes configuration, summary, priority movement, changed findings, factor details, warnings, and reviewer notes.
- [ ] Report renderer is presentation-only.
- [ ] Unit tests cover changed report sections.
- [ ] No changes to risk score calculation.
- [ ] No changes to priority band logic.
- [ ] No changes to finding IDs or evidence IDs.
- [ ] Preview mode remains non-mutating.
- [ ] All 7 gates pass.

---

## 9. Rollback plan

Revert renderer/report changes and related tests. Enhanced scoring computation remains unaffected.
