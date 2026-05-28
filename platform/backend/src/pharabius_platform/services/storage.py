"""Content-addressed bundle storage."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path


def _storage_root() -> Path:
    """Get the configured storage root directory."""
    return Path(os.environ.get("STORAGE_PATH", "platform/storage/bundles"))


def store_bundle(data: bytes, sha256: str | None = None) -> tuple[str, str]:
    """Store a bundle tarball by content hash.

    Returns (sha256, storage_path).
    If the file already exists, returns existing path without overwriting.
    """
    if sha256 is None:
        sha256 = hashlib.sha256(data).hexdigest()

    prefix = sha256[:2]
    storage_path = _storage_root() / prefix / f"{sha256}.tar.gz"
    storage_path.parent.mkdir(parents=True, exist_ok=True)

    if storage_path.exists():
        return sha256, str(storage_path)

    # Atomic write via temp file
    tmp_path = storage_path.with_suffix(".tmp")
    tmp_path.write_bytes(data)
    tmp_path.rename(storage_path)

    return sha256, str(storage_path)


def bundle_exists(sha256: str) -> bool:
    """Check if a bundle with the given hash already exists."""
    prefix = sha256[:2]
    path = _storage_root() / prefix / f"{sha256}.tar.gz"
    return path.exists()
