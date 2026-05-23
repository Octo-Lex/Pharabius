# Wave 45 — v1.8.0 Portfolio Summary Foundation

Goal: Add repository-local portfolio summary artifacts that consolidate one or more Pharabius runs into a lightweight portfolio view, without adding a server, dashboard, scheduler, database, remote repository crawler, or external integration.

Release target: `v1.8.0`  
Branch target: `roadmap/v1.8.0-portfolio-summary`  
Boundary: File-based, repository-local or workspace-local portfolio summaries only.

# W45-S03 — Portfolio Risk/Category Rollups

Risk: Medium  
Slice type: Portfolio analytics / deterministic rollups  
Artifact impact: Portfolio sidecar artifacts only

## Scope

Add deterministic rollups across repository entries for priorities, categories, highest-risk repositories, and top category concentrations.

This slice should operate only on already-extracted portfolio repository entries from W45-S02.

## Goals

- Compute aggregate priority counts.
- Compute aggregate category counts.
- Identify repositories with highest risk concentration.
- Identify dominant technical debt categories.
- Render rollups in JSON and Markdown.
- Keep rollups deterministic and evidence-derived.
- Avoid new scoring formulas or score recalculation.

## Patch Set

Expected files/modules:

```text
src/pharabius/core/portfolio.py
src/pharabius/schemas/portfolio.py
tests/test_portfolio_rollups.py
```

Recommended rollups:

```python
class PortfolioRiskRollup(BaseModel):
    aggregate_priority_counts: dict[str, int]
    aggregate_category_counts: dict[str, int]
    top_risk_repositories: list[str]
    top_categories: list[str]
    total_findings: int
```

Recommended priority ordering:

```text
Critical > High > Medium > Low
```

Recommended category ordering:

```text
count desc, category asc
```

Recommended repository ordering:

```text
critical desc, high desc, medium desc, low desc, repository_id asc
```

## Tests

Add tests for:

- Priority counts across multiple repositories.
- Category counts across multiple repositories.
- Empty repository list.
- Repositories with missing category summaries.
- Stable category ordering.
- Stable top-risk repository ordering.
- No recalculation of finding scores.
- Markdown rollup includes expected tables.

## Targeted Verification

```bash
pytest tests/test_portfolio_rollups.py
```

## Expected Behavior

Portfolio summary can answer:

- How many Critical/High/Medium/Low findings exist across the selected repos?
- Which categories dominate?
- Which repositories require attention first?
- Which repositories have no current findings?

Example Markdown table:

```markdown
## Aggregate Risk

| Priority | Count |
|---|---:|
| Critical | 1 |
| High | 8 |
| Medium | 21 |
| Low | 13 |
```

## Acceptance Criteria

- Rollups are computed from repository summaries only.
- No risk scores are recalculated.
- Output is deterministic.
- Empty/missing data is handled safely.
- Markdown and JSON rollups are covered by tests.
- No canonical artifacts are mutated.
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

