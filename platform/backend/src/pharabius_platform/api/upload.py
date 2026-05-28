"""Artifact bundle upload endpoint."""

from __future__ import annotations

import hashlib
import tarfile
import tempfile
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status

from pharabius_platform.middleware.auth import require_token
from pharabius_platform.services.parser import parse_bundle
from pharabius_platform.services.storage import store_bundle
from pharabius_platform.services.validator import validate_bundle

router = APIRouter(tags=["bundles"])

MAX_BUNDLE_SIZE = 50 * 1024 * 1024  # 50 MB
MAX_UNCOMPRESSED_SIZE = 500 * 1024 * 1024  # 500 MB


@router.post("/api/v1/bundles", status_code=status.HTTP_201_CREATED)
async def upload_bundle(
    file: UploadFile,
    repository_name: str = "",
    token: str = Depends(require_token),
) -> dict[str, object]:
    """Upload and process an .ai-debt artifact bundle.

    Accepts a tar.gz archive containing a .ai-debt directory.
    Validates the artifact contract, stores the bundle by content hash,
    and parses normalized records.
    """
    # Read upload data
    data = await file.read()

    # Size check
    if len(data) > MAX_BUNDLE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Bundle too large: {len(data)} bytes (max {MAX_BUNDLE_SIZE})",
        )

    # Content hash
    content_hash = hashlib.sha256(data).hexdigest()

    # Store bundle
    sha256, storage_path = store_bundle(data, content_hash)

    # Extract to temp directory
    with tempfile.TemporaryDirectory() as tmp_dir:
        extract_path = Path(tmp_dir)

        # Security: extract with path traversal check
        try:
            _safe_extract_tar(data, extract_path)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )

        # Validate
        validation = validate_bundle(extract_path)

        # Parse
        ai_debt_dir = _find_ai_debt_dir(extract_path)
        parse_errors: list[str] = []
        if ai_debt_dir is not None:
            parsed = parse_bundle(ai_debt_dir)
            parse_errors = parsed.parse_errors
        else:
            parsed = None

    # Build response
    bundle_id = str(uuid.uuid4())
    return {
        "bundle_id": bundle_id,
        "content_hash": sha256,
        "storage_path": storage_path,
        "file_size_bytes": len(data),
        "is_valid": validation.is_valid,
        "validation": validation.to_dict(),
        "parse_errors": parse_errors,
        "parser_version": "2.2.0",
    }


def _safe_extract_tar(data: bytes, dest: Path) -> None:
    """Extract tar.gz with path traversal protection."""

    tmp_file = dest / "_upload.tar.gz"
    tmp_file.write_bytes(data)

    try:
        with tarfile.open(str(tmp_file), "r:gz") as tar:
            # Check total uncompressed size
            total_size = 0
            for member in tar.getmembers():
                total_size += member.size
                if total_size > MAX_UNCOMPRESSED_SIZE:
                    raise ValueError(f"Uncompressed size too large ({total_size} bytes)")

            # Check for path traversal
            for member in tar.getmembers():
                name = member.name.replace("\\", "/")
                if name.startswith("/") or ".." in name.split("/"):
                    raise ValueError(f"Path traversal detected: {member.name}")

            tar.extractall(str(dest), filter="data")
    except tarfile.TarError as e:
        raise ValueError(f"Invalid tarball: {e}")
    finally:
        tmp_file.unlink(missing_ok=True)


def _find_ai_debt_dir(root: Path) -> Path | None:
    """Find the .ai-debt directory in extracted bundle."""
    if (root / ".ai-debt").is_dir():
        return root / ".ai-debt"
    for child in root.iterdir():
        if child.is_dir() and (child / ".ai-debt").is_dir():
            return child / ".ai-debt"
    if (root / "evidence.json").exists() and (root / "debt-register.json").exists():
        return root
    return None
