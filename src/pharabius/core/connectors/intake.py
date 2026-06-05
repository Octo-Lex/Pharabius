"""Evidence intake policy and combination logic.

Governs how external evidence (from connectors) is combined with native
evidence (from repository scan) into a single combined EvidenceStore.

Design rules:
- Native evidence items are preserved unchanged.
- External evidence items preserve source, metadata, provenance, confidence.
- External evidence IDs are deterministically namespaced for uniqueness.
- Semantic duplicates are skipped deterministically, never overwritten.
- Source files are processed in stable sorted order.
- No evidence is silently overwritten.
- Combined evidence is explicit, deterministic, and lineage-preserving.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from pharabius.schemas.evidence import EvidenceItem, EvidenceStore

# ---------------------------------------------------------------------------
# S01 — Intake Policy Model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IntakePolicy:
    """Controls how external evidence is combined with native evidence.

    Attributes:
        allow_external: Whether external evidence is accepted.
        deduplicate: Whether semantic duplicate detection is applied.
        preserve_lineage: Always True — cannot be disabled.
        max_external_items: Safety cap on external evidence items.
    """

    allow_external: bool = True
    deduplicate: bool = True
    preserve_lineage: bool = True  # Always True — invariant
    max_external_items: int = 1000


# ---------------------------------------------------------------------------
# S04 — Manifest Models
# ---------------------------------------------------------------------------


class EvidenceSourceRecord(BaseModel):
    """Record of a single evidence source in the combination."""

    source_type: str  # "native" or "external"
    source_file: str
    evidence_count: int = 0
    imported_count: int = 0
    duplicate_count: int = 0
    skipped_count: int = 0
    imported_at: str = ""


class CombinedEvidenceManifest(BaseModel):
    """Manifest tracking all sources in a combined evidence store."""

    schema_version: str = "1.0"
    native: EvidenceSourceRecord | None = None
    external_sources: list[EvidenceSourceRecord] = Field(default_factory=list)
    total_native: int = 0
    total_external: int = 0
    total_combined: int = 0
    deduplicated: int = 0
    warnings: list[str] = Field(default_factory=list)
    combined_at: str = Field(
        default_factory=lambda: datetime.now(UTC).replace(microsecond=0).isoformat()
    )


# ---------------------------------------------------------------------------
# S02 — Combine Result
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CombineResult:
    """Result from combining native and external evidence."""

    combined: EvidenceStore
    manifest: CombinedEvidenceManifest
    native_count: int
    external_count: int
    duplicate_count: int
    skipped_count: int
    warnings: list[str] = field(default_factory=list)
    ok: bool = True


# ---------------------------------------------------------------------------
# S03 — Deterministic ID namespacing + semantic duplicate detection
# ---------------------------------------------------------------------------


def _namespace_external_id(
    item: EvidenceItem,
    source_file: str,
    source_index: int,
) -> str:
    """Create a globally unique evidence ID for an external item.

    Format: EXT-{prefix}-{hash6}-{seq}
    where prefix comes from connector provenance or source file stem,
    hash6 is first 6 chars of source file path hash,
    seq is the item index within the source.

    Guarantees uniqueness across all sources while remaining deterministic.
    """
    prov = item.metadata.get("connector_provenance", {})
    connector_name = prov.get("connector_name", "EXT")
    # Deterministic hash of source file path for disambiguation
    path_hash = hashlib.sha256(source_file.encode()).hexdigest()[:6].upper()
    return f"EXT-{connector_name.upper()}-{path_hash}-{source_index:06d}"


def _semantic_fingerprint(item: EvidenceItem) -> str:
    """Deterministic fingerprint for semantic duplicate detection.

    Uses: source, connector_name, rule_id, location file, line_start, summary.
    """
    prov = item.metadata.get("connector_provenance", {})
    connector_name = prov.get("connector_name", "")
    rule_id = prov.get("source_rule_id", "")
    parts = [
        item.source,
        connector_name,
        rule_id,
        item.location.file,
        str(item.location.line_start or ""),
        item.summary[:200] if item.summary else "",
    ]
    return "|".join(parts)


def _build_intake_metadata(
    original_id: str,
    combined_id: str,
    source_file: str,
    source_index: int,
    status: str,
) -> dict[str, Any]:
    """Build intake metadata for lineage tracking."""
    return {
        "intake": {
            "original_evidence_id": original_id,
            "combined_evidence_id": combined_id,
            "source_file": source_file,
            "source_index": source_index,
            "deduplication_status": status,
        }
    }


# ---------------------------------------------------------------------------
# S02 — Combine Evidence Library Function
# ---------------------------------------------------------------------------


def combine_evidence(
    native_path: Path,
    external_paths: list[Path],
    policy: IntakePolicy | None = None,
) -> CombineResult:
    """Combine native and external evidence into a single EvidenceStore.

    Args:
        native_path: Path to native evidence store (.ai-debt/evidence.json).
        external_paths: Paths to external evidence stores (sorted for determinism).
        policy: Intake policy controls. Defaults to permissive.

    Returns:
        CombineResult with combined store, manifest, counts, and warnings.
    """
    if policy is None:
        policy = IntakePolicy()

    warnings: list[str] = []
    now = datetime.now(UTC).replace(microsecond=0).isoformat()

    # --- Load native evidence ---
    native_store = _load_store(native_path)
    native_items: list[EvidenceItem] = []
    if native_store is not None:
        native_items = list(native_store.evidence)

    native_record = EvidenceSourceRecord(
        source_type="native",
        source_file=str(native_path),
        evidence_count=len(native_items),
        imported_count=len(native_items),
        imported_at=now,
    )

    # --- Deterministic source ordering ---
    sorted_external = sorted(external_paths, key=lambda p: str(p))

    # --- Dedup tracking ---
    seen_fingerprints: set[str] = set()
    # Pre-populate with native fingerprints (native items are never deduped
    # against external, but we track them to avoid false positives)
    for item in native_items:
        seen_fingerprints.add(f"native:{item.evidence_id}")

    combined_items: list[EvidenceItem] = list(native_items)  # Native first, unchanged
    external_records: list[EvidenceSourceRecord] = []
    total_external = 0
    total_duplicate = 0
    total_skipped = 0

    if not policy.allow_external:
        warnings.append("External evidence disabled by intake policy")
    else:
        for ext_path in sorted_external:
            ext_store = _load_store(ext_path)
            if ext_store is None:
                warnings.append(f"Could not load external evidence: {ext_path}")
                external_records.append(
                    EvidenceSourceRecord(
                        source_type="external",
                        source_file=str(ext_path),
                        evidence_count=0,
                        imported_count=0,
                        imported_at=now,
                    )
                )
                total_skipped += 1
                continue

            ext_items = ext_store.evidence
            imported = 0
            dup_count = 0

            for idx, item in enumerate(ext_items):
                total_external += 1

                # Safety cap
                if imported >= policy.max_external_items:
                    warnings.append(
                        f"External evidence cap reached ({policy.max_external_items}) in {ext_path}"
                    )
                    total_skipped += len(ext_items) - idx
                    break

                # Semantic duplicate detection
                if policy.deduplicate:
                    fp = _semantic_fingerprint(item)
                    if fp in seen_fingerprints:
                        dup_count += 1
                        total_duplicate += 1
                        continue
                    seen_fingerprints.add(fp)

                # Namespace the external ID for uniqueness
                combined_id = _namespace_external_id(item, str(ext_path), idx + 1)

                # Build intake metadata — preserve existing metadata
                intake_meta = _build_intake_metadata(
                    original_id=item.evidence_id,
                    combined_id=combined_id,
                    source_file=str(ext_path),
                    source_index=idx + 1,
                    status="renamed_for_uniqueness" if combined_id != item.evidence_id else "kept",
                )

                # Create new item with namespaced ID and merged metadata
                merged_meta = {**item.metadata, **intake_meta}
                new_item = EvidenceItem(
                    evidence_id=combined_id,
                    source=item.source,
                    type=item.type,
                    category=item.category,
                    location=item.location.model_copy(),
                    subject=item.subject,
                    object=item.object,
                    summary=item.summary,
                    raw_observation=item.raw_observation,
                    confidence=item.confidence,
                    collected_at=item.collected_at,
                    metadata=merged_meta,
                )
                combined_items.append(new_item)
                imported += 1

            external_records.append(
                EvidenceSourceRecord(
                    source_type="external",
                    source_file=str(ext_path),
                    evidence_count=len(ext_items),
                    imported_count=imported,
                    duplicate_count=dup_count,
                    imported_at=now,
                )
            )

    # --- Build combined store ---
    combined_store = EvidenceStore(
        repository=native_store.repository if native_store else "",
        evidence=combined_items,
    )

    # --- Build manifest ---
    manifest = CombinedEvidenceManifest(
        native=native_record,
        external_sources=external_records,
        total_native=len(native_items),
        total_external=total_external,
        total_combined=len(combined_items),
        deduplicated=total_duplicate,
        warnings=warnings,
        combined_at=now,
    )

    return CombineResult(
        combined=combined_store,
        manifest=manifest,
        native_count=len(native_items),
        external_count=total_external,
        duplicate_count=total_duplicate,
        skipped_count=total_skipped,
        warnings=warnings,
        ok=True,
    )


def _load_store(path: Path) -> EvidenceStore | None:
    """Load an EvidenceStore from a JSON file. Returns None on failure."""
    try:
        data = path.read_text(encoding="utf-8")
        return EvidenceStore.model_validate_json(data)
    except (FileNotFoundError, ValueError, OSError):
        return None
