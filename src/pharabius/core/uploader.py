"""HTTP upload client for Pharabius platform."""

from __future__ import annotations

import hashlib
import io
import tarfile
from pathlib import Path

import httpx


def create_bundle_tarball(ai_debt_dir: Path) -> tuple[bytes, str]:
    """Create a tar.gz from the .ai-debt directory.

    Returns (tarball_bytes, sha256_hash).
    """
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for file_path in ai_debt_dir.rglob("*"):
            if file_path.is_file():
                arcname = f".ai-debt/{file_path.relative_to(ai_debt_dir)}"
                tar.add(str(file_path), arcname=arcname)

    data = buf.getvalue()
    sha256 = hashlib.sha256(data).hexdigest()
    return data, sha256


def upload_bundle(
    url: str,
    token: str,
    ai_debt_dir: Path,
    repository_name: str = "",
) -> dict[str, object]:
    """Upload .ai-debt bundle to the platform.

    Returns the API response as a dict.
    Raises httpx.HTTPStatusError on non-2xx responses.
    """
    data, _sha256 = create_bundle_tarball(ai_debt_dir)

    response = httpx.post(
        f"{url.rstrip('/')}/api/v1/bundles",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("pharabius-bundle.tar.gz", data, "application/gzip")},
        data={"repository_name": repository_name},
        timeout=60.0,
    )
    response.raise_for_status()
    result: dict[str, object] = response.json()
    return result
