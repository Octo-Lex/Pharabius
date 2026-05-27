# Wave 48 — v1.10.0 v1 Contract Consolidation & Release Candidate

Goal: Consolidate the v1 artifact contract, command surface, documentation, examples, validation scripts, and release readiness into a coherent v1.10 release candidate without adding a new product capability.

Release target: `v1.10.0`  
Branch target: `roadmap/v1.10.0-v1-contract-consolidation`  
Boundary: Consolidation, validation, documentation, and release-readiness only. No new product capability, no autonomous remediation, no external API writes.

# W48-S05 — v1 Readiness Report Generator

Risk: Medium  
Slice type: Release-readiness reporting / validation sidecar  
Artifact impact: New readiness report artifact only

## Scope

Add a v1 readiness report generator that summarizes the state of the artifact contract, command surface, validation results, documentation coverage, and safety boundaries for a repository or release candidate.

This report is for maintainers and adopters. It should not add new analysis capabilities or alter existing outputs.

## Goals

- Generate `.ai-debt/reports/v1-readiness-report.md`.
- Optionally generate `.ai-debt/reports/v1-readiness-report.json`.
- Summarize required artifact presence.
- Summarize schema/JSON parse status.
- Summarize command/golden-path validation status if available.
- Summarize documentation link coverage if available.
- Summarize safety boundary checks.
- Provide release-candidate readiness status: `ready`, `partial`, `needs_review`.

## Patch Set

Expected files/modules:

```text
src/pharabius/core/v1_readiness.py            # new
src/pharabius/schemas/readiness.py            # optional
tests/test_v1_readiness_report.py             # new
docs/VALIDATION.md                            # update
```

Recommended readiness schema:

```python
class V1ReadinessCheck(BaseModel):
    name: str
    status: Literal["pass", "warning", "fail", "not_applicable"]
    message: str
    artifact_path: str | None = None

class V1ReadinessReport(BaseModel):
    schema_version: str = "1.0"
    generated_at: str
    status: Literal["ready", "partial", "needs_review"]
    checks: list[V1ReadinessCheck]
    summary: dict[str, int]
```

Recommended Markdown sections:

```markdown
# v1 Readiness Report

## Summary
## Artifact Contract Coverage
## Schema Validation
## Command Surface
## Golden Path Validation
## Documentation Coverage
## Safety Boundary Checks
## Warnings
## Release Candidate Verdict
```

Recommended safety checks:

| Check | Expected |
|---|---|
| No external API configuration required | pass |
| No remediation command present | pass |
| Ticket/export workflows are file-based | pass |
| Portfolio is local-only | pass |
| Agent-handoff contract forbids autonomous modification | pass |

## Tests

Add tests for:

- Readiness report generated for complete fixture.
- Missing key artifact yields warning or fail.
- Invalid JSON artifact yields fail.
- Sidecar-only missing optional artifact yields warning.
- Safety boundary text included.
- Status aggregation works.
- Markdown is deterministic.
- JSON report parses if generated.

## Targeted Verification

```bash
pytest tests/test_v1_readiness_report.py
python -m pharabius.cli report --help
```

## Expected Behavior

Users can review one report to understand if a repository’s `.ai-debt/` output is complete and v1-ready.

Expected path:

```text
.ai-debt/reports/v1-readiness-report.md
```

## Acceptance Criteria

- v1 readiness report generator exists.
- Report covers artifacts, schemas, docs, validation, and safety boundaries.
- Readiness status is deterministic.
- Report does not modify canonical artifacts.
- No new product capability is introduced.
- All 7 local gates pass.
## Guardrails

- Do not add a new product capability.
- Do not modify production/source code under analysis.
- Do not generate remediation patches.
- Do not create pull requests or external issues.
- Do not call external APIs.
- Do not add a server, dashboard, scheduler, queue, remote crawler, or database.
- Do not change risk scoring behavior.
- Do not mutate canonical analysis artifacts except where explicitly regenerating validation outputs in controlled tests.
- Do not weaken the no-remediation boundary.
- Treat this wave as a v1 contract consolidation and release-candidate hardening wave.

## Verification Commands

Run the full local gate suite:

```bash
ruff format --check .
ruff check .
mypy src
lint-imports
pytest
python -m build
python scripts/validate_repo.py .
```

Additional targeted checks for this slice are listed below.

