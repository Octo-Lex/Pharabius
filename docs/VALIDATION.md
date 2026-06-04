# Validation Methodology & Results

## What was validated

v3.6.0 validated 8 synthetic fixtures. v3.7.0 adds **3 pinned public OSS repositories** and introduces **advisory classification** for structural hygiene signals.

### Synthetic benchmarks (8 fixtures)

| Fixture | Languages | Key signals |
|---------|-----------|-------------|
| small-python-package | Python | pyproject.toml, 5 files |
| medium-python-service | Python | Unpinned deps, low coverage, long functions, broad exceptions, debt markers |
| small-node-package | JavaScript | Unpinned package.json |
| medium-node-app | TypeScript+JS | Unpinned deps, Istanbul coverage, broad exception |
| mixed-python-node | Python+JS | Dual ecosystem manifests |
| coverage-heavy | Python+Java+JS | 4 coverage formats: JSON, Istanbul, LCOV, JaCoCo |
| poor-hygiene | Python+JS | All deps unpinned, no runtime pins, no lockfiles |
| clean-baseline | Python | All pinned, runtime pin, 92% coverage |

### OSS benchmarks (3 pinned repositories)

| Name | Upstream | Commit | Languages | License |
|------|----------|--------|-----------|---------|
| python-click | pallets/click | `c4802104` | Python | BSD-3-Clause |
| node-uuid | uuidjs/uuid | `664cb316` | JavaScript | MIT |
| typescript-json-schema | YousefED/typescript-json-schema | `e9246330` | TypeScript | BSD-3-Clause |

Snapshots are committed as `.tar.gz` files in `benchmarks/oss/snapshots/` with SHA-256 verification. Tests do not require network access.

---

## Methodology

### Finding quality rubric

5 weighted criteria evaluate whether findings are useful:

| Criterion | Weight | Evaluator |
|-----------|--------|-----------|
| Actionable | 3 | `recommended_action` is ≥20 chars and not vague |
| Evidence-linked | 2 | At least one `evidence_id` |
| Not duplicate | 2 | Unique by (category, locations, title prefix) |
| Not trivial | 1 | `risk_score > 5` or High+ severity |
| Specific location | 1 | At least one non-empty location |

Score range: 0.0–1.0. Noise threshold: <0.4.

### Advisory classification (v3.7.0)

Structural hygiene signals are now classified as **advisories** rather than technical debt:

| Signal | `issue_type` | Severity cap | Generates WPs? | Generates claims? |
|--------|-------------|-------------|----------------|-------------------|
| Missing CI/CD (TD-BUILD) | advisory | Low | No | No |
| Missing docs (TD-DOC) | advisory | Low | No | No |
| Missing process artifacts (TD-PROCESS) | advisory | Low | No | No |
| Missing lockfile (TD-DEP) | advisory | Low | No | No |
| Unpinned dependencies (TD-DEP) | technical_debt | Normal | Yes | Yes |
| Code quality defects | technical_debt | Normal | Yes | Yes |
| Low coverage from reports | technical_debt | Normal | Yes | Yes |

Advisories:
- Are capped at severity "Low" with risk_score ≤ 10
- Do not generate work packages by default
- Do not generate operational claims by default
- Are reported in a separate "Advisory Signals" section
- Are counted separately in run history snapshots (`advisory_count`, `advisories_by_category`)
- Are excluded from finding trend calculations (trend uses `technical_debt_count`)

### Calibration policy

Default: **observe, document, keep**. Threshold changes require:
1. Benchmark evidence showing clear noise or under-detection
2. All existing tests passing
3. All benchmark tests passing
4. Before/after rationale in this document

---

## Threshold calibration results

| Threshold | Value | Decision | Rationale |
|-----------|-------|----------|-----------|
| LARGE_FILE_LINE_THRESHOLD | 1000 | **Keep** | No large files in any fixture triggered noise |
| LONG_FUNCTION_LINE_THRESHOLD | 80 | **Keep** | 100-line functions detected correctly |
| BROAD_EXCEPTION_PER_FILE_THRESHOLD | 3 | **Keep** | 4-exception files detected correctly |
| MIN_DEBT_MARKER_OCCURRENCES | 5 | **Keep** | 8-marker files detected correctly |
| COVERAGE_LOW_THRESHOLD_PCT | 60.0 | **Keep** | 45% coverage correctly flagged |
| DEFAULT_MAX_FILE_SIZE_KB | 500 | **Keep** | No files exceeded 500KB in any fixture |

**No threshold changes needed.**

---

## Structural signal calibration (v3.7.0)

