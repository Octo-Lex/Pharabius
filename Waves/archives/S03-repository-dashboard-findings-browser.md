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


# S03 — Repository Dashboard and Findings Browser

Risk: Medium-high  
Slice type: Hosted UI / repository drilldown  
Artifact impact: Read-only UI and API endpoints

## Scope

Build the first repository-level dashboard and findings browser over normalized artifact records.

This slice should focus on read-only visibility. It should not add review state, policy mutation, ticket writes, or external integrations.

## Goals

- Add repository dashboard API.
- Add repository dashboard UI.
- Show latest run summary.
- Show priority counts.
- Show latest quality gate status.
- Show trend trajectory if available.
- Show blocking gaps count if available.
- Show readiness status if available.
- Add findings browser.
- Support filtering by priority/category/status.
- Support finding detail view with evidence references where available.

## Patch Set

Expected files/directories:

```text
src/pharabius_platform/api/repositories.py
src/pharabius_platform/api/findings.py
src/pharabius_platform/services/repository_dashboard.py
src/pharabius_platform/frontend/              # if bundled frontend
  repository-dashboard.*
  findings-browser.*

tests/platform/test_repository_dashboard_api.py
tests/platform/test_findings_browser_api.py
tests/platform/test_repository_dashboard_rendering.py
```

If using a separate frontend app:

```text
web/
  package.json
  src/
    pages/
    components/
    api/
```

Recommended repository dashboard fields:

```json
{
  "repository_id": "",
  "name": "",
  "latest_run": {},
  "priority_counts": {
    "critical": 0,
    "high": 0,
    "medium": 0,
    "low": 0
  },
  "quality_gate": "pass | warn | fail | unknown",
  "trajectory": "improving | stable | worsening | insufficient_data | unknown",
  "readiness": "ready | partial | needs_review | unknown",
  "blocking_gaps": 0,
  "top_categories": []
}
```

Recommended findings browser filters:

```text
priority
category
claim status
has blocking gap
quality gate relevance
text search
```

## Tests

Add tests for:

- Repository dashboard API returns latest summary.
- Repository with no runs renders empty state.
- Repository with findings renders priority counts.
- Findings filter by priority.
- Findings filter by category.
- Finding detail includes evidence references.
- Missing evidence does not crash UI/API.
- UI or rendering snapshot includes expected headings.
- API responses are stable.

## Targeted Verification

```bash
pytest tests/platform/test_repository_dashboard_api.py
pytest tests/platform/test_findings_browser_api.py
pytest tests/platform/test_repository_dashboard_rendering.py
```

If frontend exists:

```bash
cd web && npm test
cd web && npm run build
```

## Expected Behavior

Users can open the hosted platform, select a repository, and understand its latest Pharabius state.

## Acceptance Criteria

- Repository dashboard exists.
- Findings browser exists.
- UI/API are read-only.
- Empty states are handled cleanly.
- Filters work.
- No review workflow is added yet.
- No policy engine is added.
- No external writes are added.
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
