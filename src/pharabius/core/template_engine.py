"""Template engine — safe placeholder rendering for Markdown artifacts.

Uses simple {{ placeholder }} substitution. No code execution.
No external template engines. Unknown placeholders emit warnings.
"""

from __future__ import annotations

import re
import warnings
from pathlib import Path

# Match {{ placeholder_name }} — no nested braces, no expressions
_PLACEHOLDER_RE = re.compile(r"\{\{\s*(\w+)\s*\}\}")

# Artifacts that support template overrides
TEMPLATEABLE_ARTIFACTS = frozenset(
    {
        "work-package.md",
        "handoff-summary.md",
        "remediation-roadmap.md",
    }
)


def render_template(
    template_text: str,
    placeholders: dict[str, str],
    *,
    artifact_name: str = "",
) -> str:
    """Render a template by substituting {{ key }} placeholders.

    Unknown placeholders in the template produce warnings and render as-is.
    Extra placeholder values not used in the template are silently ignored.
    """
    used_keys: set[str] = set()

    def _replace(match: re.Match[str]) -> str:
        key = match.group(1)
        used_keys.add(key)
        if key in placeholders:
            return placeholders[key]
        if artifact_name:
            warnings.warn(
                f"Unknown placeholder '{{{{ {key} }}}}' in template for "
                f"'{artifact_name}'. Rendering as-is.",
                stacklevel=2,
            )
        else:
            warnings.warn(
                f"Unknown placeholder '{{{{ {key} }}}}'. Rendering as-is.",
                stacklevel=2,
            )
        return match.group(0)

    result = _PLACEHOLDER_RE.sub(_replace, template_text)
    return result


def load_template_file(path: Path) -> str | None:
    """Load a template file safely.

    Returns None if file doesn't exist or can't be read.
    """
    if not path.exists():
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except Exception as exc:
        warnings.warn(
            f"Could not read template '{path}': {exc}. Falling back to built-in default.",
            stacklevel=2,
        )
        return None

    if not text.strip():
        warnings.warn(
            f"Template '{path}' is empty. Falling back to built-in default.",
            stacklevel=2,
        )
        return None

    return text


def _is_safe_path(resolved_path: Path, repo_root: Path, artifact_name: str) -> bool:
    """Verify a resolved path stays within the repository root.

    Rejects path traversal attempts. Warns and returns False if unsafe.
    """
    try:
        resolved_path.relative_to(repo_root)
    except ValueError:
        warnings.warn(
            f"Template override path for '{artifact_name}' escapes "
            f"repository root. Falling back to default.",
            stacklevel=3,
        )
        return False
    return True


def resolve_template_path(
    artifact_name: str,
    repository_root: Path,
    *,
    override_dir: str = "",
    preset: str = "default",
) -> Path | None:
    """Resolve template using lookup order.

    1. governance.yaml templates.override_dir
    2. conventional .ai-debt/templates/{artifact_name}
    3. bundled preset template
    4. None (use built-in default)

    Returns Path if found, None for built-in default.
    """
    if artifact_name not in TEMPLATEABLE_ARTIFACTS:
        return None

    # Resolve repository root once for safety checks
    repo_root = repository_root.resolve()

    # 1. Explicit override_dir from governance.yaml
    if override_dir:
        override_path = (repo_root / override_dir / artifact_name).resolve()
        if not _is_safe_path(override_path, repo_root, artifact_name):
            return None  # warning already emitted
        if override_path.exists():
            return override_path

    # 2. Conventional .ai-debt/templates/ directory
    conventional = (repo_root / ".ai-debt" / "templates" / artifact_name).resolve()
    if conventional.exists():
        return conventional

    # 3. Bundled preset template (inside package, always safe)
    # Map preset name (hyphenated) to directory name (underscored)
    preset_dir = preset.replace("-", "_")
    preset_path = (
        Path(__file__).parent.parent / "presets" / preset_dir / "templates" / artifact_name
    )
    if preset_path.exists():
        return preset_path

    # 4. Built-in default (None means use hardcoded renderer)
    return None


def load_resolved_template(
    artifact_name: str,
    repository_root: Path,
    *,
    override_dir: str = "",
    preset: str = "default",
) -> str | None:
    """Load template text using full lookup cascade.

    Returns template text if a template file is found, None for built-in.
    """
    path = resolve_template_path(
        artifact_name,
        repository_root,
        override_dir=override_dir,
        preset=preset,
    )
    if path is None:
        return None
    return load_template_file(path)
