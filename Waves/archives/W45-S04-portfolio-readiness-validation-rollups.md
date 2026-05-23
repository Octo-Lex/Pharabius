# Wave 45 — v1.8.0 Portfolio Summary Foundation

Goal: Add repository-local portfolio summary artifacts that consolidate one or more Pharabius runs into a lightweight portfolio view, without adding a server, dashboard, scheduler, database, remote repository crawler, or external integration.

Release target: `v1.8.0`  
Branch target: `roadmap/v1.8.0-portfolio-summary`  
Boundary: File-based, repository-local or workspace-local portfolio summaries only.

# W45-S04 — Portfolio Readiness and Validation Rollups

Risk: Medium  
Slice type: Readiness analytics / validation rollup  
Artifact impact: Portfolio sidecar artifacts only

## Scope

Add portfolio-level readiness and validation rollups. This slice summarizes whether repositories appear ready for PET execution, ticket drafting, tracker export review, or further validation.

It must not make business decisions or acceptance decisions. It reports status only.

## Goals

- Aggregate repository validation status.
- Summarize ticket draft availability.
- Summarize export bundle availability.
- Summarize validation warnings/limitations.
- Identify repositories needing review.
- Generate `validation-rollup.md`.
- Preserve human ownership of decisions.

## Patch Set

Expected files/modules:

```text
src/pharabius/core/portfolio.py
src/pharabius/schemas/portfolio.py
tests/test_portfolio_readiness_rollups.py
```

Recommended readiness fields:

```python
class PortfolioReadinessRollup(BaseModel):
    repositories_total: int
    with_ticket_drafts: int
    with_export_bundles: int
    complete: int
    partial: int
    needs_review: int
    unknown: int
    repositories_needing_review: list[str]
    warnings: list[str] = []
```

Recommended readiness classification:

| Condition | Status |
|---|---|
| Debt register present, no validation warnings, ticket/export artifacts present when expected | complete |
| Debt register present, some optional artifacts missing | partial |
| Missing/malformed required artifacts | needs_review |
| Insufficient data | unknown |

Recommended `validation-rollup.md` sections:

```markdown
# Portfolio Validation Rollup

## Summary
## Readiness by Repository
## Ticket Draft Availability
## Export Bundle Availability
## Repositories Needing Review
## Warnings and Limitations
```

## Tests

Add tests for:

- Complete repository readiness.
- Partial repository readiness.
- Needs-review repository readiness.
- Unknown repository readiness.
- Ticket draft availability counts.
- Export bundle availability counts.
- Warning aggregation.
- `validation-rollup.md` rendering.
- No mutation of source artifacts.

## Targeted Verification

```bash
pytest tests/test_portfolio_readiness_rollups.py
```

## Expected Behavior

Users can see which repositories are ready for planning or import review and which require additional validation.

Example Markdown table:

```markdown
| Repository | Readiness | Ticket Drafts | Export Bundles | Notes |
|---|---|---|---|---|
| service-a | complete | yes | yes | — |
| service-b | needs_review | no | no | missing debt-register.json |
```

## Acceptance Criteria

- Readiness rollup is implemented and tested.
- Validation rollup report is deterministic.
- The rollup reports status, not approval decisions.
- Human review remains required.
- No canonical artifacts are mutated.
- No scoring behavior changes.
- No external API behavior added.
- All 7 local gates pass.
## Guardrails

- Do not add a dashboard, web server, API server, scheduler, queue, or persistent database.
- Do not crawl remote repositories or organizations.
- Do not call GitHub, GitLab, Bitbucket, Jira, Linear, Azure DevOps, or other external APIs.
- Do not create or modify external issues.
- Do not mutate source repositories outside Pharabius output directories.
- Do not mutate source `.ai-debt/debt-register.json` files during aggregation.
- Do not change risk scoring behavior.
- Do not let review sidecar decisions influence scores.
- Do not introduce autonomous remediation or code modification.
- Treat portfolio output as a read-only rollup over existing Pharabius artifacts.

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

