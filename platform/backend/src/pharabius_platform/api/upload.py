"""Artifact bundle upload endpoint.

Persists Organization, Repository, ArtifactBundle, Run, Finding,
Claim, Gap, and QualityGateResult records to the database.
"""

from __future__ import annotations

import hashlib
import tarfile
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pharabius_platform.db import get_session
from pharabius_platform.middleware.auth import require_token
from pharabius_platform.models import (
    ArtifactBundle,
    Claim,
    Finding,
    Gap,
    Organization,
    Repository,
    Run,
)
from pharabius_platform.services.parser import parse_bundle
from pharabius_platform.services.storage import store_bundle
from pharabius_platform.services.validator import validate_bundle

router = APIRouter(tags=["bundles"])

MAX_BUNDLE_SIZE = 50 * 1024 * 1024  # 50 MB
MAX_UNCOMPRESSED_SIZE = 500 * 1024 * 1024  # 500 MB


@router.post("/api/v1/bundles", status_code=status.HTTP_201_CREATED)
async def upload_bundle(
    file: UploadFile,
    session: Annotated[AsyncSession, Depends(get_session)],
    token: str = Depends(require_token),
    repository_name: str = "",
) -> dict[str, object]:
    """Upload and process an .ai-debt artifact bundle.

    Accepts a tar.gz archive containing a .ai-debt directory.
    Validates the artifact contract, stores the bundle by content hash,
    persists normalized records to the database, and returns the result.
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

    # Check for duplicate bundle
    existing = await session.execute(
        select(ArtifactBundle).where(ArtifactBundle.content_hash == content_hash)
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Bundle with hash {content_hash} already uploaded.",
        )

    # Store bundle to filesystem
    sha256, storage_path = store_bundle(data, content_hash)

    # Extract to temp directory for validation and parsing
    with tempfile.TemporaryDirectory() as tmp_dir:
        extract_path = Path(tmp_dir)

        try:
            _safe_extract_tar(data, extract_path)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            ) from None

        # Validate artifact contract
        validation = validate_bundle(extract_path)

        # Parse normalized records
        ai_debt_dir = _find_ai_debt_dir(extract_path)
        parse_errors: list[str] = []
        parsed = None
        if ai_debt_dir is not None:
            parsed = parse_bundle(ai_debt_dir)
            parse_errors = parsed.parse_errors

    # --- Persist to database ---

    # 1. Get or create organization
    result = await session.execute(select(Organization).where(Organization.slug == "default"))
    org = result.scalar_one_or_none()
    if org is None:
        org = Organization(name="Default", slug="default")
        session.add(org)
        await session.flush()

    # 2. Get or create repository
    repo_slug = repository_name or content_hash[:12]
    result = await session.execute(
        select(Repository).where(
            Repository.organization_id == org.id,
            Repository.slug == repo_slug,
        )
    )
    repo = result.scalar_one_or_none()
    if repo is None:
        repo_name = repository_name or repo_slug
        repo = Repository(
            organization_id=org.id,
            name=repo_name,
            slug=repo_slug,
            last_uploaded_at=datetime.now(UTC),
        )
        session.add(repo)
        await session.flush()
    else:
        repo.last_uploaded_at = datetime.now(UTC)
        await session.flush()

    # 3. Create ArtifactBundle record
    bundle = ArtifactBundle(
        repository_id=repo.id,
        upload_source="api",
        file_size_bytes=len(data),
        content_hash=sha256,
        storage_path=storage_path,
        is_valid=validation.is_valid,
        validation_report=validation.to_dict(),
    )
    session.add(bundle)
    await session.flush()

    # 4. If parsed data exists, create Run + Finding records
    run_record: Run | None = None
    if parsed is not None and parsed.debt_register is not None:
        findings_list = parsed.debt_register.findings
        total = len(findings_list)
        critical = sum(1 for f in findings_list if f.severity == "Critical")
        high = sum(1 for f in findings_list if f.severity == "High")
        medium = sum(1 for f in findings_list if f.severity == "Medium")
        low = sum(1 for f in findings_list if f.severity == "Low")

        run_id_str = f"RUN-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}"
        run_record = Run(
            bundle_id=bundle.id,
            repository_id=repo.id,
            run_id=run_id_str,
            pharabius_version=parsed.debt_register.schema_version
            if hasattr(parsed.debt_register, "schema_version")
            else "2.2.1",
            total_findings=total,
            critical=critical,
            high=high,
            medium=medium,
            low=low,
            readiness_status="unknown",
            gate_result="unknown",
        )
        session.add(run_record)
        await session.flush()

        # Create Finding records
        for f in findings_list:
            finding_record = Finding(
                run_id=run_record.id,
                finding_id=f.id,
                category=f.category,
                issue_type=getattr(f, "issue_type", "technical_debt"),
                title=f.title,
                severity=f.severity,
                confidence=getattr(f, "confidence", "Medium"),
                risk_score=getattr(f, "risk_score", 0),
                priority=getattr(f, "priority", "Medium"),
            )
            session.add(finding_record)

        # Create Claim records
        for claim in parsed.claims:
            claim_record = Claim(
                bundle_id=bundle.id,
                repository_id=repo.id,
                claim_id=getattr(claim, "claim_id", "CLAIM-UNKNOWN"),
                claim_type=getattr(claim, "claim_type", "behavioral"),
                status=getattr(claim, "status", "unvalidated"),
                confidence=str(getattr(claim, "confidence", "Medium")),
                description=getattr(claim, "description", ""),
            )
            session.add(claim_record)

        # Create Gap records
        for gap in parsed.gaps:
            gap_record = Gap(
                bundle_id=bundle.id,
                repository_id=repo.id,
                gap_id=str(gap.get("gap_id", "GAP-UNKNOWN")),
                description=str(gap.get("description", "")),
                severity=str(gap.get("severity", "Medium")),
            )
            session.add(gap_record)

        await session.flush()

    await session.commit()

    return {
        "bundle_id": str(bundle.id),
        "repository_id": str(repo.id),
        "content_hash": sha256,
        "storage_path": storage_path,
        "file_size_bytes": len(data),
        "is_valid": validation.is_valid,
        "validation": validation.to_dict(),
        "parse_errors": parse_errors,
        "parser_version": "2.2.2",
        "findings_count": run_record.total_findings if run_record else 0,
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
        raise ValueError(f"Invalid tarball: {e}") from None
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
