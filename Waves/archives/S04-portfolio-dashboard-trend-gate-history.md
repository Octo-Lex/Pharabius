# v2.2 — Hosted Platform Foundation + CI Ingestion

Goal: Build the first hosted Pharabius platform for artifact ingestion, repository/portfolio visibility, trend review, claims/gaps inspection, and CI upload — without source-code storage, repository cloning, tracker writes, PR comments, issue creation, or remediation.

Release target: `v2.2.0`  
Branch target: `roadmap/v2.2.0-hosted-platform-foundation`  
Posture: Large release, category change, strict MVP boundary.

Primary product loop:

```text
Run Pharabius locally or in CI
→ generate .ai-debt artifacts
→ upload artifact bundle
→ validate artifact contract
→ parse normalized records
→ view repository dashboard
→ view portfolio dashboard
→ inspect findings, trends, claims, gaps, gates, and readiness
```


# S04 — Portfolio Dashboard, Trend Views, and Gate History

Risk: Medium-high  
Slice type: Hosted portfolio visibility / trend UI  
Artifact impact: Read-only UI and API endpoints

## Scope

Build portfolio-level and historical views that aggregate uploaded repositories and their artifact-derived run histories.

This slice makes the hosted platform useful to engineering managers and platform teams.

## Goals

- Add organization or project portfolio dashboard.
- Show repository list with risk/readiness/gate status.
- Show portfolio priority rollups.
- Show repositories with failing gates.
- Show repositories with blocking gaps.
- Show trend trajectory per repository.
- Show gate history per repository.
- Show risk movement from stored trend artifacts or run summaries.
- Preserve insufficient-data honesty.

## Patch Set

Expected files/modules:

```text
src/pharabius_platform/api/portfolio.py
src/pharabius_platform/api/trends.py
src/pharabius_platform/services/portfolio_summary.py
src/pharabius_platform/services/gate_history.py
src/pharabius_platform/services/trend_views.py
tests/platform/test_portfolio_dashboard_api.py
tests/platform/test_gate_history_api.py
tests/platform/test_trend_views_api.py
```

Frontend:

```text
portfolio-dashboard
trend-view
gate-history-view
```

Recommended portfolio metrics:

```text
repository_count
repositories_by_gate_result
repositories_by_readiness
total_critical
total_high
total_blocking_gaps
top_categories_when_available
trend_trajectory_counts
latest_upload_time
```

Recommended gate history fields:

```json
{
  "repository_id": "",
  "runs": [
    {
      "run_id": "",
      "timestamp": "",
      "gate_result": "pass | warn | fail | unknown",
      "critical": 0,
      "high": 0,
      "blocking_gaps": 0
    }
  ]
}
```

## Tests

Add tests for:

- Portfolio dashboard aggregates multiple repositories.
- Empty portfolio renders cleanly.
- Repositories with failing gates are counted.
- Repositories with blocking gaps are counted.
- Gate history sorts by timestamp.
- Trend view handles insufficient data.
- Category rollups are shown only when available.
- API response ordering is deterministic.

## Targeted Verification

```bash
pytest tests/platform/test_portfolio_dashboard_api.py
pytest tests/platform/test_gate_history_api.py
pytest tests/platform/test_trend_views_api.py
```

If frontend exists:

```bash
cd web && npm test
cd web && npm run build
```

## Expected Behavior

Managers and platform teams can see cross-repository debt posture and gate history from uploaded artifact bundles.

## Acceptance Criteria

- Portfolio dashboard exists.
- Trend view exists.
- Gate history view exists.
- Insufficient data is explicitly shown.
- No trend dimensions are fabricated.
- No external APIs are called.
- No source-code data is required.
- All tests pass.
## Guardrails

- Do not require source-code upload.
- Do not clone repositories.
- Do not store full source files by default.
- Do not create issues, PR comments, tracker items, or external writes.
- Do not call Jira, Linear, GitHub Issues, Azure DevOps, GitHub, GitLab, or other external write APIs.
- Do not upload SARIF to code scanning by default.
- Do not perform autonomous remediation.
- Do not generate patches.
- Do not modify production code.
- Treat uploaded `.ai-debt` bundles as analysis artifacts, not as implementation authority.
- Keep v2.2 hosted behavior read-only with respect to source systems.


## Verification Commands

Minimum local verification:

```bash
ruff format --check .
ruff check .
mypy src
lint-imports
pytest
python -m build
python scripts/validate_repo.py .
```

Hosted-platform verification should additionally include the new platform checks introduced in this release, such as API tests, database migration checks, frontend checks, and Docker Compose smoke tests.
