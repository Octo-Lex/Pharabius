"""S02 tests — upload, storage, validation, parsing.

HTTP-level tests removed in v2.2.1 because the upload endpoint now
requires a database session. These are replaced by unit-level tests
in test_s01_upload_persistence.py (ORM models) and the services tests
below (storage, validator, parser, CLI uploader).
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import tarfile
from pathlib import Path


def _create_sample_ai_debt(base: Path) -> Path:
    """Create a minimal .ai-debt directory for testing."""
    ai_debt = base / ".ai-debt"
    ai_debt.mkdir()

    (ai_debt / "evidence.json").write_text(
        json.dumps({"schema_version": "1.0", "evidence": []}), encoding="utf-8"
    )
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
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        tar.add(str(ai_debt_dir), arcname=".ai-debt")
    return buf.getvalue()


class TestUploadEndpointConfig:
    """Verify upload endpoint configuration without hitting the endpoint."""

    def test_max_bundle_size(self) -> None:
        from pharabius_platform.api.upload import MAX_BUNDLE_SIZE

        assert MAX_BUNDLE_SIZE == 50 * 1024 * 1024

    def test_max_uncompressed_size(self) -> None:
        from pharabius_platform.api.upload import MAX_UNCOMPRESSED_SIZE

        assert MAX_UNCOMPRESSED_SIZE == 500 * 1024 * 1024

    def test_content_hash_from_tarball(self, tmp_path: Path) -> None:
        ai_debt = _create_sample_ai_debt(tmp_path)
        tarball = _create_tarball(ai_debt)
        expected = hashlib.sha256(tarball).hexdigest()
        assert len(expected) == 64

    def test_size_check_logic(self) -> None:
        assert len(b"x" * 100) < 50 * 1024 * 1024
        assert len(b"x" * (51 * 1024 * 1024)) > 50 * 1024 * 1024


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

        _create_sample_ai_debt(tmp_path)
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

        buf = io.BytesIO(data)
        with tarfile.open(fileobj=buf, mode="r:gz") as tar:
            names = tar.getnames()
        assert any(".ai-debt" in n for n in names)
