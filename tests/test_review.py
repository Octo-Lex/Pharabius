"""Tests for v1.4.0 Review Decision Sidecar."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from pharabius.core.review import (
    format_summary_text,
    init_review_sidecar,
    load_decisions,
    summarize_decisions,
    validate_decisions,
)
from pharabius.schemas.review import (
    _VALID_STATUSES,
    DecisionStatus,
    ReviewDecision,
    ReviewDecisions,
    ReviewSummary,
)

# ── Fixtures ──────────────────────────────────────────────────────────


def _make_workspace(tmp_path: Path, findings: list[dict] | None = None) -> Path:
    """Create a minimal .ai-debt workspace with optional debt-register."""
    ai_debt = tmp_path / ".ai-debt"
    ai_debt.mkdir()
    if findings is not None:
        register = {
            "schema_version": "1.0",
            "findings": findings,
        }
        (ai_debt / "debt-register.json").write_text(json.dumps(register), encoding="utf-8")
    return tmp_path


def _sample_findings() -> list[dict]:
    return [
        {
            "id": "TD-DEP-001",
            "category": "TD-DEP",
            "title": "Missing lockfile",
            "severity": "Medium",
            "priority": "Medium",
            "evidence_ids": ["EVD-001"],
        },
        {
            "id": "TD-PROCESS-001",
            "category": "TD-PROCESS",
            "title": "Missing process artifacts",
            "severity": "Low",
            "priority": "Low",
            "evidence_ids": ["EVD-002"],
        },
    ]


def _make_decision(
    finding_id: str = "TD-DEP-001",
    status: str = "accepted",
    reviewer: str = "platform-team",
) -> dict:
    return {
        "finding_id": finding_id,
        "status": status,
        "reviewed_at": "2026-05-20T12:00:00Z",
        "reviewer": reviewer,
        "rationale": "Required for reproducibility.",
        "ticket_url": "",
        "owner_area": "platform",
        "target_release": "",
        "notes": "",
    }


# ── Schema tests ──────────────────────────────────────────────────────


class TestReviewDecisionSchema:
    def test_valid_decision(self) -> None:
        d = ReviewDecision(
            finding_id="TD-DEP-001",
            status=DecisionStatus.ACCEPTED,
            reviewed_at=datetime(2026, 5, 20, 12, 0, tzinfo=UTC),
        )
        assert d.finding_id == "TD-DEP-001"
        assert d.status == DecisionStatus.ACCEPTED

    @pytest.mark.parametrize(
        "status",
        [
            "accepted",
            "rejected",
            "deferred",
            "needs-investigation",
            "duplicate",
            "already-fixed",
            "risk-accepted",
        ],
    )
    def test_all_statuses_accepted(self, status: str) -> None:
        d = ReviewDecision(
            finding_id="TD-001",
            status=DecisionStatus(status),
            reviewed_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
        assert d.status.value == status

    def test_invalid_status_rejected(self) -> None:
        with pytest.raises(ValueError):
            ReviewDecision(
                finding_id="TD-001",
                status="not-a-status",  # type: ignore[arg-type]
                reviewed_at=datetime(2026, 1, 1, tzinfo=UTC),
            )

    def test_empty_finding_id_rejected(self) -> None:
        with pytest.raises(ValueError):
            ReviewDecision(
                finding_id="  ",
                status=DecisionStatus.ACCEPTED,
                reviewed_at=datetime(2026, 1, 1, tzinfo=UTC),
            )

    def test_optional_fields_default_empty(self) -> None:
        d = ReviewDecision(
            finding_id="TD-001",
            status=DecisionStatus.DEFERRED,
            reviewed_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
        assert d.reviewer == ""
        assert d.rationale == ""
        assert d.ticket_url == ""
        assert d.owner_area == ""
        assert d.target_release == ""
        assert d.notes == ""

    def test_extra_fields_rejected(self) -> None:
        with pytest.raises(ValueError):
            ReviewDecision(
                finding_id="TD-001",
                status=DecisionStatus.ACCEPTED,
                reviewed_at=datetime(2026, 1, 1, tzinfo=UTC),
                unknown_field="oops",  # type: ignore[call-arg]
            )

    def test_valid_statuses_count(self) -> None:
        assert len(_VALID_STATUSES) == 7


class TestReviewDecisionsSchema:
    def test_empty_decisions(self) -> None:
        rd = ReviewDecisions()
        assert rd.schema_version == "1.0"
        assert rd.generated_by == "pharabius"
        assert rd.decisions == []

    def test_with_decisions(self) -> None:
        d = ReviewDecision(
            finding_id="TD-001",
            status=DecisionStatus.ACCEPTED,
            reviewed_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
        rd = ReviewDecisions(decisions=[d])
        assert len(rd.decisions) == 1

    def test_extra_fields_ignored(self) -> None:
        rd = ReviewDecisions(unknown_key="value")
        assert rd.schema_version == "1.0"


# ── Init tests ────────────────────────────────────────────────────────


class TestInitReviewSidecar:
    def test_creates_empty_sidecar(self, tmp_path: Path) -> None:
        root = _make_workspace(tmp_path, _sample_findings())
        path = init_review_sidecar(root)

        assert path.exists()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["schema_version"] == "1.0"
        assert data["generated_by"] == "pharabius"
        assert data["decisions"] == []

    def test_refuses_overwrite(self, tmp_path: Path) -> None:
        root = _make_workspace(tmp_path, _sample_findings())
        init_review_sidecar(root)

        with pytest.raises(FileExistsError):
            init_review_sidecar(root)

    def test_creates_review_directory(self, tmp_path: Path) -> None:
        root = _make_workspace(tmp_path, _sample_findings())
        review_dir = root / ".ai-debt" / "review"
        assert not review_dir.exists()

        init_review_sidecar(root)
        assert review_dir.exists()


# ── Load tests ────────────────────────────────────────────────────────


class TestLoadDecisions:
    def test_load_valid(self, tmp_path: Path) -> None:
        root = _make_workspace(tmp_path, _sample_findings())
        init_review_sidecar(root)
        rd = load_decisions(root)
        assert rd is not None
        assert rd.decisions == []

    def test_load_returns_none_if_missing(self, tmp_path: Path) -> None:
        root = _make_workspace(tmp_path)
        rd = load_decisions(root)
        assert rd is None

    def test_load_malformed_json(self, tmp_path: Path) -> None:
        root = _make_workspace(tmp_path)
        review_dir = root / ".ai-debt" / "review"
        review_dir.mkdir(parents=True)
        (review_dir / "decisions.json").write_text("not json{{{", encoding="utf-8")

        with pytest.raises(ValueError, match="Malformed"):
            load_decisions(root)


# ── Validate tests ────────────────────────────────────────────────────


class TestValidateDecisions:
    def test_empty_decisions_valid(self, tmp_path: Path) -> None:
        root = _make_workspace(tmp_path, _sample_findings())
        init_review_sidecar(root)

        result = validate_decisions(root)
        assert result.valid
        assert result.total_decisions == 0
        assert result.undecided_finding_ids == ["TD-DEP-001", "TD-PROCESS-001"]

    def test_valid_decision(self, tmp_path: Path) -> None:
        root = _make_workspace(tmp_path, _sample_findings())
        init_review_sidecar(root)

        # Add a decision
        path = root / ".ai-debt" / "review" / "decisions.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["decisions"].append(_make_decision())
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

        result = validate_decisions(root)
        assert result.valid
        assert result.total_decisions == 1
        assert "TD-DEP-001" not in result.undecided_finding_ids

    def test_unknown_finding_id_warning(self, tmp_path: Path) -> None:
        root = _make_workspace(tmp_path, _sample_findings())
        init_review_sidecar(root)

        path = root / ".ai-debt" / "review" / "decisions.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["decisions"].append(_make_decision(finding_id="TD-FAKE-999"))
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

        result = validate_decisions(root)
        # Unknown finding is a warning, not an error
        assert result.valid
        assert "TD-FAKE-999" in result.unknown_finding_ids

    def test_duplicate_finding_id_warning(self, tmp_path: Path) -> None:
        root = _make_workspace(tmp_path, _sample_findings())
        init_review_sidecar(root)

        path = root / ".ai-debt" / "review" / "decisions.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["decisions"].append(_make_decision())
        data["decisions"].append(_make_decision(status="rejected", reviewer="other-team"))
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

        result = validate_decisions(root)
        # Duplicate is a warning, not an error
        assert result.valid
        assert "TD-DEP-001" in result.duplicate_finding_ids

    def test_invalid_status_error(self, tmp_path: Path) -> None:
        root = _make_workspace(tmp_path, _sample_findings())
        init_review_sidecar(root)

        path = root / ".ai-debt" / "review" / "decisions.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["decisions"].append(
            {
                "finding_id": "TD-DEP-001",
                "status": "invalid-status",
                "reviewed_at": "2026-05-20T12:00:00Z",
            }
        )
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

        result = validate_decisions(root)
        assert not result.valid
        assert any(n.level == "error" for n in result.notices)

    def test_missing_debt_register(self, tmp_path: Path) -> None:
        root = _make_workspace(tmp_path)  # no findings
        init_review_sidecar(root)

        result = validate_decisions(root)
        assert not result.valid
        assert any("debt-register" in n.message for n in result.notices)

    def test_missing_sidecar(self, tmp_path: Path) -> None:
        root = _make_workspace(tmp_path, _sample_findings())
        # Don't init review sidecar

        result = validate_decisions(root)
        assert not result.valid
        assert any("not found" in n.message for n in result.notices)

    def test_malformed_sidecar(self, tmp_path: Path) -> None:
        root = _make_workspace(tmp_path, _sample_findings())
        review_dir = root / ".ai-debt" / "review"
        review_dir.mkdir(parents=True)
        (review_dir / "decisions.json").write_text("bad json{{{", encoding="utf-8")

        result = validate_decisions(root)
        assert not result.valid

    def test_stale_detection(self, tmp_path: Path) -> None:
        root = _make_workspace(tmp_path, _sample_findings())
        init_review_sidecar(root)

        path = root / ".ai-debt" / "review" / "decisions.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["decisions"].append(_make_decision(finding_id="TD-REMOVED-001"))
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

        result = validate_decisions(root)
        assert "TD-REMOVED-001" in result.stale_finding_ids

    def test_status_counts(self, tmp_path: Path) -> None:
        root = _make_workspace(tmp_path, _sample_findings())
        init_review_sidecar(root)

        path = root / ".ai-debt" / "review" / "decisions.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["decisions"].append(_make_decision(finding_id="TD-DEP-001", status="accepted"))
        data["decisions"].append(_make_decision(finding_id="TD-PROCESS-001", status="deferred"))
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

        result = validate_decisions(root)
        assert result.status_counts.get("accepted") == 1
        assert result.status_counts.get("deferred") == 1

    def test_canonical_hash_unchanged(self, tmp_path: Path) -> None:
        root = _make_workspace(tmp_path, _sample_findings())
        register_path = root / ".ai-debt" / "debt-register.json"
        hash_before = hashlib.sha256(register_path.read_bytes()).hexdigest()

        init_review_sidecar(root)

        # Add a decision
        path = root / ".ai-debt" / "review" / "decisions.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["decisions"].append(_make_decision())
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

        # Validate
        validate_decisions(root)

        hash_after = hashlib.sha256(register_path.read_bytes()).hexdigest()
        assert hash_before == hash_after


# ── Summarize tests ───────────────────────────────────────────────────


class TestSummarizeDecisions:
    def test_no_sidecar(self, tmp_path: Path) -> None:
        root = _make_workspace(tmp_path, _sample_findings())
        summary = summarize_decisions(root)
        assert summary.total_findings == 2
        assert summary.decisions_recorded == 0
        assert summary.undecided_count == 2
        assert any("not found" in w.lower() or "no review" in w.lower() for w in summary.warnings)

    def test_empty_decisions(self, tmp_path: Path) -> None:
        root = _make_workspace(tmp_path, _sample_findings())
        init_review_sidecar(root)

        summary = summarize_decisions(root)
        assert summary.total_findings == 2
        assert summary.decisions_recorded == 0
        assert summary.undecided_count == 2
        assert "TD-DEP-001" in summary.undecided_findings
        assert "TD-PROCESS-001" in summary.undecided_findings

    def test_with_decisions(self, tmp_path: Path) -> None:
        root = _make_workspace(tmp_path, _sample_findings())
        init_review_sidecar(root)

        path = root / ".ai-debt" / "review" / "decisions.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["decisions"].append(_make_decision())
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

        summary = summarize_decisions(root)
        assert summary.decisions_recorded == 1
        assert summary.undecided_count == 1
        assert summary.status_counts.get("accepted") == 1

    def test_stale_in_summary(self, tmp_path: Path) -> None:
        root = _make_workspace(tmp_path, _sample_findings())
        init_review_sidecar(root)

        path = root / ".ai-debt" / "review" / "decisions.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["decisions"].append(_make_decision(finding_id="TD-REMOVED-001"))
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

        summary = summarize_decisions(root)
        assert "TD-REMOVED-001" in summary.stale_decisions

    def test_duplicate_first_kept(self, tmp_path: Path) -> None:
        root = _make_workspace(tmp_path, _sample_findings())
        init_review_sidecar(root)

        path = root / ".ai-debt" / "review" / "decisions.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["decisions"].append(_make_decision(status="accepted", reviewer="team-a"))
        data["decisions"].append(_make_decision(status="rejected", reviewer="team-b"))
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

        summary = summarize_decisions(root)
        # First kept
        assert len(summary.decided_findings) == 1
        assert summary.decided_findings[0]["status"] == "accepted"
        assert summary.decided_findings[0]["reviewer"] == "team-a"


class TestFormatSummaryText:
    def test_basic_format(self) -> None:
        summary = ReviewSummary(
            total_findings=3,
            decisions_recorded=1,
            undecided_count=2,
            status_counts={"accepted": 1},
            decided_findings=[
                {
                    "finding_id": "TD-DEP-001",
                    "status": "accepted",
                    "reviewer": "platform",
                    "reviewed_at": "2026-05-20T12:00:00Z",
                }
            ],
            undecided_findings=["TD-PROCESS-001", "TD-SEC-001"],
        )
        text = format_summary_text(summary)
        assert "Total findings:  3" in text
        assert "Decisions recorded: 1" in text
        assert "TD-DEP-001: accepted" in text
        assert "TD-PROCESS-001" in text

    def test_empty_decisions_format(self) -> None:
        summary = ReviewSummary(total_findings=2, undecided_count=2)
        text = format_summary_text(summary)
        assert "Decisions recorded: 0" in text


# ── Import contract test ──────────────────────────────────────────────


class TestImportContract:
    def test_core_imports_schemas_only(self) -> None:
        """core/review.py should only import from schemas, not cli or ai."""
        import inspect

        import pharabius.core.review as mod

        src = inspect.getsource(mod)
        # Should not import from cli or ai packages
        assert "from pharabius.cli" not in src
        assert "from pharabius.ai" not in src
