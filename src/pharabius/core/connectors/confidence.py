"""Connector confidence assignment.

External scanner output carries confidence information without overclaiming.
Confidence is conservative: missing data lowers the score.

Each confidence level has a deterministic reason stored in
EvidenceItem.metadata["confidence_reason"].

Levels:
    High   — location + rule_id + message present
    Medium — partial location or missing rule metadata
    Low    — missing location, missing rule, or fallback parsing
"""

from __future__ import annotations

from pharabius.schemas.evidence import EvidenceItem

# Confidence levels
CONFIDENCE_HIGH = "High"
CONFIDENCE_MEDIUM = "Medium"
CONFIDENCE_LOW = "Low"

# Deterministic reasons
REASON_LOCATION_RULE_MESSAGE = "location_rule_and_message_present"
REASON_PARTIAL_LOCATION_OR_MISSING_RULE = "partial_location_or_missing_rule"
REASON_MISSING_LOCATION_OR_FALLBACK = "missing_location_or_fallback"


def assign_confidence(
    *,
    has_location: bool,
    has_rule_id: bool,
    has_message: bool,
) -> tuple[str, str]:
    """Assign a conservative confidence level and reason.

    Args:
        has_location: Whether file path and line number are present.
        has_rule_id: Whether a rule/check ID is present.
        has_message: Whether a human-readable message is present.

    Returns:
        Tuple of (confidence_level, confidence_reason).
    """
    if has_location and has_rule_id and has_message:
        return CONFIDENCE_HIGH, REASON_LOCATION_RULE_MESSAGE
    elif has_location or has_rule_id:
        return CONFIDENCE_MEDIUM, REASON_PARTIAL_LOCATION_OR_MISSING_RULE
    else:
        return CONFIDENCE_LOW, REASON_MISSING_LOCATION_OR_FALLBACK


def apply_confidence(
    item: EvidenceItem,
    *,
    has_location: bool,
    has_rule_id: bool,
    has_message: bool,
) -> EvidenceItem:
    """Apply confidence to an evidence item via metadata.

    Returns a new EvidenceItem with confidence and confidence_reason set.
    The original item is not modified (EvidenceItem is a Pydantic model).
    """
    confidence, reason = assign_confidence(
        has_location=has_location,
        has_rule_id=has_rule_id,
        has_message=has_message,
    )
    updated_metadata = {**item.metadata, "confidence_reason": reason}
    return item.model_copy(
        update={
            "confidence": confidence,
            "metadata": updated_metadata,
        }
    )
