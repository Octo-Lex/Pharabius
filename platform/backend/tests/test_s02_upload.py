"""S02 tests — upload, storage, validation, parsing."""

from __future__ import annotations

import hashlib
import io
import json
import os
import tarfile
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from pharabius_platform.main import app


def _create_sample_ai_debt(base: Path) -> Path:
    """Create a minimal .ai-debt directory for testing."""
    ai_debt = base / ".ai-debt"
    ai_debt.mkdir()

    # evidence.json
    (ai_debt / "evidence.json").write_text(
        json.dumps({"schema_version": "1.0", "evidence": []}), encoding="utf-8"
    )

    # debt-register.json
    (ai_debt / "debt-register.json").write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "project_name": "test-project",
                "findings": [
                    {
                        "id": "TD-DEP-001",
                        "category": "TD-DEP",
                        "issue_type": "technical_debt",
                        "title": "Test finding",
                        "description": "Test description",
                        "severity": "Medium",
                        "confidence": "Medium",
                        "locations": ["src/main.py"],
                        "evidence_ids": ["EVD-001"],
                        "technical_impact": "Low",
                        "business_impact": "Low",
                        "risk_score": 15,
                        "priority": "Medium",
                        "recommended_action": "Fix it",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    # project-profile.json
    (ai_debt / "project-profile.json").write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "project_name": "test-project",
                "repository_root": "/test",
            }
        ),
        encoding="utf-8",
    )

    return ai_debt


def _create_tarball(ai_debt_dir: Path) -> bytes:
    """Create a tar.gz from an .ai-debt directory."""
    buf = io.BytesIO()
    parent = ai_debt_dir.parent
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        tar.add(str(ai_debt_dir), arcname=".ai-debt")
    return buf.getvalue()


@pytest.fixture
def admin_token() -> str:
    token = "test_admin_s02"
    os.environ["ADMIN_TOKEN"] = token
    yield token
    os.environ.pop("ADMIN_TOKEN", "")


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def sample_tarball(tmp_path: Path) -> bytes:
    ai_debt = _create_sample_ai_debt(tmp_path)
    return _create_tarball(ai_debt)


