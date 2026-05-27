# Pharabius v2.0 — Local CI Quality Gate

Product thesis: Pharabius v2.0 enters developer workflow through a local, deterministic CI quality gate without becoming infrastructure.

Core boundary:
- No server
- No database requirement
- No dashboard service
- No remote repository crawling
- No external API writes
- No issue creation
- No autonomous remediation
- No production code modification

Primary command target:

```bash
ai-debt gate
```

Primary outputs:

```text
.ai-debt/reports/quality-gate.json
.ai-debt/reports/quality-gate.md
```

## Config location

Use `config.yaml`.

Recommended section:

```yaml
quality_gate:
  enabled: true
  mode: strict

  thresholds:
    max_critical: 0
    max_high: 5
    max_blocking_gaps: 0

  fail_on:
    contract_drift: true
    readiness_needs_review: true
    missing_required_artifacts: true

  warn_on:
    missing_optional_artifacts: true
    inferred_claims: false
    partial_readiness: true

  output:
    markdown: true
    json: true
```

## Rule set v2.0

| Rule ID | Rule | Default | Severity |
|---|---|---:|---|
| `max_critical_findings` | Critical findings must not exceed threshold | 0 | error |
| `max_high_findings` | High findings must not exceed threshold | configurable | error |
| `max_blocking_gaps` | Blocking gaps must not exceed threshold | 0 | error |
| `contract_drift` | Artifact contract must not have errors | true | error |
| `readiness_needs_review` | v1 readiness must not be `needs_review` | true | error |
| `missing_required_artifacts` | Required artifacts must exist | true | error |
| `missing_optional_artifacts` | Optional artifacts should exist | true | warning |
| `partial_readiness` | Partial readiness should be visible | true | warning |
| `inferred_claims` | Inferred claims may warn if configured | false | warning |

## Evaluation order

```text
1. Load config
2. Apply CLI overrides
3. Load required artifacts
4. Evaluate missing required artifacts
5. Evaluate debt register thresholds
6. Evaluate blocking gaps
7. Evaluate contract drift
8. Evaluate readiness status
9. Evaluate warnings
10. Compute final result
11. Write reports
12. Return exit code
```

## Result calculation

```text
If any error-level violation exists:
  result = fail
Else if any warning-level violation exists:
  result = warn
Else:
  result = pass
```

Mode affects exit code, not result.

## Acceptance criteria

- Defaults are conservative.
- CLI overrides are deterministic and test-covered.
- Missing required artifacts are fail-level in strict mode.
- Warning rules do not produce fail result unless configured as fail rules.
- Config supports future expansion without requiring v2.0 to become a full policy engine.
