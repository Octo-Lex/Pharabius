"""Candidate finding proposal from external evidence (v3.6.0).

Proposes candidate findings from external connector evidence.
Candidates are review artifacts, NOT accepted debt findings.

Design rules:
- Only processes evidence with source="external_connector"
- Only processes evidence with type="external_scanner_result"
- Generates one candidate per evidence item (granular review)
- Stores provenance in dedicated CandidateProvenance model
- Candidates go to .ai-debt/candidate-findings.json, NOT debt-register.json
- No auto-promotion. No auto-approval. No historical artifact mutation.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from pharabius.schemas.candidate import (
    CandidateFinding,
    CandidateFindingsArtifact,
    CandidateFindingsSummary,
    CandidateProvenance,
)
from pharabius.schemas.evidence import EvidenceStore

CONNECTOR_EVIDENCE_SOURCE = "external_connector"
EXTERNAL_SCANNER_RESULT_TYPE = "external_scanner_result"

# Candidate ID prefix
CANDIDATE_ID_PREFIX = "CAND"


def propose_candidates(
    evidence_store: EvidenceStore,
) -> CandidateFindingsArtifact:
    """Propose candidate findings from external connector evidence.

    This is a pure function — it reads evidence and returns a new artifact.
    It does NOT write to disk or modify any existing artifact.

    Returns a CandidateFindingsArtifact ready for optional serialization.
    """
    external_items = [
        item
        for item in evidence_store.evidence
        if item.source == CONNECTOR_EVIDENCE_SOURCE and item.type == EXTERNAL_SCANNER_RESULT_TYPE
    ]

    if not external_items:
        return CandidateFindingsArtifact()

    candidates: list[CandidateFinding] = []
    for counter, item in enumerate(external_items, start=1):
        # Extract connector provenance from metadata
        meta = item.metadata or {}
        cp = meta.get("connector_provenance", {})
        connector_name = cp.get("connector_name", "unknown")
        source_format = cp.get("source_format", "unknown")

        candidate_id = f"{CANDIDATE_ID_PREFIX}-{counter:04d}"

        provenance = CandidateProvenance(
            connector_name=connector_name,
            source_format=source_format,
            evidence_count=1,
            evidence_ids=[item.evidence_id],
            source_types=[item.type],
        )

        # Build locations from evidence location
        locations: list[str] = []
        if item.location and item.location.file:
            loc_str = item.location.file
            if item.location.line_start:
                loc_str += f":{item.location.line_start}"
            locations.append(loc_str)

        # Extract severity from metadata if available (v3.3.0 convention)
        severity = "Unscored"
        if meta.get("severity"):
            severity = meta["severity"]

        # Confidence from evidence item
        confidence = item.confidence if item.confidence else "Low"

        candidate = CandidateFinding(
            id=candidate_id,
            category=item.category,
            title=item.summary[:200] if item.summary else f"External finding from {connector_name}",
            description=item.summary or item.raw_observation or "No description available.",
            severity=severity,
            confidence=confidence,
            status="Candidate",
            locations=locations,
            evidence_ids=[item.evidence_id],
            risk_score=0,
            priority="Unscored",
            provenance=provenance,
        )
        candidates.append(candidate)

    # Build summary
    by_connector = dict(Counter(c.provenance.connector_name for c in candidates))
    by_category = dict(Counter(c.category for c in candidates))
    by_severity = dict(Counter(c.severity for c in candidates))

    summary = CandidateFindingsSummary(
        total_candidates=len(candidates),
        by_connector=by_connector,
        by_category=by_category,
        by_severity=by_severity,
    )

    return CandidateFindingsArtifact(
        summary=summary,
        candidates=candidates,
    )


def get_candidate_provenance(candidate: CandidateFinding) -> CandidateProvenance:
    """Access provenance for a candidate finding.

    Provenance is stored in its own model, not in risk_breakdown or metadata.
    """
    return candidate.provenance


def write_candidate_artifact(
    artifact: CandidateFindingsArtifact,
    repository_root: Path,
) -> Path:
    """Write candidate findings artifact to .ai-debt/candidate-findings.json.

    This is a separate artifact from debt-register.json.
    Does not modify any existing artifact.
    """
    ai_debt_dir = repository_root.resolve() / ".ai-debt"
    ai_debt_dir.mkdir(parents=True, exist_ok=True)
    output_path = ai_debt_dir / "candidate-findings.json"
    output_path.write_text(
        artifact.model_dump_json(indent=2),
        encoding="utf-8",
    )
    return output_path


def load_candidate_artifact(repository_root: Path) -> CandidateFindingsArtifact:
    """Load candidate findings artifact. Returns empty if missing.

    Missing artifact is not an error — candidates are optional.
    """
    path = repository_root.resolve() / ".ai-debt" / "candidate-findings.json"
    if not path.exists():
        return CandidateFindingsArtifact()
    data = path.read_text(encoding="utf-8")
    return CandidateFindingsArtifact.model_validate_json(data)
