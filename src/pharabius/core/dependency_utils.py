"""Dependency version classification utilities.

Provides consistent pinning classification across Python dependency
formats: requirements.txt, pyproject.toml, Poetry, and Pipfile.
"""

from __future__ import annotations

from typing import Literal


def classify_python_specifier(
    specifier: str,
    source_format: str,
) -> Literal["pinned", "broad", "unknown"]:
    """Classify Python dependency pinning from full dependency strings or version fragments.

    Handles both full PEP 508 strings ("requests>=2.0") and bare version
    fragments ("^3.11") used by Poetry and Pipfile.

    Rules:
    - "pinned": ==, ===, @ file/http/https, exact version with no operator
    - "broad": *, ^, ~, ~=, >=, <, !=, empty string, compound ranges,
               bare package names with no version constraint
    - "unknown": anything else

    source_format determines parsing strategy:
    - "pep508": full dependency strings from requirements.txt or pyproject.toml
    - "poetry": version fragments from Poetry dependency tables
    - "pipfile": version fragments from Pipfile sections
    """
    if not specifier or specifier.strip() == "*":
        return "broad"

    s = specifier.strip()

    # Direct references are pinned enough for local evidence model.
    # Preserve spaces during parsing so " @ " detection is reliable.
    if " @ " in s:
        return "pinned"

    # Exact pins — works for both full strings and version fragments
    if "==" in s or "===" in s:
        return "pinned"

    # PEP 508 full dependency strings: "requests>=2.0", "requests", "requests~=2.0"
    if source_format == "pep508":
        # Strip environment markers for classification
        dep_part = s.split(";")[0].strip()
        # Any comparator operator means constrained (but not pinned)
        if any(op in dep_part for op in (">=", "<=", "~=", "!=", ">", "<", "^", "*")):
            return "broad"
        # No version operator at all = bare package name = unpinned
        return "broad"

    # Poetry / Pipfile version fragments: "^3.11", "~2.0", "1.2.3", "*"
    if source_format in ("poetry", "pipfile"):
        if s.startswith(("^", "~", ">", "<", "!", "*", ">=", "<=", "~=")):
            return "broad"
        if "," in s:
            return "broad"
        if s[0].isdigit():
            return "pinned"
        return "broad"

    return "unknown"