### Before advisory classification

| Fixture | Total | Structural (TD-BUILD/DOC/PROCESS) | Lockfile (TD-DEP) | Advisory would be |
|---------|-------|-----------------------------------|--------------------|--------------------|
| clean-baseline | 5 | 3 | 1 | 4 of 5 |
| small-python-package | 6 | 3 | 1 | 4 of 6 |
| medium-python-service | 7 | 3 | 1 | 4 of 7 |
| small-node-package | 5 | 2 | 1 | 3 of 5 |
| medium-node-app | 6 | 3 | 1 | 4 of 6 |
| mixed-python-node | 6 | 2 | 2 | 4 of 6 |
| coverage-heavy | 7 | 3 | 1 | 4 of 7 |
| poor-hygiene | 7 | 2 | 2 | 4 of 7 |

**Observation:** 40–80% of findings in synthetic fixtures were structural hygiene signals. This explains why clean-baseline appeared noisy.

### After advisory classification

| Fixture | technical_debt_count | advisory_count | High/Critical debt |
|---------|---------------------|---------------|-------------------|
| clean-baseline | 1 | 4 | 0 |
| small-python-package | 2 | 4 | 0 |
| medium-python-service | 3 | 4 | 1 |
| small-node-package | 2 | 3 | 0 |
| medium-node-app | 2 | 4 | 0 |
| mixed-python-node | 2 | 4 | 0 |
| coverage-heavy | 3 | 4 | 0 |
| poor-hygiene | 3 | 4 | 1 |

**Clean-baseline now shows: 1 technical debt finding (TD-TEST), 0 High/Critical.** This matches the clean-baseline quietness policy.

### Classification boundary warning

```text
v3.7.0 reclassified selected structural hygiene signals as advisories.
Apparent finding-count improvement may reflect classification changes,
not repository remediation.
```

Run history trend calculations use `technical_debt_count` (not `total_findings`) to avoid this distortion. A classification-boundary warning is emitted when comparing pre-v3.7.0 vs v3.7.0+ runs.

---

## Clean-baseline quietness policy

A clean/healthy repo should not produce High/Critical technical debt findings. It may produce:
- Evidence observations
- Low-severity advisories (structural hygiene)
- Limitations

**Enforced thresholds for clean-baseline:**
- `technical_debt_count` ≤ 1
- `high` = 0, `critical` = 0
- `advisory_count` = 3–4 (expected)
- Work packages ≤ 1

---

## Finding quality scores

| Fixture | Avg quality | Noise rate | Target quality | Target noise | Pass |
|---------|------------|------------|---------------|-------------|------|
| clean-baseline | 0.911 | 0.000 | 0.80 | 0.10 | ✅ |
| coverage-heavy | 0.889 | 0.000 | 0.60 | 0.20 | ✅ |
| medium-node-app | 0.944 | 0.000 | 0.60 | 0.20 | ✅ |
| medium-python-service | 0.963 | 0.000 | 0.60 | 0.20 | ✅ |
| mixed-python-node | 0.951 | 0.000 | 0.60 | 0.20 | ✅ |
| poor-hygiene | 0.951 | 0.000 | 0.50 | 0.25 | ✅ |
| small-node-package | 0.937 | 0.000 | 0.70 | 0.15 | ✅ |
| small-python-package | 0.937 | 0.000 | 0.70 | 0.15 | ✅ |

---

## Performance smoke test (v3.7.0)

| Metric | 1000-file synthetic repo | Bound |
|--------|--------------------------|-------|
| Runtime | 7.8s | < 60s |
| Output size | 0.65 MB | < 50 MB |
| Completed | Yes | Must complete |
| Findings | 6 (2 debt + 4 advisory) | — |

---

## OSS validation results

*To be populated after running validation against pinned snapshots during release.*

---

## Known issues

1. **OSS validation is a small sample** — 3 repos cannot represent all ecosystems. Field truth remains partial.
2. **Small fixtures don't produce Critical findings** — larger, more complex repos would be needed.
3. **Pre-v3.7.0 runs have no `technical_debt_count`** — trend comparisons emit classification-boundary warning.
4. **Advisory classification is a judgment call** — governance presets may later promote advisories to findings.

---

## Recommendations for v3.8.0

1. Runtime version conflict detection (carry-forward from v3.3.0)
2. Ruby/Java runtime pin detection (carry-forward from v3.3.0)
3. Expand OSS corpus to 5–10 repos for broader coverage
4. Investigate whether TD-TEST (no test evidence) should also be advisory for clean repos
5. AST-based analysis (replace indentation heuristic)
