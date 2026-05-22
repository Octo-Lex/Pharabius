# W40-S05 — Tune Thresholds Only If Evidence Supports It

**Wave:** Wave 40 — v1.5.1 Scoring Calibration & Evidence Pack  
**Slice:** W40-S05  
**Title:** Tune thresholds only if evidence supports it  
**Risk:** High  
**Impact class:** Canonical scoring behavior, optional  
**Release target:** v1.5.1 only if justified; otherwise defer/no-op  
**Implementation unit:** Isolated slice; must not be bundled with docs, tooling, or unrelated changes

---

## 1. Scope

This is a conditional slice. It should only be implemented if W40-S03 fixtures and W40-S04 field validation evidence show that the current v1.5.0 thresholds produce materially poor prioritization.

If the evidence does not justify tuning, this slice should close with a no-op calibration decision document rather than code changes.

### In scope if evidence supports tuning

- Adjust architecture centrality thresholds.
- Adjust change frequency thresholds.
- Update calibration fixtures and expectations.
- Update scoring docs and known limitations.
- Add explicit release notes explaining score churn risk.
- Re-run field validation on the approved validation repository set.

### Out of scope

- No new scoring factors.
- No default enhanced scoring.
- No AI/provider involvement.
- No governance scoring flags.
- No review sidecar influence.
- No ticket export.
- No remediation/code modification.
- No changes to priority band ranges unless approved as a separate wave.

---

## 2. Goals

1. Improve enhanced scoring precision only if validation evidence proves a need.
2. Avoid subjective threshold changes.
3. Keep score churn visible and bounded.
4. Preserve default v1.4/v1.5 behavior when enhanced scoring is disabled.
5. Maintain factor scale compatibility: Low=1, Medium=3, High=5, Critical=8 reserved.

---

## 3. Entry criteria

This slice may start only if all conditions are met:

- [ ] W40-S03 calibration fixtures are merged.
- [ ] W40-S04 validation script is merged.
- [ ] Field validation evidence pack exists for at least the approved validation repos.
- [ ] Evidence pack identifies recurring misclassification or noisy priority movement.
- [ ] Proposed threshold change is written before implementation.
- [ ] Expected score/priority churn is documented.

Recommended minimum validation set:

```text
Pharabius
validation-java
validation-empty
Ghostwire
Symbiot
```

Recommended expanded set before tuning:

```text
10+ repositories if available, including at least:
- small Python repo
- Java/Maven repo
- empty/minimal repo
- Node.js repo
- multi-language repo
- larger repository with many evidence items
```

---

## 4. Decision paths

### Path A — No tuning justified

Create or update:

```text
docs/release-notes/v1.5.1-scoring-calibration-decision.md
```

Content:

```markdown
# v1.5.1 Scoring Calibration Decision

## Decision
No threshold changes in v1.5.1.

## Evidence reviewed
- Evidence pack path
- Repository count
- Score changes reviewed
- Priority changes reviewed

## Rationale
Current thresholds remain conservative and acceptable.

## Follow-up
Continue collecting field evidence before any v2.0 default scoring decision.
```

No production code changes.

### Path B — Tuning justified

Proceed with the patch set below.

---

## 5. Patch set if tuning is justified

### 5.1 Update threshold constants

Likely file:

```text
src/pharabius/core/scoring.py
```

Current conceptual thresholds:

```text
architecture_centrality:
  Low: fan-in <= 2 and not in cycle
  Medium: fan-in 3-5 or moderate edges
  High: fan-in > 5 or cycle > 2 nodes or top-10% hub

change_frequency:
  Low: 0-2 commits
  Medium: 3-10 commits
  High: >10 commits
```

Any change must be explicit and named:

```python
ARCHITECTURE_CENTRALITY_THRESHOLDS = ArchitectureCentralityThresholds(
    low_fan_in_max=2,
    medium_fan_in_max=5,
    high_cycle_size_min=3,
    hub_percentile=0.90,
)

CHANGE_FREQUENCY_THRESHOLDS = ChangeFrequencyThresholds(
    low_commit_max=2,
    medium_commit_max=10,
)
```

