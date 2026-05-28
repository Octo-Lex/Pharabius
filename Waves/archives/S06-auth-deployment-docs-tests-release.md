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


# S06 — Auth, Deployment Docs, Tests, Release

Risk: High  
Slice type: Platform finalization / deployment / release  
Artifact impact: Authentication, deployment documentation, release metadata

## Scope

Finalize v2.2 hosted platform MVP with basic authentication, deployment documentation, test coverage, release notes, and version metadata.

This slice should not add new product capability beyond completing the hosted platform MVP.

## Goals

- Add basic authentication suitable for MVP.
- Protect hosted UI and APIs.
- Add deployment documentation.
- Add local development documentation.
- Add security boundary documentation.
- Add platform smoke tests.
- Update changelog and roadmap.
- Bump version to `2.2.0`.
- Confirm all gates pass.
- Confirm platform can run locally with Docker Compose.
- Confirm CLI remains usable independently.

## Patch Set

Expected files/modules:

```text
src/pharabius_platform/auth.py
src/pharabius_platform/api/auth.py
src/pharabius_platform/settings.py
platform/README.md
docs/HOSTED_PLATFORM.md
docs/HOSTED_SECURITY_BOUNDARY.md
docs/DEPLOYMENT.md
CHANGELOG.md
docs/ROADMAP.md
KNOWN_LIMITATIONS.md
tests/platform/test_auth.py
tests/platform/test_platform_smoke.py
```

Recommended MVP auth options:

| Option | Recommendation |
|---|---|
| Email/password local auth | Acceptable for MVP if hashed securely |
| Single admin bootstrap token | Acceptable for dev/self-hosted MVP |
| GitHub OAuth | Useful, but can expand scope |
| SSO/SAML | Out of scope |
| Complex RBAC | Out of scope |

Recommended security requirements:

```text
password hashing if passwords exist
secure token generation
upload token hashing
auth required for dashboards/APIs
CORS configured intentionally
file upload limits documented
no source-code storage by default
```

Recommended deployment docs:

```text
Docker Compose local
environment variables
database setup
storage path
backup considerations
upload size limits
security boundary
known limitations
```

## Tests

Add tests for:

- Unauthenticated dashboard/API request rejected.
- Authenticated request succeeds.
- Upload token auth works separately from user auth.
- Password or admin token handling is secure enough for MVP.
- Docker Compose config validates.
- Platform smoke test passes.
- CLI import still does not require platform dependencies if designed that way.
- Version is `2.2.0`.
- Build artifact is correct.

## Targeted Verification

```bash
pytest tests/platform/test_auth.py
pytest tests/platform/test_platform_smoke.py
docker compose -f platform/docker-compose.yml config
python -m build
python scripts/validate_release_consistency.py
python scripts/validate_packaging.py
```

## Expected Behavior

v2.2.0 can be released as a hosted platform foundation with read-only artifact intelligence, CI ingestion, basic auth, and documented deployment path.

## Acceptance Criteria

- Version is `2.2.0`.
- Hosted app requires auth.
- CI upload tokens work and are scoped.
- Docker Compose config validates.
- Deployment docs exist.
- Security boundary docs exist.
- Existing CLI remains functional.
- All unit, integration, platform, build, and release checks pass.
- No external writes are introduced.
- No remediation is introduced.
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
