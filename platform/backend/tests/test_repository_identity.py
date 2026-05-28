"""S01 tests — Repository identity and upload UX fixes (v2.2.4)."""

from __future__ import annotations

import hashlib
import io
import json
import tarfile
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient

from pharabius_platform.main import app


def _make_tar_gz(files: dict[str, str]) -> bytes:
    """Create a tar.gz in-memory from {filename: content} pairs."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for name, content in files.items():
            data = content.encode("utf-8")
            info = tarfile.TarInfo(name=name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


EVIDENCE_JSON = json.dumps({"schema_version": "1.0", "evidence": []})
DEBT_REGISTER_JSON = json.dumps(
    {
        "schema_version": "1.0",
        "project_name": "profile-project",
        "findings": [
            {
                "id": "TD-DEP-001",
                "category": "TD-DEP",
                "issue_type": "technical_debt",
                "title": "Test finding",
                "description": "Test",
                "severity": "Medium",
                "confidence": "High",
                "locations": ["package.json"],
                "evidence_ids": ["EVD-001"],
                "technical_impact": "Low",
                "business_impact": "Low",
                "risk_score": 15,
                "priority": "Medium",
                "recommended_action": "Fix",
            }
        ],
    }
)
PROFILE_JSON = json.dumps(
    {
        "schema_version": "1.0",
        "project_name": "profile-project",
        "repository_root": "/tmp/test",
    }
)

ADMIN_TOKEN = "test_admin_token_v224"


@pytest.fixture(autouse=True)
async def _setup_db(monkeypatch: pytest.MonkeyPatch) -> AsyncGenerator[None, None]:
    """Create tables before each test, drop after."""
    monkeypatch.setenv("ADMIN_TOKEN", ADMIN_TOKEN)
    monkeypatch.setenv(
        "DATABASE_URL",
        "sqlite+aiosqlite:///file::memory:?cache=shared&uri=true",
    )

    from pharabius_platform import db as db_mod
    from pharabius_platform.db import init_db
    from pharabius_platform.models import Base

    db_url = "sqlite+aiosqlite:///file::memory:?cache=shared&uri=true"
    init_db(db_url)

    assert db_mod._engine is not None
    async with db_mod._engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    async with db_mod._engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client() -> AsyncClient:
    """Provide an async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def _upload(client: AsyncClient, files: dict[str, str], repo_name: str = "") -> dict:
    """Helper: upload a bundle and return parsed JSON."""
    tar_data = _make_tar_gz(files)
    content_hash = hashlib.sha256(tar_data).hexdigest()

    form_files = {"file": ("bundle.tar.gz", tar_data, "application/gzip")}
    data = {}
    if repo_name:
        data["repository_name"] = repo_name

    resp = await client.post(
        "/api/v1/bundles",
        files=form_files,
        data=data,
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
    )
    return resp.json(), resp.status_code, content_hash


class TestRepositoryNameFromFormField:
    """repository_name Form field takes priority."""

    async def test_explicit_name_stored(self, client: AsyncClient) -> None:
        files = {
            ".ai-debt/evidence.json": EVIDENCE_JSON,
            ".ai-debt/debt-register.json": DEBT_REGISTER_JSON,
            ".ai-debt/project-profile.json": PROFILE_JSON,
        }
        body, status_code, _ = await _upload(client, files, repo_name="my-custom-repo")
        assert status_code == 201, f"Expected 201, got {status_code}: {body}"

        # Check repository name via list endpoint
        resp = await client.get("/api/v1/repositories")
        data = resp.json()
        assert data["total"] == 1
        repo = data["repositories"][0]
        assert repo["name"] == "my-custom-repo"
        assert repo["slug"] == "my-custom-repo"

    async def test_name_with_spaces_slugified(self, client: AsyncClient) -> None:
        files = {
            ".ai-debt/evidence.json": EVIDENCE_JSON,
            ".ai-debt/debt-register.json": DEBT_REGISTER_JSON,
            ".ai-debt/project-profile.json": PROFILE_JSON,
        }
        body, status_code, _ = await _upload(client, files, repo_name="My Cool Project")
        assert status_code == 201, f"Expected 201, got {status_code}: {body}"

        resp = await client.get("/api/v1/repositories")
        data = resp.json()
        repo = data["repositories"][0]
        assert repo["name"] == "My Cool Project"
        assert repo["slug"] == "my-cool-project"


class TestRepositoryNameFromProfile:
    """When no repository_name provided, use project-profile.json project_name."""

    async def test_profile_name_used_as_fallback(self, client: AsyncClient) -> None:
        files = {
            ".ai-debt/evidence.json": EVIDENCE_JSON,
            ".ai-debt/debt-register.json": DEBT_REGISTER_JSON,
            ".ai-debt/project-profile.json": PROFILE_JSON,
        }
        body, status_code, _ = await _upload(client, files, repo_name="")
        assert status_code == 201, f"Expected 201, got {status_code}: {body}"

        resp = await client.get("/api/v1/repositories")
        data = resp.json()
        repo = data["repositories"][0]
        assert repo["name"] == "profile-project"
        assert repo["slug"] == "profile-project"


