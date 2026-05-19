# AI Adapter — Pharabius v0.7.2

## Overview

Pharabius v0.7.0 adds a provider-neutral, schema-validated, evidence-constrained AI enrichment layer.

**Key principle:** AI enriches existing deterministic findings. It never replaces them.

## Quick Start

```bash
# Run deterministic pipeline first
ai-debt run -r /path/to/repo

# Enrich with mock provider (for testing)
ai-debt enrich --provider mock -r /path/to/repo

# Check sidecar status
ai-debt ai-status -r /path/to/repo

# Machine-readable status
ai-debt ai-status --json -r /path/to/repo

# Dry run (assemble context, validate, but write nothing)
ai-debt enrich --provider mock --dry-run -r /path/to/repo

# Enrich a single finding
ai-debt enrich --provider mock --finding-id TD-DEP-001 -r /path/to/repo
```

## Default Behavior

**AI is disabled by default.**

Running `ai-debt enrich` with no flags prints:

```
AI provider is disabled. Use --provider mock for local testing.
```

## Sidecar Review Workflow

The recommended workflow for reviewing AI enrichments:

```bash
# 1. Run deterministic pipeline
ai-debt analyze --no-ai -r /path/to/repo

# 2. Enrich with mock (or future real provider)
ai-debt enrich --provider mock -r /path/to/repo

# 3. Review sidecar summary
ai-debt ai-status -r /path/to/repo

# 4. Read full report if needed
# Open .ai-debt/ai/enrichment-report.md
```

### What to check

| Question | Where to find the answer |
|---|---|
| Which findings were enriched? | `ai-status` output + Enrichments section |
| Which enrichments were rejected? | `ai-status` output + Rejections section |
| Why were outputs rejected? | Rejection reasons + invalid fields |
| Which evidence IDs support each enrichment? | Per-finding Evidence IDs |
| Were evidence items omitted due to budget? | Evidence omitted count |
| Are canonical artifacts unchanged? | By design + `ai-status` statement |
| What should reviewers trust? | Only deterministic findings in `debt-register.json` |
| What is AI suggestion only? | Everything in `.ai-debt/ai/` |

### `ai-debt ai-status`

Read-only command that summarizes AI sidecar state without modifying anything.

```
AI Sidecar Status

  Provider:              mock
  Model:                 mock-v0.7.0
  Generated:             2026-05-19T00:00:00+00:00

  Findings selected:     5
  Enrichments accepted:  5
  Enrichments rejected:  0
  Evidence referenced:   12
  Evidence omitted:      3

  Canonical artifacts:   not modified (by design)
```

With `--json`:

```json
{
  "sidecar_present": true,
  "provider": "mock",
  "model": "mock-v0.7.0",
  "generated_at": "2026-05-19T00:00:00+00:00",
  "findings_selected": 5,
  "enrichments_accepted": 5,
  "enrichments_rejected": 0,
  "evidence_referenced": 12,
  "evidence_omitted": 3,
  "canonical_artifacts_modified": false,
  "status": "review_recommended"
}
```

**Exit codes:**
- 0: sidecar present and valid, or no sidecar found (informational)
- 1: sidecar directory exists but report is missing or corrupted

### Sharing sidecar files

- `.ai-debt/ai/` may contain summarized repository context
- Review before committing to git
- Consider adding `.ai-debt/ai/` to `.gitignore` for sensitive repos
- Future external providers may send evidence off-machine
- Sidecar files are never read by other Pharabius commands in v0.7.x

## Command Reference

```
ai-debt enrich [OPTIONS]

Options:
  -r, --repository-root PATH     Repository root (default: current directory)
  --provider TEXT                Provider: disabled (default) or mock
  --max-findings INTEGER         Maximum findings to enrich (default: 10)
  --finding-id TEXT              Enrich a single finding by ID
  --dry-run                      Assemble context and validate without writing files
  --strict                       Reject entire batch if any enrichment fails validation

ai-debt ai-status [OPTIONS]

Options:
  -r, --repository-root PATH     Repository root (default: current directory)
  --json                         Output machine-readable JSON
```

## Provider Modes

| Provider | Behavior | Network |
|---|---|---|
| `disabled` | No-op. Prints disabled message. | No |
| `mock` | Returns deterministic schema-valid test output | No |