If constants do not exist, introduce them before changing values so future reviews can see threshold changes clearly.

### 5.2 Update calibration fixtures

Update only the affected fixtures:

```text
tests/fixtures/scoring_calibration/**
```

Add new cases for any newly discovered boundary condition.

### 5.3 Update tests

Likely files:

```text
tests/test_scoring.py
tests/test_scoring_calibration_fixtures.py
```

Required tests:

```python
def test_architecture_centrality_thresholds_match_calibration_decision():
    ...


def test_change_frequency_thresholds_match_calibration_decision():
    ...
```

### 5.4 Update docs

Likely files:

```text
docs/SCORING.md
docs/KNOWN_LIMITATIONS.md
CHANGELOG.md
```

Docs must include:

- Old thresholds.
- New thresholds.
- Why they changed.
- Evidence pack path or summary.
- Expected score churn.
- Reminder that enhanced scoring remains opt-in.

---

## 6. Tests

### Required tests if tuning occurs

- Default scoring unchanged when enhanced scoring disabled.
- Architecture threshold boundary cases pass.
- Change frequency threshold boundary cases pass.
- Enhanced scoring expected cases match fixture expectations.
- Preview mode remains non-mutating.
- Finding IDs remain stable.
- Evidence IDs remain stable.
- Exports reflect canonical scores only when enhanced scoring is enabled.

---

## 7. Verification commands

```bash
ruff format --check .
ruff check .
mypy src
pytest tests/test_scoring.py tests/test_scoring_calibration_fixtures.py
python scripts/validate_v151_scoring_calibration.py \
  --repo Pharabius=. \
  --output .ai-debt/reports/scoring-evidence-pack.json \
  --markdown-output .ai-debt/reports/scoring-evidence-pack.md
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

Field validation after tuning:

```bash
python scripts/validate_v151_scoring_calibration.py \
  --repo Pharabius=../Pharabius \
  --repo validation-java=../validation-java \
  --repo validation-empty=../validation-empty \
  --repo Ghostwire=../Ghostwire \
  --repo Symbiot=../Symbiot \
  --output .ai-debt/reports/scoring-evidence-pack.json \
  --markdown-output .ai-debt/reports/scoring-evidence-pack.md
```

---

## 8. Expected behavior

### If no tuning occurs

- v1.5.1 ships calibration evidence and improved reporting only.
- Thresholds remain identical to v1.5.0.
- No score churn beyond existing v1.5.0 enhanced scoring behavior.

### If tuning occurs

- Enhanced scoring may produce different scores than v1.5.0 when explicitly enabled.
- Default scoring remains unchanged.
- Preview mode remains non-mutating.
- Score deltas and priority movement are documented.
- Threshold change is supported by evidence pack output.

---

## 9. Acceptance criteria

### Always required

- [ ] Evidence pack reviewed before any threshold change.
- [ ] Default behavior unchanged when enhanced scoring disabled.
- [ ] Enhanced scoring remains opt-in.
- [ ] Factor scale remains Low=1, Medium=3, High=5, Critical=8 reserved.
- [ ] No governance or review sidecar influence.
- [ ] No autonomous remediation behavior.
- [ ] All 7 gates pass.

### Required if tuning occurs

- [ ] Threshold changes are isolated to this slice.
- [ ] Old/new thresholds are documented.
- [ ] Calibration fixtures updated intentionally.
- [ ] Field validation evidence pack regenerated.
- [ ] Score churn is summarized.
- [ ] Priority churn is summarized.
- [ ] No finding ID or evidence ID instability.
- [ ] Preview mode remains non-mutating.

### Required if no tuning occurs

- [ ] No-op calibration decision document exists.
- [ ] Evidence reviewed is summarized.
- [ ] Follow-up recommendation is documented.

---

## 10. Rollback plan

If threshold tuning causes unexpected score churn:

1. Revert changes to threshold constants.
2. Revert changed calibration expectations.
3. Keep evidence pack tooling if already merged.
4. Document rollback in `CHANGELOG.md` if the slice had been released.

Because this slice is isolated, rollback should not affect W40-S01 through W40-S04.
