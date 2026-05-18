"""AI output validation and rejection.

Validates AI-generated enrichment against:
- Schema correctness
- Evidence ID existence
- Finding ID existence
- Analysis unit ID existence (if provided)
- Graph ID existence (if provided)
- Confidence format
- Limitations presence
- No forbidden extra fields
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from pharabius.schemas.ai_enrichment import (
    AIValidationResult,
    FindingEnrichment,
)

_VALID_CONFIDENCE = {"High", "Medium", "Low"}


def _hash_output(raw: str) -> str:
    """Deterministic hash of raw output for audit trail."""
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def validate_finding_enrichment(
    enrichment_data: dict[str, Any],
    valid_finding_ids: set[str],
    valid_evidence_ids: set[str],
    valid_unit_ids: set[str] | None = None,
    valid_graph_ids: set[str] | None = None,
    raw_output_hash: str = "",
) -> AIValidationResult:
    """Validate a single finding enrichment against known IDs.

    Checks (in order):
    1. Schema validity (Pydantic parse)
    2. Finding ID exists
    3. All evidence IDs exist
    4. Analysis unit IDs exist (if provided)
    5. Graph IDs exist (if provided)
    6. Confidence is valid
    7. Limitations is non-empty

    Returns AIValidationResult with is_valid=True/False and details.
    """
    rejection_reasons: list[str] = []
    invalid_fields: list[str] = []
    missing_evidence_ids: list[str] = []

    # 1. Schema validity
    try:
        enrichment = FindingEnrichment.model_validate(enrichment_data)
    except Exception as exc:
        return AIValidationResult(
            enrichment=None,
            is_valid=False,
            rejection_reasons=[f"Schema validation failed: {exc}"],
            invalid_fields=["schema"],
            raw_output_hash=raw_output_hash,
        )

    # 2. Finding ID exists
    if enrichment.finding_id not in valid_finding_ids:
        rejection_reasons.append(f"Unknown finding ID: {enrichment.finding_id}")
        invalid_fields.append("finding_id")

    # 3. Evidence IDs must be non-empty
    if not enrichment.evidence_ids:
        rejection_reasons.append("evidence_ids must contain at least one valid evidence ID")
        invalid_fields.append("evidence_ids")
    else:
        # 3b. Evidence IDs must all exist
        for eid in enrichment.evidence_ids:
            if eid not in valid_evidence_ids:
                missing_evidence_ids.append(eid)
        if missing_evidence_ids:
            rejection_reasons.append(f"Missing evidence IDs: {missing_evidence_ids}")
            invalid_fields.append("evidence_ids")

    # 4. Analysis unit IDs exist (if provided)
    if enrichment.analysis_unit_ids and valid_unit_ids is not None:
        unknown_units = [uid for uid in enrichment.analysis_unit_ids if uid not in valid_unit_ids]
        if unknown_units:
            rejection_reasons.append(f"Unknown analysis unit IDs: {unknown_units}")
            invalid_fields.append("analysis_unit_ids")

    # 5. Graph IDs exist (if provided)
    if enrichment.graph_ids and valid_graph_ids is not None:
        unknown_graphs = [gid for gid in enrichment.graph_ids if gid not in valid_graph_ids]
        if unknown_graphs:
            rejection_reasons.append(f"Unknown graph IDs: {unknown_graphs}")
            invalid_fields.append("graph_ids")

    # 6. Confidence is valid
    if enrichment.confidence not in _VALID_CONFIDENCE:
        rejection_reasons.append(f"Invalid confidence: {enrichment.confidence}")
        invalid_fields.append("confidence")

    # 7. Limitations is non-empty
    if not enrichment.limitations:
        rejection_reasons.append("Limitations must be non-empty")
        invalid_fields.append("limitations")

    is_valid = len(rejection_reasons) == 0

    return AIValidationResult(
        enrichment=enrichment if is_valid else None,
        is_valid=is_valid,
        rejection_reasons=rejection_reasons,
        missing_evidence_ids=missing_evidence_ids,
        invalid_fields=invalid_fields,
        raw_output_hash=raw_output_hash,
    )


def validate_raw_output(
    raw_json: str,
    valid_finding_ids: set[str],
    valid_evidence_ids: set[str],
    valid_unit_ids: set[str] | None = None,
    valid_graph_ids: set[str] | None = None,
) -> list[AIValidationResult]:
    """Parse and validate raw AI JSON output containing enrichments.

    Expected format: {"enrichments": [...]}

    Returns list of AIValidationResult, one per enrichment.
    """
    raw_hash = _hash_output(raw_json)

    try:
        parsed = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        return [
            AIValidationResult(
                enrichment=None,
                is_valid=False,
                rejection_reasons=[f"Malformed JSON: {exc}"],
                invalid_fields=["json"],
                raw_output_hash=raw_hash,
            )
        ]

    enrichments = parsed.get("enrichments")
    if enrichments is None:
        return [
            AIValidationResult(
                enrichment=None,
                is_valid=False,
                rejection_reasons=["Missing 'enrichments' array in output"],
                invalid_fields=["enrichments"],
                raw_output_hash=raw_hash,
            )
        ]
    if not isinstance(enrichments, list):
        return [
            AIValidationResult(
                enrichment=None,
                is_valid=False,
                rejection_reasons=["Expected 'enrichments' array"],
                invalid_fields=["enrichments"],
                raw_output_hash=raw_hash,
            )
        ]

    results: list[AIValidationResult] = []
    for enrichment_data in enrichments:
        if not isinstance(enrichment_data, dict):
            results.append(
                AIValidationResult(
                    enrichment=None,
                    is_valid=False,
                    rejection_reasons=["Enrichment must be a JSON object"],
                    invalid_fields=["type"],
                    raw_output_hash=raw_hash,
                )
            )
            continue

        result = validate_finding_enrichment(
            enrichment_data,
            valid_finding_ids,
            valid_evidence_ids,
            valid_unit_ids,
            valid_graph_ids,
            raw_output_hash=raw_hash,
        )
        results.append(result)

    return results
