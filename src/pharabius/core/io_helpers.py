"""Shared file I/O helpers.

Provides read_text and read_json with consistent error handling
across scanner, coverage parsers, dependency parsers, and runtime detectors.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read_text(path: Path, *, max_chars: int = 100_000) -> str:
    """Read file as UTF-8 text.

    Behavior:
    - Missing or unreadable file returns ""
    - UTF-8 with errors='ignore' (same as original scanner helper)
    - Output capped at max_chars characters (default 100K)
    """
    try:
        return path.read_text(encoding="utf-8", errors="ignore")[:max_chars]
    except (OSError, UnicodeDecodeError):
        return ""


def read_json(path: Path) -> dict[str, Any]:
    """Read file as JSON, returning a dict.

    Behavior:
    - Missing or unreadable file returns {}
    - Invalid JSON returns {}
    - Non-dict JSON (arrays, scalars) returns {}
    - Reads as UTF-8
    """
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return {}

    if isinstance(value, dict):
        return value
    return {}
