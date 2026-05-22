# Scoring Evidence Pack

## Purpose

The scoring evidence pack is a non-canonical validation sidecar used to evaluate
enhanced risk scoring behavior across repositories. It summarizes how scores,
priorities, and provenance change when enhanced scoring is enabled versus the
default v1.4.0-compatible scoring.

## Artifact status

- **Non-canonical** — not read by any Pharabius command.
- Does not affect `debt-register.json` scoring.
- Does not affect work package ordering.
- Does not affect review sidecar decisions.
- Safe to delete and regenerate at any time.
- Not committed to version control (in `.gitignore`).

## Output files

| File | Audience | Format |
|---|---|---|
| `.ai-debt/reports/scoring-evidence-pack.json` | Machines, regression tests | JSON |
| `.ai-debt/reports/scoring-evidence-pack.md` | Human reviewers | Markdown |

## Required JSON fields

### Top level

| Field | Type | Description |
|---|---|---|
| `schema_version` | `string` | Evidence pack schema version (`"1.0"`) |
| `tool_version` | `string` | Pharabius version that produced the pack |
| `generated_at` | `string` | ISO 8601 timestamp |
| `analysis_mode` | `string` | `"enhanced_scoring_validation"` |
| `repositories` | `array` | Per-repository results (see below) |
| `summary` | `object` | Aggregate pass/fail counts |

### Repository entry

| Field | Type | Description |
|---|---|---|
| `name` | `string` | Repository display name |
| `path` | `string` | Relative or absolute path |
| `commit` | `string` | HEAD commit SHA at validation time |
| `default_findings` | `integer` | Finding count with default scoring |
| `enhanced_findings` | `integer` | Finding count with enhanced scoring |
| `finding_ids_stable` | `boolean` | IDs unchanged between modes |
| `evidence_ids_stable` | `boolean` | Evidence IDs unchanged between modes |
| `canonical_mutation_in_preview` | `boolean` | Whether preview mode mutated canonical artifacts |
| `score_changes` | `array` | Per-finding score deltas (see below) |
| `warnings` | `array` | Non-fatal issues encountered |
| `runtime_seconds` | `object` | Default/enhanced/preview runtimes |

### Score change entry

| Field | Type | Description |
|---|---|---|
| `finding_id` | `string` | Finding identifier (e.g., `TD-ARCH-001`) |
| `title` | `string` | Finding title |
| `category` | `string` | Debt category |
| `before_score` | `integer` | Default mode risk score |
| `after_score` | `integer` | Enhanced mode risk score |
| `before_priority` | `string` | Default mode priority |
| `after_priority` | `string` | Enhanced mode priority |
| `changed_factors` | `array` | Factor-level provenance deltas |

### Changed factor entry

| Field | Type | Description |
|---|---|---|
| `factor` | `string` | Factor name (e.g., `architecture_centrality`) |
| `before_level` | `string` | Default level |
| `after_level` | `string` | Enhanced level |
| `before_value` | `integer` | Default numeric value |
| `after_value` | `integer` | Enhanced numeric value |
| `source` | `string` | Data source for enhanced value |
| `reason` | `string` | Human-readable explanation |

### Summary

| Field | Type | Description |
|---|---|---|
| `repositories_checked` | `integer` | Total repos validated |
| `repositories_passed` | `integer` | Repos with all checks passing |
| `score_changes_total` | `integer` | Total score changes observed |
| `priority_changes_total` | `integer` | Total priority band changes |
| `preview_mutation_failures` | `integer` | Preview mode canonical mutation count |
| `id_stability_failures` | `integer` | Finding/evidence ID instability count |

## Interpretation guide

1. **Score changes** are expected when enhanced scoring is enabled. An increase
   means the finding's risk factors are elevated by graph/git data; a decrease
   means the default factors were overstating risk.

2. **Priority changes** (band shifts) are more operationally significant than
   raw score changes. A finding moving from Medium to High may reorder work
   packages.

3. **Provenance** (`source` and `reason`) explains *why* a factor changed.
   Without provenance, a score change is unexplained and should be investigated.

4. **Preview mutation failures** must be zero. If preview mode mutates canonical
   artifacts, the validation fails immediately.

5. **ID stability failures** must be zero. Finding and evidence IDs must be
   deterministic across scoring modes.

## Calibration rules

- **No evidence → no calibration.** Threshold tuning (S05) must not proceed
  without evidence packs from at least 3 real repositories.
- Evidence packs from synthetic/test repos are advisory only.
- Calibration changes require a new evidence pack proving the improvement.
- All threshold changes must preserve default scoring identity with v1.4.0.
