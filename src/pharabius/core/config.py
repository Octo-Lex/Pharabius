"""Config loader — reads .ai-debt/config.yaml after workspace path is known.

Loading order:
1. Start with safe built-in defaults
2. If .ai-debt/config.yaml exists and is valid YAML → merge
3. CLI flags → override both

Safety rules:
- Missing config → safe defaults, no warning
- Malformed YAML → warning + safe defaults
- Schema validation error → warning + safe defaults
- Unknown keys → warning + ignore
- No secrets, no .env, no environment variable loading
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from pharabius.schemas.config import PharabiusConfig

logger = logging.getLogger(__name__)

# Model-level field names (for unknown key detection)
_KNOWN_TOP_KEYS: frozenset[str] = frozenset(PharabiusConfig.model_fields.keys())


def _safe_defaults() -> PharabiusConfig:
    """Return safe built-in defaults."""
    return PharabiusConfig()


def _parse_yaml(content: str) -> dict[str, Any] | None:
    """Parse YAML content. Returns None on failure."""
    try:
        data = yaml.safe_load(content)
        if isinstance(data, dict):
            return data
        # YAML parsed to non-dict (e.g. plain string)
        return None
    except yaml.YAMLError:
        return None


def _find_unknown_keys(data: dict[str, Any]) -> list[str]:
    """Return top-level keys not in the schema."""
    return [k for k in data if k not in _KNOWN_TOP_KEYS]


def load_config(repository_root: Path) -> PharabiusConfig:
    """Load config from .ai-debt/config.yaml.

    Returns safe defaults if config is missing or malformed.
    Logs warnings for malformed YAML, schema errors, and unknown keys.
    """
    config_path = repository_root.resolve() / ".ai-debt" / "config.yaml"

    if not config_path.exists():
        return _safe_defaults()

    try:
        content = config_path.read_text(encoding="utf-8")
    except OSError:
        logger.warning("Could not read config.yaml — using safe defaults")
        return _safe_defaults()

    if not content.strip():
        return _safe_defaults()

    data = _parse_yaml(content)
    if data is None:
        logger.warning("config.yaml is malformed — using safe defaults")
        return _safe_defaults()

    # Detect unknown keys
    unknown = _find_unknown_keys(data)
    if unknown:
        logger.warning("config.yaml has unknown keys: %s — ignored", ", ".join(unknown))

    # Validate with Pydantic
    try:
        config = PharabiusConfig.model_validate(data)
    except ValidationError as exc:
        # Show first few errors
        errors = exc.errors()
        for err in errors[:3]:
            field = ".".join(str(loc) for loc in err.get("loc", []))
            logger.warning(
                "config.yaml field '%s': %s — using safe default",
                field,
                err.get("msg", "validation error"),
            )
        if len(errors) > 3:
            logger.warning("... and %d more config errors", len(errors) - 3)
        return _safe_defaults()

    return config


def effective_exclude_paths(config: PharabiusConfig) -> set[str]:
    """Return effective exclude paths from config (supplements hardcoded).

    These are ADDITIONAL exclusions beyond the built-in EXCLUDED_DIR_NAMES.
    """
    return set(config.analysis.exclude_paths)
