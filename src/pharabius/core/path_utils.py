"""Shared path-normalization utilities.

Repository-relative paths are always stored as POSIX-style (forward-slash)
strings in evidence, traceability, and report artifacts. This module provides
canonical helpers so no call site does ad-hoc string replacement.
"""

from __future__ import annotations

from pathlib import Path


def normalize_repo_path(path: str | Path) -> str:
    """Normalize any path to forward-slash POSIX form.

    Rules:
    - Backslashes → forward slashes
    - Consecutive slashes collapsed
    - Leading ./ stripped
    - Trailing slashes stripped
    - Case preserved (not lowercased)
    - Empty string → "."
    """
    s = str(path).replace("\\", "/")
    while "//" in s:
        s = s.replace("//", "/")
    if s.startswith("./"):
        s = s[2:]
    if len(s) > 1 and s.endswith("/"):
        s = s[:-1]
    return s or "."


def relative_repo_path(path: Path, root: Path) -> str:
    """Return normalized repository-relative path as POSIX string."""
    try:
        rel = path.relative_to(root)
    except ValueError:
        return normalize_repo_path(path)
    return normalize_repo_path(rel)


def path_matches_exact_or_suffix(relative: str, pattern: str) -> bool:
    """Match a normalized path against a pattern.

    Use for known artifact discovery such as coverage files.

    Semantics:
    - Exact match: "coverage.json" == "coverage.json"
    - Directory-bearing pattern: "target/site/jacoco/jacoco.xml" matches
      any path ending with "/target/site/jacoco/jacoco.xml"
    - Filename-only pattern (no "/"): matches at any depth
    """
    rel = normalize_repo_path(relative)
    pat = normalize_repo_path(pattern)
    if rel == pat:
        return True
    if "/" in pat:
        # Directory-bearing pattern requires directory-respecting suffix match
        return rel.endswith("/" + pat)
    # Filename-only pattern matches at any depth
    return rel == pat or rel.endswith("/" + pat)


def path_matches_root_pattern(relative: str, pattern: str) -> bool:
    """Match a normalized path against a pattern, root-only for bare filenames.

    Use when filename-only patterns should match only at repository root.

    Semantics:
    - Exact match: "package.json" == "package.json"
    - Pattern with directory: "coverage/cobertura.xml" matches any
      path ending with "coverage/cobertura.xml"
    - Filename-only: "package.json" does NOT match "subdir/package.json"
    """
    rel = normalize_repo_path(relative)
    pat = normalize_repo_path(pattern)
    if rel == pat:
        return True
    if "/" in pat:
        return rel.endswith("/" + pat)
    return False
