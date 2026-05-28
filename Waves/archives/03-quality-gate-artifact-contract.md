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

## JSON artifact

Path:

```text
.ai-debt/reports/quality-gate.json
```

Recommended schema:

```json
{
  "schema_version": "1.0",
  "generated_at": "",
  "tool_version": "",
  "repository": "",
  "branch": "",
  "commit": "",
  "mode": "strict",
  "result": "pass",
  "summary": {
    "critical_findings": 0,
    "high_findings": 0,
    "medium_findings": 0,
    "low_findings": 0,
    "blocking_gaps": 0,
    "contract_drift_errors": 0,
    "readiness_status": "ready",
    "missing_required_artifacts": 0,
    "missing_optional_artifacts": 0
  },
  "rules": [],
  "violations": [],
  "warnings": [],
  "recommended_actions": []
}
```

## Core models

```python
class QualityGateMode(str, Enum):
    STRICT = "strict"
    WARN = "warn"
    ADVISORY = "advisory"

class QualityGateResult(str, Enum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"

class QualityGateViolation(BaseModel):
    rule_id: str
    severity: Literal["error", "warning"]
    message: str
    observed: str | int | bool | None = None
    expected: str | int | bool | None = None
    artifact: str | None = None
    recommended_action: str | None = None
```

## Markdown artifact

Path:

```text
.ai-debt/reports/quality-gate.md
```

Recommended sections:

```markdown
# Pharabius Quality Gate

## Result
## Summary
## Rule Results
## Violations
## Warnings
## Recommended Actions
## Artifact Inputs
## Safety Boundary
```

## Acceptance criteria

- JSON schema is versioned.
- Markdown and JSON carry equivalent result information.
- Reports are deterministic.
- Safety boundary is explicitly stated.
- Reports do not imply external write behavior.
