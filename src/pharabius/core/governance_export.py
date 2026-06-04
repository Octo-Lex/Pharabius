"""Governance analytics export.

Machine-readable governance analytics export in stable JSON format.
Does not create findings, advisories, work packages, or alter behavior.
Does not apply quality gates, thresholds, pass/fail, or policy decisions.

Export schema versioning follows additive compatibility:
new fields may be added; existing fields are never removed or renamed.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from pharabius.core.signals.quality import (
    GovernanceQualityMetrics,
    governance_quality_metrics_to_dict,
)
from pharabius.core.signals.trends import (
    GovernanceTrendSummary,
    governance_trend_to_dict,
)

SCHEMA_VERSION = "1.0"
EXPORT_TYPE = "governance_analytics"

# Forbidden field names — policy interpretation is not allowed
_FORBIDDEN_FIELDS = frozenset(
    {
        "pass",
        "fail",
        "score",
        "grade",
        "compliant",
        "noncompliant",
        "healthy",
        "unhealthy",
    }
)


def _get_tool_version() -> str:
    try:
        from importlib.metadata import version

        return version("pharabius")
    except Exception:
        return "unknown"


def _validate_no_forbidden_fields(data: dict) -> list[str]:
    """Check for forbidden policy/gate field names in exported data."""
    warnings: list[str] = []
    for key in data:
        if key.lower() in _FORBIDDEN_FIELDS:
            warnings.append(f"Forbidden field '{key}' found in export data")
    return warnings


def build_governance_export(
    *,
    signal_summary: dict | None = None,
    governance_quality: GovernanceQualityMetrics | None = None,
    governance_trends: GovernanceTrendSummary | None = None,
    run_id: str | None = None,
    families_governed: int = 10,
) -> dict:
    """Build governance analytics export dictionary.

    Stable schema: schema_version, export_type, and all governance data.
    Does not introduce policy interpretation.
    """
    quality_dict = None
    if governance_quality is not None:
        quality_dict = governance_quality_metrics_to_dict(governance_quality)

    trend_dict = None
    if governance_trends is not None:
        trend_dict = governance_trend_to_dict(governance_trends)

    diagnostics = []
    if quality_dict and quality_dict.get("diagnostics"):
        diagnostics = quality_dict["diagnostics"]

    export = {
        "schema_version": SCHEMA_VERSION,
        "export_type": EXPORT_TYPE,
        "tool_version": _get_tool_version(),
        "run_id": run_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "signal_summary": signal_summary,
        "governance_quality": quality_dict,
        "governance_trends": trend_dict,
        "diagnostics": diagnostics,
        "recurring_diagnostics": (
            trend_dict.get("recurring_diagnostics", []) if trend_dict else []
        ),
        "metadata": {
            "families_governed": families_governed,
            "source": "run_history",
        },
    }

    return export


def write_governance_export(
    export: dict,
    output_path: Path,
) -> Path:
    """Write governance analytics export as JSON.

    Creates parent directories if needed.
    Returns the path to the written file.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(export, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return output_path


def write_governance_export_jsonl(
    export: dict,
    output_path: Path,
) -> Path:
    """Write governance analytics export as JSONL (single line).

    Useful for streaming/append-based consumers.
    Creates parent directories if needed.
    Returns the path to the written file.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(export, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return output_path
