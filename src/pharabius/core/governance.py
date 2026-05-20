"""Governance loader — reads .ai-debt/governance.yaml safely.

Missing/malformed governance.yaml → safe defaults + warnings.
"""

from __future__ import annotations

import warnings
from pathlib import Path

import yaml
from pydantic import ValidationError

from pharabius.schemas.governance import GovernanceConfig


def load_governance(repository_root: Path) -> GovernanceConfig:
    """Load governance.yaml from .ai-debt/ directory.

    Returns GovernanceConfig with safe defaults if file is missing or malformed.
    Emits warnings for any issues encountered.
    """
    governance_path = repository_root / ".ai-debt" / "governance.yaml"

    if not governance_path.exists():
        return GovernanceConfig()

    try:
        raw = governance_path.read_text(encoding="utf-8")
    except Exception as exc:
        warnings.warn(
            f"Could not read governance.yaml: {exc}. Using defaults.",
            stacklevel=2,
        )
        return GovernanceConfig()

    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        warnings.warn(
            f"Malformed governance.yaml: {exc}. Using defaults.",
            stacklevel=2,
        )
        return GovernanceConfig()

    if not isinstance(data, dict):
        warnings.warn(
            "governance.yaml is not a mapping. Using defaults.",
            stacklevel=2,
        )
        return GovernanceConfig()

    try:
        config = GovernanceConfig.model_validate(data)
    except ValidationError as exc:
        warnings.warn(
            f"Invalid governance.yaml: {exc}. Using defaults.",
            stacklevel=2,
        )
        return GovernanceConfig()

    # Warn about unknown top-level keys
    known_keys = set(GovernanceConfig.model_fields.keys())
    unknown = set(data.keys()) - known_keys
    if unknown:
        warnings.warn(
            f"Unknown governance.yaml keys: {sorted(unknown)}. Ignoring.",
            stacklevel=2,
        )

    return config


def effective_preset(governance: GovernanceConfig) -> str:
    """Return the effective preset name, warning if unknown."""
    known = {
        "default",
        "platform-engineering",
        "security-sensitive",
        "compliance-sensitive",
        "startup-lean",
    }
    if governance.preset not in known:
        warnings.warn(
            f"Unknown preset '{governance.preset}'. Falling back to 'default'.",
            stacklevel=2,
        )
        return "default"
    return governance.preset


def default_governance_yaml() -> str:
    """Return the default governance.yaml content for `ai-debt init`."""
    return """\
# governance.yaml — Pharabius output governance
# Controls how findings are presented, not what findings are generated.
# This file does NOT change scanner, analyzer, or provider behavior.

preset: default  # default, platform-engineering, security-sensitive, compliance-sensitive

review:
  require_evidence_review: true
  require_business_impact_review: true
  review_checklist: true

templates:
  # Override directory for custom Markdown templates.
  # Lookup: project-local override → preset template → built-in default
  override_dir: ""  # empty = no overrides

handoff:
  include_escalation_guide: true
  include_triage_guide: true
  max_work_packages: 10

safety:
  # These are enforced by the engine regardless of this file.
  no_finding_suppression: true
  no_severity_escalation: true
  no_evidence_id_changes: true
  no_canonical_json_mutation: true
  no_ai_canonical_mutation: true
  no_remediation_execution: true
"""
