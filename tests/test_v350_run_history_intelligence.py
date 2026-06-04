"""Regression tests for v3.5.0 Run History Intelligence.

Verifies:
- Enriched per-run snapshots are built and written correctly
- Run history index avoids self-ingestion
- Finding trend with complete/partial/insufficient_data status
- Risk trend with status
- Evidence coverage trend with limitation phrasing
- Work-package readiness trend
- Traceability trend surfacing
- Overall trajectory is conservative
- Structured warnings with codes
- Markdown report contains required sections
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pharabius.core.constants import EVIDENCE_SOURCE_FILE_SKIPPED
from pharabius.core.run_history import (
    _is_history_snapshot_file,
    _is_run_metadata_file,
    build_current_run_snapshot,
    build_run_history_index,
    build_run_history_summary,
    compute_evidence_coverage_trend,
    compute_finding_trend,
    compute_risk_trend,
    compute_work_package_readiness_trend,
    render_run_history_summary_markdown,
    write_run_history_index,
    write_run_history_snapshot,
    write_run_history_summary,
)


def _write_run_metadata(runs_dir: Path, run_id: str, timestamp: str, summary: dict) -> Path:
    """Helper: write a run metadata JSON file."""
    data = {
        "schema_version": "1.0",
        "run_id": run_id,
        "timestamp": timestamp,
        "repository": "/test",
        "commit": "abc123",
        "branch": "main",
        "tool_version": "3.5.0",
        "analysis_mode": "deterministic-no-ai",
        "commands_run": ["run"],
        "files_written": [],
        "limitations": [],
        "summary": summary,
    }
    path = runs_dir / f"{run_id}.json"
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return path


def _write_snapshot(runs_dir: Path, snapshot: dict) -> Path:
    """Helper: write an enriched history snapshot."""
    run_id = snapshot.get("run_id", "unknown")
    path = runs_dir / f"{run_id}-history-snapshot.json"
    path.write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")
    return path


def _make_workspace_with_findings(
    tmp_path: Path,
    findings: list[dict] | None = None,
    evidence_items: list[dict] | None = None,
) -> Path:
    """Create a minimal .ai-debt workspace with given findings and evidence."""
    workspace = tmp_path / ".ai-debt"
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "runs").mkdir(parents=True, exist_ok=True)
    (workspace / "traceability").mkdir(parents=True, exist_ok=True)

    # Debt register
    register = {
        "schema_version": "1.0",
        "findings": findings or [],
        "summary": {"total_findings": len(findings or [])},
    }
    (workspace / "debt-register.json").write_text(json.dumps(register, indent=2), encoding="utf-8")

    # Evidence
    ev = {"schema_version": "1.0", "evidence": evidence_items or []}
    (workspace / "evidence.json").write_text(json.dumps(ev, indent=2), encoding="utf-8")

    # Traceability quality
    tq = {"traceability_grade": "usable", "findings_with_evidence_pct": 80.0}
    (workspace / "traceability" / "traceability-quality.json").write_text(
        json.dumps(tq, indent=2), encoding="utf-8"
    )

    return workspace


# ── File discrimination ───────────────────────────────────────────────


class TestFileDiscrimination:
    def test_run_metadata_file_recognized(self):
        assert _is_run_metadata_file(Path("RUN-20260530-143000.json"))

    def test_snapshot_file_excluded(self):
        assert not _is_run_metadata_file(Path("RUN-20260530-143000-history-snapshot.json"))

    def test_index_file_excluded(self):
        assert not _is_run_metadata_file(Path("run-history-index.json"))

    def test_snapshot_file_recognized(self):
        assert _is_history_snapshot_file(Path("RUN-20260530-143000-history-snapshot.json"))

    def test_metadata_not_snapshot(self):
        assert not _is_history_snapshot_file(Path("RUN-20260530-143000.json"))


# ── S01: Enriched snapshot ────────────────────────────────────────────


class TestEnrichedSnapshot:
    def test_current_run_snapshot_written(self, tmp_path):
        workspace = _make_workspace_with_findings(tmp_path)
        snapshot = build_current_run_snapshot(workspace, "RUN-20260530-143000")
        path = write_run_history_snapshot(workspace, snapshot)
        assert path.exists()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["run_id"] == "RUN-20260530-143000"

    def test_snapshot_contains_required_fields(self, tmp_path):
        workspace = _make_workspace_with_findings(tmp_path)
        snapshot = build_current_run_snapshot(workspace, "RUN-20260530-143000")

        required_fields = [
            "schema_version",
            "run_id",
            "timestamp",
            "findings_by_category",
            "risk_by_category",
            "total_risk_score",
            "average_risk_score",
            "max_risk_score",
            "evidence_type_counts",
            "evidence_observation_strength_counts",
            "limitation_evidence_count",
            "findings_with_evidence_pct",
            "orphan_evidence_count",
            "orphan_finding_count",
            "broken_reference_count",
            "claim_count",
            "work_package_count",
            "traceability_grade",
        ]
        for field in required_fields:
            assert field in snapshot, f"Missing field: {field}"

    def test_snapshot_findings_by_category(self, tmp_path):
        findings = [
            {"id": "TD-CODE-001", "category": "TD-CODE", "risk_score": 15, "title": "t"},
            {"id": "TD-CODE-002", "category": "TD-CODE", "risk_score": 10, "title": "t"},
            {"id": "TD-DEP-001", "category": "TD-DEP", "risk_score": 8, "title": "t"},
        ]
        workspace = _make_workspace_with_findings(tmp_path, findings=findings)
        snapshot = build_current_run_snapshot(workspace, "RUN-001")

        assert snapshot["findings_by_category"] == {"TD-CODE": 2, "TD-DEP": 1}

    def test_snapshot_risk_by_category(self, tmp_path):
        findings = [
            {"id": "TD-CODE-001", "category": "TD-CODE", "risk_score": 15, "title": "t"},
            {"id": "TD-CODE-002", "category": "TD-CODE", "risk_score": 10, "title": "t"},
        ]
        workspace = _make_workspace_with_findings(tmp_path, findings=findings)
        snapshot = build_current_run_snapshot(workspace, "RUN-001")

        risk = snapshot["risk_by_category"]["TD-CODE"]
        assert risk["total_risk"] == 25
        assert risk["average_risk"] == 12.5
        assert risk["max_risk"] == 15

    def test_snapshot_evidence_type_counts(self, tmp_path):
        evidence = [
            {"evidence_id": "EVD-001", "type": "large_file_detected", "metadata": {}},
            {"evidence_id": "EVD-002", "type": "large_file_detected", "metadata": {}},
            {"evidence_id": "EVD-003", "type": "debt_marker_detected", "metadata": {}},
        ]
        workspace = _make_workspace_with_findings(tmp_path, evidence_items=evidence)
        snapshot = build_current_run_snapshot(workspace, "RUN-001")

        assert snapshot["evidence_type_counts"]["large_file_detected"] == 2
        assert snapshot["evidence_type_counts"]["debt_marker_detected"] == 1

    def test_snapshot_source_file_skipped_uses_type(self, tmp_path):
        evidence = [
            {
                "evidence_id": "EVD-001",
                "type": EVIDENCE_SOURCE_FILE_SKIPPED,
                "metadata": {"reason": "file_size_limit"},
            },
            {
                "evidence_id": "EVD-002",
                "type": EVIDENCE_SOURCE_FILE_SKIPPED,
                "metadata": {"reason": "file_size_limit"},
            },
        ]
        workspace = _make_workspace_with_findings(tmp_path, evidence_items=evidence)
        snapshot = build_current_run_snapshot(workspace, "RUN-001")

        assert snapshot["evidence_type_counts"][EVIDENCE_SOURCE_FILE_SKIPPED] == 2
        assert snapshot["source_file_skipped_by_reason"]["file_size_limit"] == 2


# ── S02: Run history index ────────────────────────────────────────────


class TestRunHistoryIndex:
    def test_run_history_index_created(self, tmp_path):
        workspace = _make_workspace_with_findings(tmp_path)
        _write_run_metadata(
            workspace / "runs",
            "RUN-001",
            "2026-05-29T12:00:00+00:00",
            {"finding_count": 10, "evidence_count": 50},
        )
        index = build_run_history_index(workspace)
        path = write_run_history_index(workspace, index)
        assert path.exists()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert len(data["runs"]) == 1

    def test_run_history_index_does_not_index_itself(self, tmp_path):
        workspace = _make_workspace_with_findings(tmp_path)
        _write_run_metadata(
            workspace / "runs",
            "RUN-001",
            "2026-05-29T12:00:00+00:00",
            {"finding_count": 10},
        )
        # Write a pre-existing index file
        (workspace / "runs" / "run-history-index.json").write_text(
            '{"test": true}', encoding="utf-8"
        )

        index = build_run_history_index(workspace)
        run_ids = [r["run_id"] for r in index["runs"]]
        assert "run-history-index" not in str(run_ids)
        assert len(index["runs"]) == 1

    def test_history_snapshot_not_treated_as_run_metadata(self, tmp_path):
        workspace = _make_workspace_with_findings(tmp_path)
        _write_run_metadata(
            workspace / "runs",
            "RUN-001",
            "2026-05-29T12:00:00+00:00",
            {"finding_count": 10},
        )
        # Write a snapshot file
        _write_snapshot(workspace / "runs", {"run_id": "RUN-001", "schema_version": "1.0"})

        index = build_run_history_index(workspace)
        # Should have exactly 1 run entry (the metadata, not the snapshot)
        assert len(index["runs"]) == 1
        assert index["runs"][0]["enriched"] is True

    def test_old_run_without_snapshot_marked_not_enriched(self, tmp_path):
        workspace = _make_workspace_with_findings(tmp_path)
        _write_run_metadata(
            workspace / "runs",
            "RUN-001",
            "2026-05-29T12:00:00+00:00",
            {"finding_count": 10},
        )
        # No snapshot file

        index = build_run_history_index(workspace)
        assert index["runs"][0]["enriched"] is False

    def test_malformed_run_skipped_with_warning(self, tmp_path):
        workspace = _make_workspace_with_findings(tmp_path)
        # Write malformed file
        (workspace / "runs" / "RUN-BAD.json").write_text("not json{{{", encoding="utf-8")

        index = build_run_history_index(workspace)
        assert len(index["runs"]) == 0
        assert len(index["warnings"]) >= 1
        assert index["warnings"][0]["code"] == "malformed_run_metadata"


# ── S03: Finding trend ────────────────────────────────────────────────


class TestFindingTrend:
    def test_first_run_insufficient_data(self, tmp_path):
        workspace = _make_workspace_with_findings(tmp_path)
        _write_run_metadata(
            workspace / "runs",
            "RUN-001",
            "2026-05-29T12:00:00+00:00",
            {"finding_count": 10},
        )
        index = build_run_history_index(workspace)
        trend = compute_finding_trend(index)
        assert trend["status"] == "insufficient_data"

    def test_finding_trend_partial_without_prior_snapshot(self, tmp_path):
        workspace = _make_workspace_with_findings(tmp_path)
        _write_run_metadata(
            workspace / "runs",
            "RUN-001",
            "2026-05-29T12:00:00+00:00",
            {"finding_count": 10},
        )
        _write_run_metadata(
            workspace / "runs",
            "RUN-002",
            "2026-05-30T12:00:00+00:00",
            {"finding_count": 8},
        )
        # Only second run has snapshot
        _write_snapshot(
            workspace / "runs",
            {
                "run_id": "RUN-002",
                "schema_version": "1.0",
                "findings_by_category": {"TD-CODE": 5, "TD-DEP": 3},
            },
        )

        index = build_run_history_index(workspace)
        trend = compute_finding_trend(index)
        assert trend["status"] == "partial"
        assert trend["total_delta"] == -2
        assert trend["by_category"] is None

    def test_finding_trend_complete_with_two_snapshots(self, tmp_path):
        workspace = _make_workspace_with_findings(tmp_path)
        _write_run_metadata(
            workspace / "runs",
            "RUN-001",
            "2026-05-29T12:00:00+00:00",
            {"finding_count": 10},
        )
        _write_snapshot(
            workspace / "runs",
            {
                "run_id": "RUN-001",
                "schema_version": "1.0",
                "findings_by_category": {"TD-CODE": 8, "TD-DEP": 2},
            },
        )
        _write_run_metadata(
            workspace / "runs",
            "RUN-002",
            "2026-05-30T12:00:00+00:00",
            {"finding_count": 9},
        )
        _write_snapshot(
            workspace / "runs",
            {
                "run_id": "RUN-002",
                "schema_version": "1.0",
                "findings_by_category": {"TD-CODE": 6, "TD-DEP": 3},
            },
        )

        index = build_run_history_index(workspace)
        trend = compute_finding_trend(index)
        assert trend["status"] == "complete"
        assert trend["total_delta"] == -1
        assert trend["by_category"]["TD-CODE"]["delta"] == -2
        assert trend["by_category"]["TD-DEP"]["delta"] == 1

    def test_new_category_tracked_as_added(self, tmp_path):
        workspace = _make_workspace_with_findings(tmp_path)
        _write_run_metadata(
            workspace / "runs",
            "RUN-001",
            "2026-05-29T12:00:00+00:00",
            {"finding_count": 5},
        )
        _write_snapshot(
            workspace / "runs",
            {
                "run_id": "RUN-001",
                "schema_version": "1.0",
                "findings_by_category": {"TD-CODE": 5},
            },
        )
        _write_run_metadata(
            workspace / "runs",
            "RUN-002",
            "2026-05-30T12:00:00+00:00",
            {"finding_count": 7},
        )
        _write_snapshot(
            workspace / "runs",
            {
                "run_id": "RUN-002",
                "schema_version": "1.0",
                "findings_by_category": {"TD-CODE": 5, "TD-DEP": 2},
            },
        )

        index = build_run_history_index(workspace)
        trend = compute_finding_trend(index)
        assert "TD-DEP" in trend["added_categories"]

    def test_removed_category_tracked_as_zero(self, tmp_path):
        workspace = _make_workspace_with_findings(tmp_path)
        _write_run_metadata(
            workspace / "runs",
            "RUN-001",
            "2026-05-29T12:00:00+00:00",
            {"finding_count": 5},
        )
        _write_snapshot(
            workspace / "runs",
            {
                "run_id": "RUN-001",
                "schema_version": "1.0",
                "findings_by_category": {"TD-CODE": 3, "TD-DEP": 2},
            },
        )
        _write_run_metadata(
            workspace / "runs",
            "RUN-002",
            "2026-05-30T12:00:00+00:00",
            {"finding_count": 3},
        )
        _write_snapshot(
            workspace / "runs",
            {
                "run_id": "RUN-002",
                "schema_version": "1.0",
                "findings_by_category": {"TD-CODE": 3},
            },
        )

        index = build_run_history_index(workspace)
        trend = compute_finding_trend(index)
        assert "TD-DEP" in trend["removed_categories"]
        assert trend["by_category"]["TD-DEP"]["latest"] == 0


# ── S04: Risk trend ───────────────────────────────────────────────────


class TestRiskTrend:
    def test_risk_trend_insufficient_data(self, tmp_path):
        workspace = _make_workspace_with_findings(tmp_path)
        _write_run_metadata(
            workspace / "runs",
            "RUN-001",
            "2026-05-29T12:00:00+00:00",
            {"finding_count": 10},
        )
        index = build_run_history_index(workspace)
        trend = compute_risk_trend(index)
        assert trend["status"] == "insufficient_data"

    def test_risk_trend_with_two_enriched_runs(self, tmp_path):
        workspace = _make_workspace_with_findings(tmp_path)
        _write_run_metadata(
            workspace / "runs",
            "RUN-001",
            "2026-05-29T12:00:00+00:00",
            {"finding_count": 10},
        )
        _write_snapshot(
            workspace / "runs",
            {
                "run_id": "RUN-001",
                "schema_version": "1.0",
                "total_risk_score": 100,
            },
        )
        _write_run_metadata(
            workspace / "runs",
            "RUN-002",
            "2026-05-30T12:00:00+00:00",
            {"finding_count": 8},
        )
        _write_snapshot(
            workspace / "runs",
            {
                "run_id": "RUN-002",
                "schema_version": "1.0",
                "total_risk_score": 80,
            },
        )

        index = build_run_history_index(workspace)
        trend = compute_risk_trend(index)
        assert trend["status"] == "complete"
        assert trend["total_risk_delta"] == -20
        assert trend["trajectory"] == "improving"


# ── S05: Evidence coverage trend ───────────────────────────────────────


class TestEvidenceCoverageTrend:
    def test_evidence_coverage_trend_insufficient_data(self, tmp_path):
        workspace = _make_workspace_with_findings(tmp_path)
        _write_run_metadata(
            workspace / "runs",
            "RUN-001",
            "2026-05-29T12:00:00+00:00",
            {"finding_count": 10},
        )
        index = build_run_history_index(workspace)
        trend = compute_evidence_coverage_trend(index)
        assert trend["status"] == "insufficient_data"

    def test_evidence_coverage_trend_complete(self):
        index = {
            "runs": [
                {"run_id": "RUN-001", "enriched": True},
                {"run_id": "RUN-002", "enriched": True},
            ]
        }
        prev = {
            "evidence_type_counts": {"large_file_detected": 3, EVIDENCE_SOURCE_FILE_SKIPPED: 1},
            "limitation_evidence_count": 2,
            "findings_with_evidence_pct": 70.0,
            "orphan_evidence_count": 5,
            "orphan_finding_count": 2,
            "broken_reference_count": 1,
        }
        latest = {
            "evidence_type_counts": {"large_file_detected": 5, EVIDENCE_SOURCE_FILE_SKIPPED: 2},
            "limitation_evidence_count": 4,
            "findings_with_evidence_pct": 80.0,
            "orphan_evidence_count": 3,
            "orphan_finding_count": 1,
            "broken_reference_count": 0,
        }
        trend = compute_evidence_coverage_trend(index, latest, prev)
        assert trend["status"] == "complete"
        assert trend["findings_with_evidence_pct_delta"] == 10.0
        assert trend["orphan_evidence_count_delta"] == -2
        assert trend["broken_reference_count_delta"] == -1

    def test_limitation_evidence_trend(self):
        index = {
            "runs": [
                {"run_id": "RUN-001", "enriched": True},
                {"run_id": "RUN-002", "enriched": True},
            ]
        }
        prev = {
            "limitation_evidence_count": 2,
            "findings_with_evidence_pct": 70.0,
            "orphan_evidence_count": 0,
            "orphan_finding_count": 0,
            "broken_reference_count": 0,
            "evidence_type_counts": {},
        }
        latest = {
            "limitation_evidence_count": 5,
            "findings_with_evidence_pct": 75.0,
            "orphan_evidence_count": 0,
            "orphan_finding_count": 0,
            "broken_reference_count": 0,
            "evidence_type_counts": {},
        }
        trend = compute_evidence_coverage_trend(index, latest, prev)
        assert trend["limitation_evidence_count_delta"] == 3


# ── S06: Work-package readiness trend ─────────────────────────────────


class TestWorkPackageReadinessTrend:
    def test_wp_trend_insufficient_data(self, tmp_path):
        workspace = _make_workspace_with_findings(tmp_path)
        _write_run_metadata(
            workspace / "runs",
            "RUN-001",
            "2026-05-29T12:00:00+00:00",
            {"finding_count": 10, "work_package_count": 3},
        )
        index = build_run_history_index(workspace)
        trend = compute_work_package_readiness_trend(index)
        assert trend["status"] == "insufficient_data"

    def test_wp_trend_complete(self):
        index = {
            "runs": [
                {"run_id": "RUN-001", "enriched": True, "work_package_count": 5},
                {"run_id": "RUN-002", "enriched": True, "work_package_count": 4},
            ]
        }
        prev = {"grouping_ratio": 2.0, "work_packages_with_linked_findings_pct": 80.0}
        latest = {
            "grouping_ratio": 2.5,
            "work_packages_with_linked_findings_pct": 100.0,
            "work_packages_with_verification_steps_pct": 75.0,
        }
        trend = compute_work_package_readiness_trend(index, latest, prev)
        assert trend["status"] == "complete"
        assert trend["work_package_count_delta"] == -1
        assert trend["trajectory"] == "improving"


# ── S08: Summary ──────────────────────────────────────────────────────


class TestRunHistorySummary:
    def test_summary_first_run_insufficient_data(self, tmp_path):
        workspace = _make_workspace_with_findings(tmp_path)
        _write_run_metadata(
            workspace / "runs",
            "RUN-001",
            "2026-05-29T12:00:00+00:00",
            {"finding_count": 10},
        )
        summary = build_run_history_summary(workspace)
        assert summary["confidence"] == "insufficient"
        assert summary["overall_trajectory"] == "insufficient_data"

    def test_overall_trajectory_worsening_on_broken_refs(self):
        """Conservative worsening when broken references increase."""
        # This tests the trajectory computation directly
        runs = [
            {"run_id": "RUN-001", "enriched": True, "finding_count": 10},
            {"run_id": "RUN-002", "enriched": True, "finding_count": 10},
        ]
        prev = {
            "broken_reference_count": 0,
            "total_risk_score": 50,
            "findings_with_evidence_pct": 80.0,
        }
        latest = {
            "broken_reference_count": 3,
            "total_risk_score": 40,
            "findings_with_evidence_pct": 90.0,
        }

        from pharabius.core.run_history import _compute_overall_trajectory

        result = _compute_overall_trajectory(runs, latest, prev, {})
        assert result == "worsening"

    def test_overall_trajectory_improving_on_lower_risk(self):
        runs = [
            {"run_id": "RUN-001", "enriched": True, "finding_count": 10},
            {"run_id": "RUN-002", "enriched": True, "finding_count": 8},
        ]
        prev = {
            "broken_reference_count": 0,
            "total_risk_score": 50,
            "findings_with_evidence_pct": 80.0,
        }
        latest = {
            "broken_reference_count": 0,
            "total_risk_score": 30,
            "findings_with_evidence_pct": 85.0,
        }

        from pharabius.core.run_history import _compute_overall_trajectory

        result = _compute_overall_trajectory(runs, latest, prev, {})
        assert result == "improving"

    def test_summary_marks_partial_historical_data(self, tmp_path):
        workspace = _make_workspace_with_findings(tmp_path)
        _write_run_metadata(
            workspace / "runs",
            "RUN-001",
            "2026-05-29T12:00:00+00:00",
            {"finding_count": 10},
        )
        # Second run with snapshot
        _write_run_metadata(
            workspace / "runs",
            "RUN-002",
            "2026-05-30T12:00:00+00:00",
            {"finding_count": 8},
        )
        _write_snapshot(
            workspace / "runs",
            {
                "run_id": "RUN-002",
                "schema_version": "1.0",
                "findings_by_category": {"TD-CODE": 8},
                "total_risk_score": 50,
                "traceability_grade": "usable",
                "claim_count": 5,
                "limitation_evidence_count": 2,
            },
        )

        summary = build_run_history_summary(workspace)
        assert summary["confidence"] == "partial"
        assert summary["finding_trend"]["status"] == "partial"

    def test_warning_schema_structured(self, tmp_path):
        workspace = _make_workspace_with_findings(tmp_path)
        # Write malformed file
        (workspace / "runs").mkdir(parents=True, exist_ok=True)
        (workspace / "runs" / "RUN-BAD.json").write_text("not json{{{", encoding="utf-8")

        index = build_run_history_index(workspace)
        if index["warnings"]:
            w = index["warnings"][0]
            assert "code" in w
            assert "message" in w
            assert w["code"] == "malformed_run_metadata"

    def test_summary_json_and_md_written(self, tmp_path):
        workspace = _make_workspace_with_findings(tmp_path)
        _write_run_metadata(
            workspace / "runs",
            "RUN-001",
            "2026-05-29T12:00:00+00:00",
            {"finding_count": 10},
        )
        summary = build_run_history_summary(workspace)
        paths = write_run_history_summary(workspace, summary)

        json_path = workspace / "reports" / "run-history-summary.json"
        md_path = workspace / "reports" / "run-history-summary.md"
        assert json_path.exists()
        assert md_path.exists()
        assert len(paths) == 2

    def test_markdown_contains_required_sections(self, tmp_path):
        workspace = _make_workspace_with_findings(tmp_path)
        _write_run_metadata(
            workspace / "runs",
            "RUN-001",
            "2026-05-29T12:00:00+00:00",
            {"finding_count": 10},
        )
        _write_snapshot(
            workspace / "runs",
            {
                "run_id": "RUN-001",
                "schema_version": "1.0",
                "findings_by_category": {"TD-CODE": 10},
                "total_risk_score": 50,
            },
        )

        summary = build_run_history_summary(workspace)
        md = render_run_history_summary_markdown(summary)

        required_sections = [
            "# Run History Summary",
            "## Overall trajectory",
            "## Finding trend",
            "## Risk trend",
            "## Evidence coverage trend",
            "## Work-package readiness trend",
            "## Traceability trend",
        ]
        for section in required_sections:
            assert section in md, f"Missing section: {section}"


# ── Traceability trend ────────────────────────────────────────────────


class TestTraceabilityTrend:
    def test_traceability_trend_in_summary(self, tmp_path):
        workspace = _make_workspace_with_findings(tmp_path)
        _write_run_metadata(
            workspace / "runs",
            "RUN-001",
            "2026-05-29T12:00:00+00:00",
            {"finding_count": 10},
        )
        # Write traceability trend
        trend_data = {
            "trajectory": "improving",
            "snapshot_count": 1,
            "baseline_grade": "partial",
            "latest_grade": "usable",
            "deltas": {},
            "warnings": [],
        }
        (workspace / "traceability" / "traceability-quality-trend.json").write_text(
            json.dumps(trend_data, indent=2), encoding="utf-8"
        )

        summary = build_run_history_summary(workspace)
        assert summary["traceability_trend"]["trajectory"] == "improving"
