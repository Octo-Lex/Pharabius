# Wave 45 — v1.8.0 Portfolio Summary Foundation

Goal: Add repository-local portfolio summary artifacts that consolidate one or more Pharabius runs into a lightweight portfolio view, without adding a server, dashboard, scheduler, database, remote repository crawler, or external integration.

Release target: `v1.8.0`  
Branch target: `roadmap/v1.8.0-portfolio-summary`  
Boundary: File-based, repository-local or workspace-local portfolio summaries only.

# W45-S02 — Aggregate Repository Summaries from `.ai-debt/` Outputs

Risk: Medium  
Slice type: Aggregation logic  
Artifact impact: New portfolio sidecar artifacts only

## Scope

Implement repository summary extraction from one or more existing `.ai-debt/` directories. This slice reads existing Pharabius output files and builds normalized portfolio repository entries.

This slice should not introduce a CLI command yet unless minimal internal plumbing is necessary for tests.

## Goals

- Read repository-level data from `.ai-debt/debt-register.json`.
- Optionally detect `.ai-debt/ticket-drafts/`.
- Optionally detect `.ai-debt/export-bundles/manifest.json`.
- Detect validation/report artifacts when present.
- Handle missing or malformed artifacts gracefully.
- Produce deterministic repository entries.
- Support aggregation from a list of local paths.

## Patch Set

Expected files/modules:

```text
src/pharabius/core/portfolio.py
src/pharabius/schemas/portfolio.py
tests/test_portfolio_aggregation.py
tests/fixtures/portfolio/                 # local fixture outputs
```

Recommended extraction inputs:

| Artifact | Use |
|---|---|
| `.ai-debt/debt-register.json` | project, branch, commit, findings, priority/category counts |
| `.ai-debt/ticket-drafts/ticket-drafts.json` | ticket draft availability |
| `.ai-debt/export-bundles/manifest.json` | export bundle availability |
| `.ai-debt/reports/export-bundle-summary.md` | export readiness signal if simple to detect |
| `.ai-debt/reports/scoring-delta.md` | optional enhanced scoring signal |

Recommended fallback behavior:

| Scenario | Behavior |
|---|---|
| Missing `.ai-debt/` | repository entry skipped or warning emitted |
| Missing debt register | repository entry marked `needs_review` |
| Malformed debt register | warning emitted, no crash |
| Empty findings | repository included with zero counts |
| Missing ticket/export artifacts | flags set false |
| Duplicate repository paths | deterministic deduplication or warning |

## Tests

Add tests for:

- Single repository aggregation.
- Multiple repository aggregation.
- Missing `.ai-debt/` path warning.
- Missing `debt-register.json` warning.
- Malformed debt register graceful handling.
- Empty debt register included with zero counts.
- Ticket draft detection.
- Export bundle detection.
- Deterministic ordering by repository ID/path.
- No mutation of input artifacts.

## Targeted Verification

```bash
pytest tests/test_portfolio_aggregation.py
```

## Expected Behavior

Given local repository paths, Pharabius can produce normalized repository entries without changing the source repositories.

Conceptual function:

```python
entries = collect_portfolio_repository_entries([
    Path("/repos/service-a"),
    Path("/repos/service-b"),
])
```

## Acceptance Criteria

- Aggregation logic reads existing `.ai-debt/` outputs.
- Missing/malformed data is handled with warnings.
- Repository entries are deterministic.
- Input artifacts are not modified.
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

