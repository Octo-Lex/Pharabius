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


## Pack contents

| Slice | Title | Risk | File |
|---|---|---|---|
| S01 | Platform scaffold: FastAPI, database, Docker Compose, base data model | High | `S01-platform-scaffold-fastapi-db-docker-model.md` |
| S02 | Artifact upload API, validation, and parsing pipeline | High | `S02-artifact-upload-validation-parsing.md` |
| S03 | Repository dashboard and findings browser | Medium-high | `S03-repository-dashboard-findings-browser.md` |
| S04 | Portfolio dashboard, trend views, and gate history | Medium-high | `S04-portfolio-dashboard-trend-gate-history.md` |
| S05 | Claims/gaps/readiness views and CI upload token flow | High | `S05-claims-gaps-readiness-ci-upload-token.md` |
| S06 | Auth, deployment docs, tests, release | High | `S06-auth-deployment-docs-tests-release.md` |

## v2.2 MVP decision

v2.2 is not a full SaaS platform. It is a hosted artifact intelligence foundation.

Allowed:

```text
manual .ai-debt bundle upload
CI upload using scoped upload token
artifact contract validation
normalized records in database
repository dashboard
portfolio dashboard
findings/trends/claims/gaps/readiness views
basic authentication
Docker Compose local deployment
```

Not allowed:

```text
source-code upload requirement
repository cloning
GitHub App
GitLab App
tracker writes
PR comments
issue creation
SARIF upload by default
remediation
complex RBAC
billing
multi-region infrastructure
background worker unless required
```

## Recommended release headline

```text
Pharabius v2.2.0 introduces the hosted platform foundation with artifact-bundle ingestion, CI upload, repository dashboards, portfolio visibility, and read-only claims/gaps/trend inspection.
```