class TestUploadSuccess:
    async def test_upload_valid_bundle(
        self, client: AsyncClient, admin_token: str, sample_tarball: bytes
    ) -> None:
        response = await client.post(
            "/api/v1/bundles",
            headers={"Authorization": f"Bearer {admin_token}"},
            files={"file": ("bundle.tar.gz", sample_tarball, "application/gzip")},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["is_valid"] is True
        assert "bundle_id" in data
        assert "content_hash" in data
        assert data["file_size_bytes"] > 0
        assert data["parser_version"] == "2.2.0"

    async def test_upload_returns_content_hash(
        self, client: AsyncClient, admin_token: str, sample_tarball: bytes
    ) -> None:
        expected_hash = hashlib.sha256(sample_tarball).hexdigest()
        response = await client.post(
            "/api/v1/bundles",
            headers={"Authorization": f"Bearer {admin_token}"},
            files={"file": ("bundle.tar.gz", sample_tarball, "application/gzip")},
        )
        assert response.json()["content_hash"] == expected_hash


class TestUploadValidation:
    async def test_upload_missing_artifacts(
        self, client: AsyncClient, admin_token: str, tmp_path: Path
    ) -> None:
        # Create bundle with only evidence.json (missing debt-register, profile)
        ai_debt = tmp_path / ".ai-debt"
        ai_debt.mkdir()
        (ai_debt / "evidence.json").write_text(
            json.dumps({"schema_version": "1.0", "evidence": []}), encoding="utf-8"
        )
        tarball = _create_tarball(ai_debt)

        response = await client.post(
            "/api/v1/bundles",
            headers={"Authorization": f"Bearer {admin_token}"},
            files={"file": ("bundle.tar.gz", tarball, "application/gzip")},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["is_valid"] is False
        assert "debt-register.json" in data["validation"]["missing_required"]


class TestUploadSecurity:
    async def test_upload_oversized_rejected(self, client: AsyncClient, admin_token: str) -> None:
        # Create a large fake tarball
        large_data = b"x" * (51 * 1024 * 1024)  # 51 MB
        response = await client.post(
            "/api/v1/bundles",
            headers={"Authorization": f"Bearer {admin_token}"},
            files={"file": ("big.tar.gz", large_data, "application/gzip")},
        )
        assert response.status_code == 413

    async def test_upload_no_token_rejected(
        self, client: AsyncClient, sample_tarball: bytes
    ) -> None:
        response = await client.post(
            "/api/v1/bundles",
            files={"file": ("bundle.tar.gz", sample_tarball, "application/gzip")},
        )
        assert response.status_code == 401

    async def test_upload_wrong_token_rejected(
        self, client: AsyncClient, admin_token: str, sample_tarball: bytes
    ) -> None:
        response = await client.post(
            "/api/v1/bundles",
            headers={"Authorization": "Bearer wrong_token"},
            files={"file": ("bundle.tar.gz", sample_tarball, "application/gzip")},
        )
        assert response.status_code == 401


class TestStorage:
    def test_store_bundle_creates_file(self, tmp_path: Path) -> None:
        from pharabius_platform.services.storage import store_bundle

        os.environ["STORAGE_PATH"] = str(tmp_path / "storage")
        data = b"test bundle content"
        sha256, path = store_bundle(data)
        assert Path(path).exists()
        assert sha256 == hashlib.sha256(data).hexdigest()
        os.environ.pop("STORAGE_PATH", "")

    def test_store_bundle_dedup(self, tmp_path: Path) -> None:
        from pharabius_platform.services.storage import store_bundle

        os.environ["STORAGE_PATH"] = str(tmp_path / "storage")
        data = b"dedup test content"
        sha1, path1 = store_bundle(data)
        sha2, path2 = store_bundle(data)
        assert sha1 == sha2
        assert path1 == path2
        os.environ.pop("STORAGE_PATH", "")


class TestValidator:
    def test_valid_bundle(self, tmp_path: Path) -> None:
        from pharabius_platform.services.validator import validate_bundle

        ai_debt = _create_sample_ai_debt(tmp_path)
        result = validate_bundle(tmp_path)
        assert result.is_valid is True
        assert len(result.found_required) == 3

    def test_invalid_bundle_missing_files(self, tmp_path: Path) -> None:
        from pharabius_platform.services.validator import validate_bundle

        ai_debt = tmp_path / ".ai-debt"
        ai_debt.mkdir()
        (ai_debt / "evidence.json").write_text("{}", encoding="utf-8")
        result = validate_bundle(tmp_path)
        assert result.is_valid is False

    def test_no_ai_debt_dir(self, tmp_path: Path) -> None:
        from pharabius_platform.services.validator import validate_bundle

        result = validate_bundle(tmp_path)
        assert result.is_valid is False


class TestParser:
    def test_parse_bundle_extracts_findings(self, tmp_path: Path) -> None:
        from pharabius_platform.services.parser import parse_bundle

        _create_sample_ai_debt(tmp_path)
        ai_debt_dir = tmp_path / ".ai-debt"
        parsed = parse_bundle(ai_debt_dir)
        assert parsed.debt_register is not None
        assert len(parsed.debt_register.findings) == 1
        assert parsed.debt_register.findings[0].id == "TD-DEP-001"
        assert parsed.profile is not None
        assert parsed.profile.project_name == "test-project"

    def test_parse_bundle_no_errors(self, tmp_path: Path) -> None:
        from pharabius_platform.services.parser import parse_bundle

        ai_debt_dir = tmp_path / ".ai-debt"
        _create_sample_ai_debt(tmp_path)
        parsed = parse_bundle(ai_debt_dir)
        assert len(parsed.parse_errors) == 0


class TestCLIUploader:
    def test_create_tarball(self, tmp_path: Path) -> None:
        from pharabius.core.uploader import create_bundle_tarball

        ai_debt = _create_sample_ai_debt(tmp_path)
        data, sha256 = create_bundle_tarball(ai_debt)
        assert len(data) > 0
        assert len(sha256) == 64

        # Verify tarball is valid
        buf = io.BytesIO(data)
        with tarfile.open(fileobj=buf, mode="r:gz") as tar:
            names = tar.getnames()
        assert any(".ai-debt" in n for n in names)
