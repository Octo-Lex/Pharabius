# AI Adapter — Pharabius v0.7.0

## Overview

Pharabius v0.7.0 adds a provider-neutral, schema-validated, evidence-constrained AI enrichment layer.

**Key principle:** AI enriches existing deterministic findings. It never replaces them.

## Quick Start

```bash
# Run deterministic pipeline first
ai-debt run -r /path/to/repo

# Enrich with mock provider (for testing)
ai-debt enrich --provider mock -r /path/to/repo

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
```

## Provider Modes

| Provider | Behavior | Network |
|---|---|---|
| `disabled` | No-op. Prints disabled message. | No |
| `mock` | Returns deterministic schema-valid test output | No |

**No real network provider in v0.7.0.** Future versions may add OpenAI, Claude, or local model providers.

## Output Contract

When `--provider mock` runs successfully:

```
.ai-debt/ai/
    enrichment-report.json      # Full report with context summary, enrichments, rejections
    enrichment-report.md        # Human-readable markdown version
    finding-enrichments.json    # Valid enrichments only (for programmatic access)
    rejected-ai-output.json     # Rejected outputs with reasons
```

**This directory is not read by any other Pharabius command in v0.7.0.** It is completely optional and does not affect deterministic workflows.

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
3. Finding ID existence
4. Evidence ID existence
5. Analysis unit ID existence (if provided)
6. Graph ID existence (if provided)
7. Confidence format (High/Medium/Low)
8. Limitations non-empty

Invalid output is written to `rejected-ai-output.json` with reasons.

## Architecture

```
cli.py
  → ai.enricher.enrich_findings()
    → ai.context.build_enrichment_context()   # Read artifacts, assemble context
    → ai.adapter.generate_json()               # Call provider (mock/disabled)
    → ai.validator.validate_raw_output()       # Validate against schemas + IDs
    → write .ai-debt/ai/ sidecar files
```

### Import contract

```
pharabius.ai imports from:   pharabius.schemas
pharabius.ai does NOT import from: pharabius.core, pharabius.cli
pharabius.cli imports from:  pharabius.ai.enricher
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

See `docs/KNOWN_LIMITATIONS.md` items 41–47 for AI-specific limitations.

Key points:
- No real AI provider in v0.7.0
- AI enrichments are sidecar records, not canonical findings
- AI does not mutate debt-register.json or any canonical artifact
- Context assembly is bounded — may omit some evidence
- No report integration in v0.7.0
- `ai-debt enrich` is not part of `ai-debt run`