**No real network provider in v0.7.x.** Future versions may add OpenAI, Claude, or local model providers.

## Output Contract

When `--provider mock` runs successfully:

```
.ai-debt/ai/
    enrichment-report.json      # Full report with context summary, enrichments, rejections
    enrichment-report.md        # Human-readable markdown version
    finding-enrichments.json    # Valid enrichments only (for programmatic access)
    rejected-ai-output.json     # Rejected outputs with reasons
```

**This directory is not read by any other Pharabius command in v0.7.x.** It is completely optional and does not affect deterministic workflows.

## Trust Model

| Property | Enforcement |
|---|---|
| Every enrichment references existing finding ID | Validator checks against debt-register.json |
| Every evidence ID exists in evidence.json | Validator rejects unknown IDs |
| No new findings created | Schema forbids new finding IDs |
| No canonical artifacts modified | Enricher writes to .ai-debt/ai/ only |
| Confidence and limitations explicit | Schema requires both fields |
| No unsupported fields | `model_config = {"extra": "forbid"}` |

## Context Assembly

For each finding, the enricher assembles:

1. **Directly linked evidence** (via `finding.evidence_ids`)
2. **Analysis units** (via `finding.analysis_unit_ids`)
3. **Graph records** (cycles/violations mentioning the finding)
4. **Verification status** (if available)
5. **Known limitations**

Context is bounded by budget controls:

| Parameter | Default |
|---|---|
| Max context chars | 30,000 |
| Max evidence items | 20 |
| Max graph records | 10 |
| Max analysis units | 5 |
| Max output chars | 4,000 |

Items exceeding budget are omitted and recorded in `context_summary`.

## Validation Pipeline

AI output goes through these checks:

1. JSON parse check
2. Schema validation (Pydantic, extra fields forbidden)
3. `enrichments` array must exist
4. Finding ID existence
5. Evidence IDs must be non-empty and all exist
6. Analysis unit ID existence (if provided)
7. Graph ID existence (if provided)
8. Confidence format (High/Medium/Low)
9. Limitations non-empty

Invalid output is written to `rejected-ai-output.json` with reasons.

### Strict vs non-strict mode

- **Non-strict** (default): Valid enrichments are kept; invalid ones are recorded as rejections.
- **Strict** (`--strict`): If any enrichment fails validation, the entire batch is rejected.

### Empty evidence_ids

Enrichments with empty `evidence_ids` are always rejected. The evidence-constrained contract requires at least one valid evidence ID per enrichment.

### Unknown --finding-id

Running `ai-debt enrich --finding-id NONEXISTENT` exits with code 1:
```
Finding ID 'NONEXISTENT' was not found in debt-register.json.
```

## Architecture

```
cli.py
  → ai.enricher.enrich_findings()
    → ai.context.build_enrichment_context()   # Read artifacts, assemble context
    → ai.adapter.generate_json()               # Call provider (mock/disabled)
    → ai.validator.validate_raw_output()       # Validate against schemas + IDs
    → write .ai-debt/ai/ sidecar files

cli.py
  → ai.status_reader.read_ai_status()        # Read sidecar, return summary
```

### Import contract

```
pharabius.ai imports from:   pharabius.schemas
pharabius.ai does NOT import from: pharabius.core, pharabius.cli
pharabius.cli imports from:  pharabius.ai.enricher, pharabius.ai.status_reader
```

### Layer diagram

```
CLI (cli.py)
  ↓
Core Runtime (core/*)
  ↓
AI Adapter (ai/*) ← new in v0.7.0
  ↓
Schemas (schemas/*)
```

## Privacy

- AI is **disabled by default** — no automatic data processing
- v0.7.0 mock provider processes everything locally
- No credentials stored in repository files
- No secrets in logs
- Future external providers will receive repository evidence — privacy caution documented

## Limitations

See `docs/KNOWN_LIMITATIONS.md` items 41–48 for AI-specific limitations.

Key points:
- No real AI provider in v0.7.x
- AI enrichments are sidecar records, not canonical findings
- AI does not mutate debt-register.json or any canonical artifact
- Context assembly is bounded — may omit some evidence
- No report integration in v0.7.x
- `ai-debt enrich` is not part of `ai-debt run`
- `ai-debt ai-status` is read-only and creates/modifies no files
