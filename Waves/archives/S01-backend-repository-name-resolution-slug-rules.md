# v2.2.4 — Repository Identity & Upload UX Patch

Goal: Fix repository identity handling so uploaded bundles produce human-readable repository names across backend persistence, frontend display, and `ai-debt upload`.

Release posture: focused patch release. This release should fix the hash-named repository usability problem without adding new product capability.

Core boundaries:
- No OAuth
- No RBAC
- No API key management UI
- No claims/gaps/readiness UI
- No policy engine
- No tracker writes
- No PR comments
- No repository cloning
- No remediation
- No source-code modification


# S01 — Backend Repository-Name Resolution and Slug Rules

Risk: Medium  
Slice type: backend data correctness patch  
Artifact impact: repository persistence and display identity

## Scope

Fix backend repository identity resolution so uploaded bundles create or associate with human-readable repositories whenever a name is available.

## Goals

- Add deterministic repository-name resolution helper.
- Prefer explicit upload `repository_name`.
- Use artifact-derived name when explicit name is absent.
- Preserve content-hash fallback only as last resort.
- Generate stable safe slugs from repository names.
- Ensure duplicate uploads to the same named repository associate correctly.
- Avoid creating random hash-named repositories when a name is provided.

## Patch Set

Expected files:

```text
platform/backend/src/pharabius_platform/services/repository_identity.py
platform/backend/src/pharabius_platform/services/parser.py
platform/backend/src/pharabius_platform/services/storage.py
platform/backend/src/pharabius_platform/api/upload.py
platform/backend/tests/test_repository_identity.py
platform/backend/tests/test_upload_repository_identity.py
```

Recommended helper:

```python
def resolve_repository_identity(
    *,
    explicit_name: str | None,
    artifact_metadata: dict[str, Any] | None,
    cli_directory_name: str | None,
    content_hash: str,
) -> RepositoryIdentity:
    ...
```

Recommended model:

```python
class RepositoryIdentity(BaseModel):
    name: str
    slug: str
    source: Literal[
        "explicit",
        "artifact",
        "git_remote",
        "cli_directory",
        "content_hash",
    ]
    is_fallback: bool = False
```

## Slug rules

```text
- lowercase
- trim whitespace
- replace spaces/underscores with hyphens
- remove unsafe characters
- collapse repeated hyphens
- max length 80
- if empty, use hash fallback
```

Examples:

| Input | Slug |
|---|---|
| `Pharabius` | `pharabius` |
| `My Service API` | `my-service-api` |
| `validation_java` | `validation-java` |
| `../bad name` | `bad-name` |

## Tests

Add tests for:

- Explicit name wins over hash.
- Explicit name wins over artifact metadata.
- Artifact-derived name used when explicit missing.
- CLI directory name used when artifact missing.
- Hash fallback used only when no names exist.
- Slug generation is deterministic and safe.
- Duplicate uploads with same repository name associate with same repository.
- Different repositories with same slug collision are handled deterministically.

## Expected Behavior

Uploading with `repository_name=Pharabius` creates/displays:

```text
Repository.name = "Pharabius"
Repository.slug = "pharabius"
```

not:

```text
Repository.name = "6bcbe18c41c2"
```

## Acceptance Criteria

- Repository-name resolution helper exists.
- Hash fallback remains but is last resort.
- Tests cover all identity sources.
- Duplicate named uploads associate predictably.
- No new auth/integration functionality is added.

## Guardrails

- Keep this patch narrow.
- Do not change the hosted platform’s persistence model beyond repository identity resolution.
- Do not add external writes.
- Do not add authentication UI, OAuth, RBAC, policy engine, tracker writes, or remediation.
- Preserve the content-hash fallback only as a last resort.
- Preserve duplicate bundle handling.
- Keep source-derived artifact warnings intact.


## Verification Commands

Run:

```bash
ruff format --check .
ruff check .
mypy src
lint-imports
pytest
pytest platform/backend/tests
npm --prefix platform/frontend run build
python -m build
python scripts/validate_repo.py .
```

Optional runtime check:

```bash
platform/scripts/smoke_docker_compose.sh
```
