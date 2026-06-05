"""v3.2.0 Evidence Intake Policy — library-level tests.

Tests intake policy model, combine logic, manifest, lineage,
duplicate handling, ID namespacing, and deterministic ordering.

Acceptance criteria verified:
  1. Native-only analyze behavior is unchanged.
  2. combine-evidence never mutates .ai-debt/evidence.json.
  3. Combined evidence IDs are unique.
  4. Native evidence IDs are preserved.
  5. External original evidence IDs are preserved in metadata.
  6. External IDs are deterministically namespaced when needed.
  7. Semantic duplicates are skipped deterministically, not overwritten.
  8. External source files are processed in stable sorted order.
  9. Combined manifest records source files, counts, duplicates, skipped items,
     and warnings.
  10. analyze --evidence reads the specified EvidenceStore path.
  11. analyze without --evidence still reads .ai-debt/evidence.json.
  12. External scanner evidence does not create new findings unless future
      analyzer logic explicitly supports it.
  13. CLI supports explicit --output and --manifest-output for deterministic tests.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pharabius.core.connectors.intake import (
    IntakePolicy,
    _namespace_external_id,
    _semantic_fingerprint,
    combine_evidence,
)
from pharabius.schemas.evidence import EvidenceItem, EvidenceLocation, EvidenceStore

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "intake"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_native_store(items: int = 2) -> EvidenceStore:
    """Create a native evidence store with N items."""
    evidence = []
    for i in range(1, items + 1):
        evidence.append(
            EvidenceItem(
                evidence_id=f"EVD-{i:06d}",
                source="repository_scan",
                type="manifest_detected",
                category="TD-DEP",
                summary=f"Native evidence item {i}",
                location=EvidenceLocation(file=f"src/file{i}.py"),
            )
        )
    return EvidenceStore(repository="/test/repo", evidence=evidence)


def _make_external_store(
    connector_name: str = "sarif",
    count: int = 2,
    evidence_ids: list[str] | None = None,
    summaries: list[str] | None = None,
    rule_ids: list[str] | None = None,
    locations: list[tuple[str, int | None]] | None = None,
) -> EvidenceStore:
    """Create an external evidence store with N items."""
    evidence = []
    for i in range(1, count + 1):
        eid = evidence_ids[i - 1] if evidence_ids else f"EXT-{connector_name.upper()}-{i:06d}"
        summary = summaries[i - 1] if summaries else f"External item {i}"
        rule_id = rule_ids[i - 1] if rule_ids else f"rule-{i}"
        loc = locations[i - 1] if locations else (f"src/ext{i}.py", i * 10)

        metadata: dict = {
            "connector_provenance": {
                "connector_name": connector_name,
                "source_rule_id": rule_id,
            }
        }
        evidence.append(
            EvidenceItem(
                evidence_id=eid,
                source="external_connector",
                type="external_scanner_result",
                category="TD-EXT",
                summary=summary,
                location=EvidenceLocation(file=loc[0], line_start=loc[1]),
                metadata=metadata,
            )
        )
    return EvidenceStore(repository="", evidence=evidence)


def _write_store(tmp_path: Path, name: str, store: EvidenceStore) -> Path:
    """Write an EvidenceStore to a temp file and return the path."""
    p = tmp_path / name
    p.write_text(store.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# S01 — Intake Policy Model
# ---------------------------------------------------------------------------


class TestIntakePolicy:
    def test_defaults(self) -> None:
        policy = IntakePolicy()
        assert policy.allow_external is True
        assert policy.deduplicate is True
        assert policy.preserve_lineage is True
        assert policy.max_external_items == 1000

    def test_frozen(self) -> None:
        policy = IntakePolicy()
        with pytest.raises(AttributeError):
            policy.allow_external = False  # type: ignore[misc]

    def test_custom(self) -> None:
        policy = IntakePolicy(allow_external=False, max_external_items=50)
        assert policy.allow_external is False
        assert policy.max_external_items == 50


# ---------------------------------------------------------------------------
# S03 — Deterministic ID namespacing
# ---------------------------------------------------------------------------


class TestNamespaceExternalId:
    def test_deterministic(self) -> None:
        item = EvidenceItem(
            evidence_id="EXT-SARIF-000001",
            source="external_connector",
            type="external_scanner_result",
            category="TD-EXT",
            summary="Test",
            metadata={
                "connector_provenance": {"connector_name": "sarif"},
            },
        )
        id1 = _namespace_external_id(item, "/path/to/file.json", 1)
        id2 = _namespace_external_id(item, "/path/to/file.json", 1)
        assert id1 == id2

    def test_different_source_different_id(self) -> None:
        item = EvidenceItem(
            evidence_id="EXT-SARIF-000001",
            source="external_connector",
            type="external_scanner_result",
            category="TD-EXT",
            summary="Test",
            metadata={
                "connector_provenance": {"connector_name": "sarif"},
            },
        )
        id1 = _namespace_external_id(item, "/path/a.json", 1)
        id2 = _namespace_external_id(item, "/path/b.json", 1)
        assert id1 != id2

    def test_different_index_different_id(self) -> None:
        item = EvidenceItem(
            evidence_id="EXT-SARIF-000001",
            source="external_connector",
            type="external_scanner_result",
            category="TD-EXT",
            summary="Test",
            metadata={
                "connector_provenance": {"connector_name": "sarif"},
            },
        )
        id1 = _namespace_external_id(item, "/path/file.json", 1)
        id2 = _namespace_external_id(item, "/path/file.json", 2)
        assert id1 != id2

    def test_starts_with_ext(self) -> None:
        item = EvidenceItem(
            evidence_id="X",
            source="external_connector",
            type="external_scanner_result",
            category="TD-EXT",
            summary="Test",
            metadata={
                "connector_provenance": {"connector_name": "semgrep"},
            },
        )
        result = _namespace_external_id(item, "/path/file.json", 1)
        assert result.startswith("EXT-SEMGREP-")

    def test_no_provenance_uses_ext(self) -> None:
        item = EvidenceItem(
            evidence_id="X",
            source="external_connector",
            type="external_scanner_result",
            category="TD-EXT",
            summary="Test",
        )
        result = _namespace_external_id(item, "/path/file.json", 1)
        assert result.startswith("EXT-EXT-")


# ---------------------------------------------------------------------------
# S03 — Semantic fingerprint
# ---------------------------------------------------------------------------


class TestSemanticFingerprint:
    def test_same_item_same_fingerprint(self) -> None:
        item = _make_external_store(count=1).evidence[0]
        fp1 = _semantic_fingerprint(item)
        fp2 = _semantic_fingerprint(item)
        assert fp1 == fp2

    def test_different_summary_different_fingerprint(self) -> None:
        store1 = _make_external_store(count=1, summaries=["Alpha"])
        store2 = _make_external_store(count=1, summaries=["Beta"])
        fp1 = _semantic_fingerprint(store1.evidence[0])
        fp2 = _semantic_fingerprint(store2.evidence[0])
        assert fp1 != fp2

    def test_different_location_different_fingerprint(self) -> None:
        store1 = _make_external_store(count=1, locations=[("a.py", 10)])
        store2 = _make_external_store(count=1, locations=[("b.py", 10)])
        fp1 = _semantic_fingerprint(store1.evidence[0])
        fp2 = _semantic_fingerprint(store2.evidence[0])
        assert fp1 != fp2

    def test_different_rule_different_fingerprint(self) -> None:
        store1 = _make_external_store(count=1, rule_ids=["rule-a"])
        store2 = _make_external_store(count=1, rule_ids=["rule-b"])
        fp1 = _semantic_fingerprint(store1.evidence[0])
        fp2 = _semantic_fingerprint(store2.evidence[0])
        assert fp1 != fp2


# ---------------------------------------------------------------------------
# S02 — Combine Evidence
# ---------------------------------------------------------------------------


class TestCombineEvidence:
    def test_native_only(self, tmp_path: Path) -> None:
        """AC1: Native-only behavior is unchanged."""
        native = _make_native_store(3)
        native_path = _write_store(tmp_path, "native.json", native)

        result = combine_evidence(native_path, [])
        assert result.ok is True
        assert result.native_count == 3
        assert result.external_count == 0
        assert len(result.combined.evidence) == 3
        # Native IDs preserved
        for i, item in enumerate(result.combined.evidence, 1):
            assert item.evidence_id == f"EVD-{i:06d}"

    def test_native_plus_external(self, tmp_path: Path) -> None:
        """AC3,4: Combined IDs unique, native IDs preserved."""
        native = _make_native_store(2)
        external = _make_external_store("sarif", 3)
        native_path = _write_store(tmp_path, "native.json", native)
        ext_path = _write_store(tmp_path, "ext.json", external)

        result = combine_evidence(native_path, [ext_path])
        assert result.ok is True
        assert result.native_count == 2
        assert result.external_count == 3
        assert len(result.combined.evidence) == 5

        # All IDs unique
        ids = [item.evidence_id for item in result.combined.evidence]
        assert len(ids) == len(set(ids))

        # Native IDs preserved exactly
        assert result.combined.evidence[0].evidence_id == "EVD-000001"
        assert result.combined.evidence[1].evidence_id == "EVD-000002"

    def test_native_unmodified_on_disk(self, tmp_path: Path) -> None:
        """AC2: combine-evidence never mutates native evidence file."""
        native = _make_native_store(2)
        native_path = _write_store(tmp_path, "native.json", native)
        original_content = native_path.read_text()

        external = _make_external_store("sarif", 2)
        ext_path = _write_store(tmp_path, "ext.json", external)

        combine_evidence(native_path, [ext_path])

        assert native_path.read_text() == original_content

    def test_original_id_in_metadata(self, tmp_path: Path) -> None:
        """AC5: External original evidence IDs preserved in metadata."""
        native = _make_native_store(1)
        external = _make_external_store("sarif", 1, evidence_ids=["EXT-SARIF-000001"])
        native_path = _write_store(tmp_path, "native.json", native)
        ext_path = _write_store(tmp_path, "ext.json", external)

        result = combine_evidence(native_path, [ext_path])

        ext_item = result.combined.evidence[1]
        assert ext_item.metadata["intake"]["original_evidence_id"] == "EXT-SARIF-000001"
        assert ext_item.metadata["intake"]["combined_evidence_id"] == ext_item.evidence_id

    def test_deterministic_ordering(self, tmp_path: Path) -> None:
        """AC8: Same inputs in different filesystem order produce identical output."""
        native = _make_native_store(1)
        ext_a = _make_external_store("sarif", 1, summaries=["SARIF item"])
        ext_b = _make_external_store("semgrep", 1, summaries=["Semgrep item"])

        native_path = _write_store(tmp_path, "native.json", native)
        path_a = _write_store(tmp_path, "z-ext-a.json", ext_a)
        path_b = _write_store(tmp_path, "a-ext-b.json", ext_b)

        # Pass in reverse alphabetical order — combine sorts internally
        result1 = combine_evidence(native_path, [path_a, path_b])
        result2 = combine_evidence(native_path, [path_b, path_a])

        ids1 = [i.evidence_id for i in result1.combined.evidence]
        ids2 = [i.evidence_id for i in result2.combined.evidence]
        assert ids1 == ids2

    def test_semantic_dedup(self, tmp_path: Path) -> None:
        """AC7: Semantic duplicates skipped deterministically."""
        native = _make_native_store(1)

        # Two external stores with identical evidence
        ext1 = _make_external_store(
            "sarif", 1, summaries=["Same"], rule_ids=["R1"], locations=[("a.py", 10)]
        )
        ext2 = _make_external_store(
            "sarif", 1, summaries=["Same"], rule_ids=["R1"], locations=[("a.py", 10)]
        )

        native_path = _write_store(tmp_path, "native.json", native)
        ext1_path = _write_store(tmp_path, "ext1.json", ext1)
        ext2_path = _write_store(tmp_path, "ext2.json", ext2)

        result = combine_evidence(native_path, [ext1_path, ext2_path])
        assert result.duplicate_count == 1
        assert result.external_count == 2
        # Only 1 external item in combined (first kept, second deduped)
        assert len(result.combined.evidence) == 2  # 1 native + 1 external

    def test_no_dedup_when_disabled(self, tmp_path: Path) -> None:
        """Dedup can be disabled in policy."""
        native = _make_native_store(1)
        ext1 = _make_external_store(
            "sarif", 1, summaries=["Same"], rule_ids=["R1"], locations=[("a.py", 10)]
        )
        ext2 = _make_external_store(
            "sarif", 1, summaries=["Same"], rule_ids=["R1"], locations=[("a.py", 10)]
        )

        native_path = _write_store(tmp_path, "native.json", native)
        ext1_path = _write_store(tmp_path, "ext1.json", ext1)
        ext2_path = _write_store(tmp_path, "ext2.json", ext2)

        policy = IntakePolicy(deduplicate=False)
        result = combine_evidence(native_path, [ext1_path, ext2_path], policy=policy)
        assert result.duplicate_count == 0
        assert len(result.combined.evidence) == 3  # 1 native + 2 external

    def test_external_disabled_by_policy(self, tmp_path: Path) -> None:
        """Policy can disable external evidence entirely."""
        native = _make_native_store(2)
        external = _make_external_store("sarif", 5)

        native_path = _write_store(tmp_path, "native.json", native)
        ext_path = _write_store(tmp_path, "ext.json", external)

        policy = IntakePolicy(allow_external=False)
        result = combine_evidence(native_path, [ext_path], policy=policy)
        assert result.external_count == 0
        assert len(result.combined.evidence) == 2
        assert "disabled by intake policy" in result.warnings[0]

    def test_max_external_cap(self, tmp_path: Path) -> None:
        """Policy max_external_items cap enforced."""
        native = _make_native_store(1)
        external = _make_external_store("sarif", 10)

        native_path = _write_store(tmp_path, "native.json", native)
        ext_path = _write_store(tmp_path, "ext.json", external)

        policy = IntakePolicy(max_external_items=3)
        result = combine_evidence(native_path, [ext_path], policy=policy)
        assert result.native_count == 1
        # Only 3 external items imported
        imported = sum(1 for i in result.combined.evidence if i.source == "external_connector")
        assert imported == 3

    def test_missing_native_file(self, tmp_path: Path) -> None:
        """Missing native file produces empty native count."""
        missing = tmp_path / "nonexistent.json"
        result = combine_evidence(missing, [])
        assert result.ok is True
        assert result.native_count == 0
        assert len(result.combined.evidence) == 0

    def test_missing_external_file(self, tmp_path: Path) -> None:
        """Missing external file generates warning, continues."""
        native = _make_native_store(1)
        native_path = _write_store(tmp_path, "native.json", native)
        missing = tmp_path / "missing.json"

        result = combine_evidence(native_path, [missing])
        assert result.ok is True
        assert result.native_count == 1
        assert result.skipped_count == 1
        assert any("Could not load" in w for w in result.warnings)

    def test_all_combined_ids_unique(self, tmp_path: Path) -> None:
        """AC3: All evidence IDs in combined store are unique."""
        native = _make_native_store(5)
        ext1 = _make_external_store("sarif", 5, evidence_ids=["EXT-SARIF-000001"] * 5)
        ext2 = _make_external_store("semgrep", 5, evidence_ids=["EXT-SEM-000001"] * 5)

        native_path = _write_store(tmp_path, "native.json", native)
        ext1_path = _write_store(tmp_path, "ext1.json", ext1)
        ext2_path = _write_store(tmp_path, "ext2.json", ext2)

        policy = IntakePolicy(deduplicate=False)
        result = combine_evidence(native_path, [ext1_path, ext2_path], policy=policy)

        ids = [i.evidence_id for i in result.combined.evidence]
        assert len(ids) == len(set(ids))


# ---------------------------------------------------------------------------
# S04 — Manifest
# ---------------------------------------------------------------------------


class TestManifest:
    def test_manifest_records_sources(self, tmp_path: Path) -> None:
        """AC9: Manifest records source files, counts, duplicates, warnings."""
        native = _make_native_store(2)
        external = _make_external_store("sarif", 3)
        native_path = _write_store(tmp_path, "native.json", native)
        ext_path = _write_store(tmp_path, "ext.json", external)

        result = combine_evidence(native_path, [ext_path])
        m = result.manifest

        assert m.native is not None
        assert m.native.source_type == "native"
        assert m.native.imported_count == 2
        assert len(m.external_sources) == 1
        assert m.external_sources[0].source_type == "external"
        assert m.external_sources[0].imported_count == 3
        assert m.total_native == 2
        assert m.total_external == 3
        assert m.total_combined == 5
        assert m.deduplicated == 0
        assert m.schema_version == "1.0"

    def test_manifest_dedup_counts(self, tmp_path: Path) -> None:
        """Manifest records deduplicated count."""
        native = _make_native_store(1)
        ext1 = _make_external_store(
            "sarif", 1, summaries=["Same"], rule_ids=["R1"], locations=[("a.py", 10)]
        )
        ext2 = _make_external_store(
            "sarif", 1, summaries=["Same"], rule_ids=["R1"], locations=[("a.py", 10)]
        )

        native_path = _write_store(tmp_path, "native.json", native)
        ext1_path = _write_store(tmp_path, "ext1.json", ext1)
        ext2_path = _write_store(tmp_path, "ext2.json", ext2)

        result = combine_evidence(native_path, [ext1_path, ext2_path])
        m = result.manifest
        assert m.deduplicated == 1
        assert m.external_sources[0].duplicate_count == 0
        assert m.external_sources[1].duplicate_count == 1

    def test_manifest_warnings(self, tmp_path: Path) -> None:
        """Manifest records warnings."""
        native = _make_native_store(1)
        native_path = _write_store(tmp_path, "native.json", native)
        missing = tmp_path / "missing.json"

        result = combine_evidence(native_path, [missing])
        assert len(result.manifest.warnings) >= 1

    def test_manifest_serializable(self, tmp_path: Path) -> None:
        """Manifest can be serialized to JSON."""
        native = _make_native_store(1)
        native_path = _write_store(tmp_path, "native.json", native)

        result = combine_evidence(native_path, [])
        json_str = result.manifest.model_dump_json(indent=2)
        parsed = json.loads(json_str)
        assert parsed["schema_version"] == "1.0"
        assert parsed["total_native"] == 1


# ---------------------------------------------------------------------------
# S06 — Lineage Preservation
# ---------------------------------------------------------------------------


class TestLineagePreservation:
    def test_native_items_unchanged(self, tmp_path: Path) -> None:
        """Native items pass through completely unchanged."""
        native = _make_native_store(2)
        native_path = _write_store(tmp_path, "native.json", native)

        result = combine_evidence(native_path, [])
        for i, item in enumerate(result.combined.evidence):
            orig = native.evidence[i]
            assert item.evidence_id == orig.evidence_id
            assert item.source == orig.source
            assert item.type == orig.type
            assert item.summary == orig.summary
            assert "intake" not in item.metadata  # Native never gets intake metadata

    def test_external_provenance_survives(self, tmp_path: Path) -> None:
        """Connector provenance from v3.1.0 survives combination."""
        native = _make_native_store(1)
        ext = _make_external_store("sarif", 1)
        ext.evidence[0].metadata["connector_provenance"]["source_tool_name"] = "Semgrep"
        ext.evidence[0].metadata["confidence_reason"] = "location_rule_and_message_present"

        native_path = _write_store(tmp_path, "native.json", native)
        ext_path = _write_store(tmp_path, "ext.json", ext)

        result = combine_evidence(native_path, [ext_path])
        ext_item = result.combined.evidence[1]
        assert ext_item.metadata["connector_provenance"]["source_tool_name"] == "Semgrep"
        assert ext_item.metadata["confidence_reason"] == "location_rule_and_message_present"

    def test_confidence_survives(self, tmp_path: Path) -> None:
        """Confidence level from connector survives combination."""
        native = _make_native_store(1)
        ext = _make_external_store("sarif", 1)
        ext.evidence[0].confidence = "High"

        native_path = _write_store(tmp_path, "native.json", native)
        ext_path = _write_store(tmp_path, "ext.json", ext)

        result = combine_evidence(native_path, [ext_path])
        assert result.combined.evidence[1].confidence == "High"

    def test_intake_metadata_has_source_file(self, tmp_path: Path) -> None:
        """Intake metadata records source file path."""
        native = _make_native_store(1)
        ext = _make_external_store("sarif", 1)

        native_path = _write_store(tmp_path, "native.json", native)
        ext_path = _write_store(tmp_path, "my-evidence.json", ext)

        result = combine_evidence(native_path, [ext_path])
        ext_item = result.combined.evidence[1]
        assert "my-evidence.json" in ext_item.metadata["intake"]["source_file"]

    def test_deduplication_status_kept(self, tmp_path: Path) -> None:
        """Unique items get status 'renamed_for_uniqueness' (IDs are always namespaced)."""
        native = _make_native_store(1)
        ext = _make_external_store("sarif", 1)

        native_path = _write_store(tmp_path, "native.json", native)
        ext_path = _write_store(tmp_path, "ext.json", ext)

        result = combine_evidence(native_path, [ext_path])
        ext_item = result.combined.evidence[1]
        assert ext_item.metadata["intake"]["deduplication_status"] == "renamed_for_uniqueness"
        assert ext_item.metadata["intake"]["original_evidence_id"] != ext_item.evidence_id

    def test_deduplication_status_duplicate_skipped(self, tmp_path: Path) -> None:
        """Duplicate items are skipped entirely (not in combined store)."""
        native = _make_native_store(1)
        ext1 = _make_external_store(
            "sarif", 1, summaries=["Same"], rule_ids=["R1"], locations=[("a.py", 10)]
        )
        ext2 = _make_external_store(
            "sarif", 1, summaries=["Same"], rule_ids=["R1"], locations=[("a.py", 10)]
        )

        native_path = _write_store(tmp_path, "native.json", native)
        ext1_path = _write_store(tmp_path, "ext1.json", ext1)
        ext2_path = _write_store(tmp_path, "ext2.json", ext2)

        result = combine_evidence(native_path, [ext1_path, ext2_path])
        # Only 2 items: 1 native + 1 unique external
        assert len(result.combined.evidence) == 2
        # The first external item has status 'renamed_for_uniqueness'
        assert (
            result.combined.evidence[1].metadata["intake"]["deduplication_status"]
            == "renamed_for_uniqueness"
        )
        # The second was never added — duplicate_count tracks it
        assert result.duplicate_count == 1


# ---------------------------------------------------------------------------
# Negative: No DebtFinding creation
# ---------------------------------------------------------------------------


class TestNoDebtFinding:
    def test_combine_does_not_import_debt_finding(self, tmp_path: Path) -> None:
        """Combine never creates or references DebtFinding objects."""
        native = _make_native_store(1)
        ext = _make_external_store("sarif", 1)
        native_path = _write_store(tmp_path, "native.json", native)
        ext_path = _write_store(tmp_path, "ext.json", ext)

        result = combine_evidence(native_path, [ext_path])

        # All items are EvidenceItem instances, never DebtFinding
        for item in result.combined.evidence:
            assert hasattr(item, "evidence_id")
            assert hasattr(item, "source")
            assert not hasattr(item, "finding_id")
