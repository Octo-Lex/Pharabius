# W40-S06 — Documentation and Changelog Finalization

**Wave:** Wave 40 — v1.5.1 Scoring Calibration & Evidence Pack  
**Slice:** W40-S06  
**Title:** Documentation and changelog  
**Risk:** Low  
**Impact class:** Finalization  
**Release target:** v1.5.1  
**Implementation unit:** Final slice after W40-S01 through W40-S04, and after W40-S05 if executed

---

## 1. Scope

Finalize v1.5.1 documentation, changelog, known limitations, roadmap, and package version after the wave’s implementation slices are complete.

This slice should not introduce new functionality.

### In scope

- Bump project version to `1.5.1`.
- Update `CHANGELOG.md`.
- Update `ROADMAP.md`.
- Update `KNOWN_LIMITATIONS.md`.
- Update `docs/SCORING.md`.
- Link scoring evidence pack documentation.
- Document whether W40-S05 tuned thresholds or made a no-op decision.
- Add release validation summary.

### Out of scope

- No scoring algorithm changes.
- No threshold changes.
- No report renderer changes.
- No validation script behavior changes.
- No CLI behavior changes.
- No canonical artifact schema changes.

---

## 2. Goals

1. Make v1.5.1 release behavior clear to users.
2. Explain the evidence pack and calibration workflow.
3. Document any known limitations and fallback behavior.
4. Preserve accurate release history.
5. Prepare the package for tagging and release.

---

## 3. Patch set

### 3.1 Update `pyproject.toml`

```toml
version = "1.5.1"
```

### 3.2 Update `CHANGELOG.md`

Add:

```markdown
## v1.5.1 — Scoring Calibration & Evidence Pack

### Added
- Scoring evidence pack format and examples.
- Field validation summary tooling for enhanced scoring calibration.
- Calibration fixtures for architecture centrality and change frequency thresholds.

### Improved
- `scoring-delta.md` readability with clearer summary, priority movement, factor provenance, and warning sections.

### Validation
- Enhanced scoring validation can now produce machine-readable and human-readable evidence packs.
- Preview-mode non-mutation, finding ID stability, evidence ID stability, and reset/default behavior are validated by tooling.

### Thresholds
- If W40-S05 was not executed: No threshold changes in v1.5.1.
- If W40-S05 was executed: Document old thresholds, new thresholds, and evidence basis here.

### Compatibility
- Enhanced scoring remains opt-in.
- Default scoring remains unchanged when enhanced scoring is disabled.
```

### 3.3 Update `ROADMAP.md`

Add completion notes for v1.5.1:

```markdown
### v1.5.1 — Scoring Calibration & Evidence Pack

Status: Released / Planned depending on branch state.

Focus:
- Evidence pack format
- Scoring delta readability
- Calibration fixtures
- Field validation summary tooling
- Optional threshold tuning only if evidence supported it
```

Update next recommended work:

```markdown
### Next candidate: v1.6

Recommended direction:
- Ticket draft export only after scoring priorities are considered stable enough for handoff artifacts.
```

### 3.4 Update `KNOWN_LIMITATIONS.md`

Add or revise:

```markdown
## Enhanced scoring calibration limitations

- Enhanced scoring remains opt-in.
- Architecture centrality depends on availability and quality of `architecture-graph.json`.
- Change frequency depends on local git history.
- Shallow clones fall back to Low for change frequency.
- Rename history may be incomplete for complex path moves.
- Calibration evidence packs are sidecar validation artifacts, not canonical product outputs.
```

### 3.5 Update `docs/SCORING.md`

Add:

```markdown
## Calibration and evidence packs

Pharabius v1.5.1 adds a scoring evidence pack workflow for validating enhanced scoring behavior across repositories.

Evidence packs are sidecar artifacts used by maintainers to inspect score changes, priority movement, provenance, warnings, runtime, and stability invariants.
```

If W40-S05 changed thresholds, include:

```markdown
## v1.5.1 threshold changes

| Factor | v1.5.0 | v1.5.1 | Reason |
|---|---|---|---|
| architecture_centrality | ... | ... | ... |
| change_frequency | ... | ... | ... |
```

If W40-S05 did not change thresholds, include:

```markdown
## v1.5.1 threshold decision

No threshold changes were made in v1.5.1. Calibration evidence did not justify changing the conservative v1.5.0 thresholds.
```

### 3.6 Optional: add release validation note

Create:

```text
docs/release-notes/v1.5.1-validation-summary.md
```

Include:

```markdown
# v1.5.1 Validation Summary

## Gates

| Gate | Result |
|---|---|
| ruff format --check | PASS |
| ruff check | PASS |
| mypy src | PASS |
| lint-imports | PASS |
| pytest | PASS |
| python -m build | PASS |
| validate_repo.py | PASS |

## Scoring validation

| Check | Result |
|---|---|
| Default behavior unchanged | PASS |
| Enhanced scoring opt-in | PASS |
| Preview mode non-mutating | PASS |
| Finding IDs stable | PASS |
| Evidence IDs stable | PASS |
```

---

## 4. Tests

Documentation-only finalization still requires full gates because version and packaging metadata change.

Recommended tests:

- Existing test suite.
- Build test.
- Self-validation test.
- Optional JSON example validation from W40-S01.

---

## 5. Verification commands

```bash
ruff format --check .
ruff check .
mypy src
lint-imports
pytest
python -m build
python scripts/validate_repo.py .
```

Additional release checks:

```bash
python -m pip install dist/pharabius-1.5.1-py3-none-any.whl --force-reinstall
ai-debt --version
ai-debt analyze --scoring-preview
```

Optional evidence pack check:

```bash
python scripts/validate_v151_scoring_calibration.py \
  --repo Pharabius=. \
  --output .ai-debt/reports/scoring-evidence-pack.json \
  --markdown-output .ai-debt/reports/scoring-evidence-pack.md
```

---

## 6. Expected behavior

After this slice:

- Package reports version `1.5.1`.
- Changelog accurately describes the release.
- Roadmap reflects Wave 40 completion and next direction.
- Known limitations document enhanced scoring calibration limitations.
- Scoring documentation explains evidence packs and threshold decision.
- No runtime behavior changes are introduced by this finalization slice.

---

## 7. Acceptance criteria

- [ ] Version is updated to `1.5.1`.
- [ ] Changelog includes v1.5.1 entry.
- [ ] Roadmap includes v1.5.1 status and next recommendation.
- [ ] Known limitations include calibration/evidence-pack limitations.
- [ ] Scoring docs include evidence pack workflow.
- [ ] Threshold decision is documented: either no-op or tuned with evidence.
- [ ] No production code changes beyond version metadata.
- [ ] All 7 gates pass.
- [ ] Built package reports `1.5.1`.

---

## 8. Rollback plan

Revert documentation and version metadata changes. No functional code behavior should be affected by this slice.