class TestRepositoryNameHashFallback:
    """When no name available, use 'Unknown repository · <hash>' pattern."""

    async def test_hash_fallback(self, client: AsyncClient) -> None:
        # No project-profile.json, no repository_name
        files = {
            ".ai-debt/evidence.json": EVIDENCE_JSON,
            ".ai-debt/debt-register.json": DEBT_REGISTER_JSON,
        }
        body, status_code, content_hash = await _upload(client, files, repo_name="")
        assert status_code == 201, f"Expected 201, got {status_code}: {body}"

        resp = await client.get("/api/v1/repositories")
        data = resp.json()
        repo = data["repositories"][0]
        assert content_hash[:12] in repo["name"]
        assert "Unknown" in repo["name"] or content_hash[:12] in repo["slug"]


class TestDuplicateUpload:
    """Duplicate bundle returns 409 with clear message."""

    async def test_duplicate_returns_409(self, client: AsyncClient) -> None:
        files = {
            ".ai-debt/evidence.json": EVIDENCE_JSON,
            ".ai-debt/debt-register.json": DEBT_REGISTER_JSON,
            ".ai-debt/project-profile.json": PROFILE_JSON,
        }
        _body1, status1, _ = await _upload(client, files, repo_name="dup-test")
        assert status1 == 201

        _body2, status2, _ = await _upload(client, files, repo_name="dup-test")
        assert status2 == 409
        assert "already" in str(_body2).lower()


class TestSlugStability:
    """Slug is stable and safe."""

    async def test_special_characters_slugified(self, client: AsyncClient) -> None:
        files = {
            ".ai-debt/evidence.json": EVIDENCE_JSON,
            ".ai-debt/debt-register.json": DEBT_REGISTER_JSON,
            ".ai-debt/project-profile.json": PROFILE_JSON,
        }
        body, status_code, _ = await _upload(client, files, repo_name="My Project! @2024")
        assert status_code == 201, f"Expected 201, got {status_code}: {body}"

        resp = await client.get("/api/v1/repositories")
        data = resp.json()
        repo = data["repositories"][0]
        assert repo["slug"] == "my-project-2024"
        # Name keeps original characters
        assert repo["name"] == "My Project! @2024"

    async def test_same_name_reuses_repo(self, client: AsyncClient) -> None:
        """Uploading different bundles with same repo name reuses the repository."""
        files1 = {
            ".ai-debt/evidence.json": EVIDENCE_JSON,
            ".ai-debt/debt-register.json": DEBT_REGISTER_JSON,
            ".ai-debt/project-profile.json": PROFILE_JSON,
        }
        _body1, status1, _ = await _upload(client, files1, repo_name="shared-repo")
        assert status1 == 201

        # Different findings to make a different content hash
        reg2 = json.loads(DEBT_REGISTER_JSON)
        reg2["findings"] = []
        files2 = {
            ".ai-debt/evidence.json": EVIDENCE_JSON,
            ".ai-debt/debt-register.json": json.dumps(reg2),
            ".ai-debt/project-profile.json": PROFILE_JSON,
        }
        _body2, status2, _ = await _upload(client, files2, repo_name="shared-repo")
        assert status2 == 201

        resp = await client.get("/api/v1/repositories")
        data = resp.json()
        # Should be 1 repo, not 2
        assert data["total"] == 1
        assert data["repositories"][0]["slug"] == "shared-repo"


class TestSlugifyUnit:
    """Unit tests for _slugify helper."""

    def test_simple_name(self) -> None:
        from pharabius_platform.api.upload import _slugify

        assert _slugify("my-repo") == "my-repo"

    def test_spaces_become_hyphens(self) -> None:
        from pharabius_platform.api.upload import _slugify

        assert _slugify("My Cool Project") == "my-cool-project"

    def test_special_chars_removed(self) -> None:
        from pharabius_platform.api.upload import _slugify

        assert _slugify("Project @2024!") == "project-2024"

    def test_consecutive_hyphens_collapsed(self) -> None:
        from pharabius_platform.api.upload import _slugify

        assert _slugify("a---b") == "a-b"

    def test_leading_trailing_hyphens_stripped(self) -> None:
        from pharabius_platform.api.upload import _slugify

        assert _slugify("--my-repo--") == "my-repo"

    def test_empty_returns_unnamed(self) -> None:
        from pharabius_platform.api.upload import _slugify

        assert _slugify("") == "unnamed-repo"

    def test_only_special_chars_returns_unnamed(self) -> None:
        from pharabius_platform.api.upload import _slugify

        assert _slugify("@#$%") == "unnamed-repo"
