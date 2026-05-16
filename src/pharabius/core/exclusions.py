"""Shared exclusion logic for scanner and profiler."""

from __future__ import annotations

from pathlib import Path

EXCLUDED_DIR_NAMES: frozenset[str] = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        ".ai-debt",
        ".venv",
        "venv",
        "env",
        "node_modules",
        "vendor",
        "dist",
        "build",
        "coverage",
        ".next",
        ".turbo",
        ".pytest_cache",
        ".ruff_cache",
        ".mypy_cache",
        "__pycache__",
        "target",
        "out",
    }
)


def is_excluded_path(path: Path, root: Path) -> bool:
    """Return True if any path component matches an excluded directory name."""
    try:
        relative_parts = path.relative_to(root).parts
    except ValueError:
        return True

    return any(part in EXCLUDED_DIR_NAMES for part in relative_parts)
