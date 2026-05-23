# Wave 45 — v1.8.0 Portfolio Summary Foundation

Goal: Add repository-local portfolio summary artifacts that consolidate one or more Pharabius runs into a lightweight portfolio view, without adding a server, dashboard, scheduler, database, remote repository crawler, or external integration.

Release target: `v1.8.0`  
Branch target: `roadmap/v1.8.0-portfolio-summary`  
Boundary: File-based, repository-local or workspace-local portfolio summaries only.

# W45-S01 — Portfolio Summary Artifact Contract

Risk: Medium  
Slice type: Schema / artifact contract  
Artifact impact: New portfolio sidecar artifacts only

## Scope

Define the versioned artifact contract for repository-local or workspace-local portfolio summaries. This slice introduces schemas and expected file layout only. It should not yet perform full aggregation across multiple repositories.

The contract should allow Pharabius to summarize one or more existing `.ai-debt/` outputs into a deterministic portfolio view.

## Goals

- Define portfolio summary schema.
- Define repository portfolio entry schema.
- Define validation/readiness rollup schema.
- Define artifact file layout.
- Keep all outputs file-based and deterministic.
- Preserve compatibility with existing `.ai-debt/` artifacts.
- Avoid server/database/dashboard scope.

## Patch Set

Expected files/modules:

```text
src/pharabius/schemas/portfolio.py          # new
src/pharabius/core/portfolio.py             # new minimal writer/helpers
tests/test_portfolio_schema.py              # new
docs/PORTFOLIO.md                           # optional stub or later in S06
```

Recommended artifact layout:

```text
.ai-debt/portfolio/
  portfolio-summary.json
  portfolio-summary.md
  repository-index.json
  validation-rollup.md
```

Recommended schema shape:

```python
class PortfolioRepositoryEntry(BaseModel):
    repository_id: str
    project_name: str
    repository_path: str
    branch: str | None = None
    commit: str | None = None
    generated_at: str | None = None
    total_findings: int = 0
    priority_counts: dict[str, int] = {}
    top_categories: list[str] = []
    highest_priority: str | None = None
    has_ticket_drafts: bool = False
    has_export_bundles: bool = False
    validation_status: Literal["complete", "partial", "needs_review", "unknown"] = "unknown"
    limitations: list[str] = []
```

Recommended Markdown sections:

```markdown
# Portfolio Summary

## Summary
## Repositories
## Aggregate Risk
## Category Rollup
## Readiness Rollup
## Validation Warnings
## Limitations
```

## Tests

Add tests for:

- Portfolio schema accepts valid minimal data.
- Portfolio schema rejects invalid readiness status.
- Repository entry defaults are safe.
- Portfolio summary is JSON-serializable.
- Markdown rendering is deterministic.
- Artifact paths are stable.
- No source `.ai-debt` artifact mutation occurs.

## Targeted Verification

```bash
pytest tests/test_portfolio_schema.py
```

## Expected Behavior

After this slice, the project has a stable internal contract for future portfolio aggregation.

No user-facing CLI command is required yet.

## Acceptance Criteria

- Portfolio schemas exist and are tested.
- Portfolio artifact layout is documented in code or tests.
- JSON output shape is deterministic.
- No existing canonical artifact contract changes.
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

