# W40-S04 — Add Field Validation Summary Command/Script

**Wave:** Wave 40 — v1.5.1 Scoring Calibration & Evidence Pack  
**Slice:** W40-S04  
**Title:** Add field validation summary command/script  
**Risk:** Medium  
**Impact class:** Tooling only  
**Release target:** v1.5.1  
**Implementation unit:** Atomic slice; should land after W40-S01 and preferably after W40-S03

---

## 1. Scope

Add a validation script that runs or summarizes enhanced scoring validation across a list of repositories and emits the scoring evidence pack artifacts defined in W40-S01.

This is tooling-only. It must not modify production scoring behavior.

### In scope

- Add a script for scoring calibration validation.
- Generate `.ai-debt/reports/scoring-evidence-pack.json`.
- Generate `.ai-debt/reports/scoring-evidence-pack.md`.
- Compare default, enhanced, reset-default, and preview modes.
- Check finding ID and evidence ID stability.
- Check preview mode non-mutation.
- Capture runtime and warnings.
- Add tests for summary generation and failure handling.

### Out of scope

- No production threshold tuning.
- No canonical artifact schema changes.
- No scoring computation changes.
- No network access.
- No GitHub API calls.
- No issue tracker integration.
- No release automation.

---

## 2. Goals

1. Make field validation repeatable.
2. Produce a reviewable evidence pack for v1.5.1 calibration.
3. Support threshold tuning decisions with measured data.
4. Detect accidental canonical mutation in preview mode.
5. Keep validation local and deterministic at fixed commits.

---

## 3. Proposed script

Add:

```text
scripts/validate_v151_scoring_calibration.py
```

Suggested usage:

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

Optional convenience:

```bash
python scripts/validate_v151_scoring_calibration.py --repos-file validation-repos.json
```

Example `validation-repos.json`:

```json
{
  "repositories": [
    {"name": "Pharabius", "path": "../Pharabius"},
    {"name": "validation-java", "path": "../validation-java"}
  ]
}
```

---

## 4. Patch set

### 4.1 Add validation script

Create:

```text
scripts/validate_v151_scoring_calibration.py
```

Responsibilities:

1. Parse repository list.
2. For each repo:
   - Capture current commit and branch if available.
   - Run default analysis.
   - Capture canonical hash and finding/evidence IDs.
   - Run enhanced scoring analysis.
   - Capture score and priority changes.
   - Run default analysis/reset behavior.
   - Confirm scores restored.
   - Run scoring preview.
   - Confirm canonical hash unchanged.
   - Capture warnings and runtimes.
3. Emit JSON evidence pack.
4. Emit Markdown evidence pack.
5. Exit non-zero if a required invariant fails.

### 4.2 Suggested internal functions

```python
def run_command(args: list[str], cwd: Path, timeout_seconds: int) -> CommandResult:
    ...


def hash_file(path: Path) -> str:
    ...


def load_debt_register(repo: Path) -> dict[str, Any]:
    ...


def extract_finding_snapshot(register: dict[str, Any]) -> FindingSnapshot:
    ...


def compare_default_to_enhanced(default: FindingSnapshot, enhanced: FindingSnapshot) -> RepositoryScoringDelta:
    ...


def render_evidence_pack_markdown(pack: ScoringEvidencePack) -> str:
    ...
```

### 4.3 Add tests

Create:

```text
tests/test_validate_v151_scoring_calibration.py
```

Test only pure functions and mocked subprocess behavior. Do not require external validation repositories in unit tests.

Required tests:

```python
def test_hash_file_is_stable(tmp_path):
    ...


def test_extract_finding_snapshot_reads_scores_priorities_and_ids():
    ...


def test_compare_default_to_enhanced_detects_score_changes():
    ...


def test_compare_default_to_enhanced_detects_priority_changes():
    ...


def test_preview_mutation_failure_is_reported():
    ...


def test_evidence_pack_markdown_contains_summary_tables():
    ...
```

### 4.4 Output schema

Emit JSON compatible with W40-S01:

```json
{
  "schema_version": "1.0",
  "tool_version": "1.5.1-dev",
  "generated_at": "...",
  "analysis_mode": "enhanced_scoring_validation",
  "repositories": [],
  "summary": {}
}
```

---

## 5. Validation invariants

The script must check:

| Invariant | Failure behavior |
|---|---|
| Default run succeeds | repo status FAIL |
| Enhanced run succeeds | repo status FAIL |
| Reset/default run restores default scoring | repo status FAIL |
| Preview does not mutate canonical debt register | repo status FAIL |
| Finding IDs stable | repo status FAIL |
| Evidence IDs stable | repo status FAIL |
| Enhanced scoring changes only allowed fields | repo status FAIL |
| Runtime captured | warning if missing |
| Graph/git fallback warning captured | warning, not failure unless unexpected |

Allowed fields to change in enhanced canonical output:

```text
risk_score
priority
risk_breakdown.architecture_centrality
risk_breakdown.change_frequency
updated_at / generated_at / run metadata if already expected
```

---

## 6. Verification commands

```bash
ruff format --check .
ruff check .
mypy src
pytest tests/test_validate_v151_scoring_calibration.py
python scripts/validate_v151_scoring_calibration.py --help
python -m build
python scripts/validate_repo.py .
```

Field validation command:

```bash
python scripts/validate_v151_scoring_calibration.py \
  --repo Pharabius=. \
  --output .ai-debt/reports/scoring-evidence-pack.json \
  --markdown-output .ai-debt/reports/scoring-evidence-pack.md
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

- Maintainers can run one script to summarize scoring behavior across repositories.
- The script emits the evidence pack JSON and Markdown artifacts.
- Preview mutation is automatically detected.
- ID stability is automatically detected.
- Validation failures are explicit and machine-readable.
- No production scoring behavior changes occur.

---

## 8. Acceptance criteria

- [ ] `scripts/validate_v151_scoring_calibration.py` exists.
- [ ] Script supports multiple repositories.
- [ ] Script emits JSON evidence pack.
- [ ] Script emits Markdown evidence pack.
- [ ] Script checks preview non-mutation.
- [ ] Script checks finding ID stability.
- [ ] Script checks evidence ID stability.
- [ ] Script checks reset/default behavior.
- [ ] Script captures score and priority changes.
- [ ] Unit tests cover pure comparison/reporting logic.
- [ ] No production scoring behavior changes.
- [ ] All 7 gates pass.

---

## 9. Rollback plan

Revert the validation script and tests. No runtime product behavior or canonical artifact behavior is affected.
