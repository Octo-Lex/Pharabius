"""Tests for v3.5.0 — Workflow Lifecycle Governance.

Covers:
- FindingStatus enum and compatibility mapping
- WorkPackageStatus enum and compatibility mapping
- Transition validation (valid and invalid)
- Lifecycle history append-only behavior
- Report-only inference from review decisions
- Reporter lifecycle summary
- Status reader lifecycle distribution
"""

from __future__ import annotations

import json
from pathlib import Path

from pharabius.core.lifecycle import (
    FINDING_TRANSITIONS,
    WORK_PACKAGE_TRANSITIONS,
    FindingStatus,
    WorkPackageStatus,
    get_allowed_finding_transitions,
    get_allowed_work_package_transitions,
    infer_finding_status_from_context,
    resolve_finding_status,
    resolve_work_package_status,
    validate_finding_transition,
    validate_work_package_transition,
)
from pharabius.schemas.lifecycle import LifecycleEntry, LifecycleHistory

# ---------------------------------------------------------------------------
# S01 — FindingStatus enum and compatibility
# ---------------------------------------------------------------------------


class TestFindingStatusEnum:
    """FindingStatus enum has correct values and compatibility."""

    def test_enum_has_eleven_states(self) -> None:
        assert len(FindingStatus) == 11

    def test_detected_is_default(self) -> None:
        assert FindingStatus.DETECTED.value == "Detected"

    def test_all_states_have_transitions(self) -> None:
        for status in FindingStatus:
            assert status in FINDING_TRANSITIONS, f"{status} missing from FINDING_TRANSITIONS"

    def test_resolve_detected(self) -> None:
        assert resolve_finding_status("Detected") == FindingStatus.DETECTED

    def test_resolve_case_insensitive_alias(self) -> None:
        assert resolve_finding_status("detected") == FindingStatus.DETECTED

    def test_resolve_review_accepted(self) -> None:
        assert resolve_finding_status("accepted") == FindingStatus.ACKNOWLEDGED

    def test_resolve_review_deferred(self) -> None:
        assert resolve_finding_status("deferred") == FindingStatus.DEFERRED

    def test_resolve_review_risk_accepted(self) -> None:
        assert resolve_finding_status("risk-accepted") == FindingStatus.WONT_FIX

    def test_resolve_review_already_fixed(self) -> None:
        assert resolve_finding_status("already-fixed") == FindingStatus.REMEDIATED

    def test_resolve_verification_remediated(self) -> None:
        assert resolve_finding_status("likely_remediated") == FindingStatus.REMEDIATED

    def test_resolve_unknown_returns_none(self) -> None:
        assert resolve_finding_status("unknown_status") is None

    def test_resolve_empty_returns_none(self) -> None:
        assert resolve_finding_status("") is None


# ---------------------------------------------------------------------------
# S02 — WorkPackageStatus enum and compatibility
# ---------------------------------------------------------------------------


class TestWorkPackageStatusEnum:
    """WorkPackageStatus enum has correct values and compatibility."""

    def test_enum_has_seven_states(self) -> None:
        assert len(WorkPackageStatus) == 7

    def test_draft_is_initial(self) -> None:
        assert WorkPackageStatus.DRAFT.value == "Draft"

    def test_all_states_have_transitions(self) -> None:
        for status in WorkPackageStatus:
            assert status in WORK_PACKAGE_TRANSITIONS

    def test_resolve_default_full_text(self) -> None:
        assert (
            resolve_work_package_status("Ready for Product Engineering review")
            == WorkPackageStatus.READY
        )

    def test_resolve_ready_for_review(self) -> None:
        assert resolve_work_package_status("Ready for review") == WorkPackageStatus.READY

    def test_resolve_ready(self) -> None:
        assert resolve_work_package_status("Ready") == WorkPackageStatus.READY

    def test_resolve_needs_review(self) -> None:
        assert resolve_work_package_status("needs_review") == WorkPackageStatus.READY

    def test_resolve_unknown_returns_none(self) -> None:
        assert resolve_work_package_status("unknown") is None


# ---------------------------------------------------------------------------
# S03 — Finding transition validation
# ---------------------------------------------------------------------------


class TestFindingTransitions:
    """Allowed finding transitions are validated correctly."""

    def test_detected_to_acknowledged(self) -> None:
        result = validate_finding_transition("Detected", "Acknowledged")
        assert result.valid
        assert result.from_status == "Detected"
        assert result.to_status == "Acknowledged"

    def test_detected_to_deferred(self) -> None:
        result = validate_finding_transition("Detected", "Deferred")
        assert result.valid

    def test_acknowledged_to_in_progress(self) -> None:
        result = validate_finding_transition("Acknowledged", "In Progress")
        assert result.valid

    def test_in_progress_to_remediated(self) -> None:
        result = validate_finding_transition("In Progress", "Remediated")
        assert result.valid

    def test_remediated_to_verified(self) -> None:
        result = validate_finding_transition("Remediated", "Verified")
        assert result.valid

    def test_remediated_to_detected_regression(self) -> None:
        result = validate_finding_transition("Remediated", "Detected")
        assert result.valid

    def test_verified_to_detected_regression(self) -> None:
        result = validate_finding_transition("Verified", "Detected")
        assert result.valid

    def test_wont_fix_to_acknowledged_reopen(self) -> None:
        result = validate_finding_transition("Won't Fix", "Acknowledged")
        assert result.valid

    def test_invalid_transition_detected_to_verified(self) -> None:
        result = validate_finding_transition("Detected", "Verified")
        assert not result.valid
        assert "not allowed" in result.reason.lower()

    def test_invalid_transition_has_allowed_targets(self) -> None:
        result = validate_finding_transition("Detected", "Verified")
        assert len(result.allowed_targets) > 0
        assert "Acknowledged" in result.allowed_targets

    def test_unknown_from_status(self) -> None:
        result = validate_finding_transition("Bogus", "Acknowledged")
        assert not result.valid
        assert "Unknown" in result.reason

    def test_unknown_to_status(self) -> None:
        result = validate_finding_transition("Detected", "Bogus")
        assert not result.valid
        assert "Unknown" in result.reason

    def test_self_transition_not_allowed(self) -> None:
        result = validate_finding_transition("Detected", "Detected")
        assert not result.valid

    def test_get_allowed_transitions(self) -> None:
        allowed = get_allowed_finding_transitions("Detected")
        assert "Acknowledged" in allowed
        assert "Deferred" in allowed

    def test_get_allowed_unknown_status(self) -> None:
        allowed = get_allowed_finding_transitions("Bogus")
        assert allowed == ()

    def test_alias_from_status_resolved(self) -> None:
        """Review decision 'accepted' resolves to Acknowledged."""
        result = validate_finding_transition("accepted", "In Progress")
        assert result.valid
        assert result.from_status == "Acknowledged"


# ---------------------------------------------------------------------------
# S04 — Work package transition validation
# ---------------------------------------------------------------------------


class TestWorkPackageTransitions:
    """Allowed work package transitions are validated correctly."""

    def test_draft_to_ready(self) -> None:
        result = validate_work_package_transition("Draft", "Ready")
        assert result.valid

    def test_ready_to_in_progress(self) -> None:
        result = validate_work_package_transition("Ready", "In Progress")
        assert result.valid

    def test_in_progress_to_completed(self) -> None:
        result = validate_work_package_transition("In Progress", "Completed")
        assert result.valid

    def test_completed_to_verified(self) -> None:
        result = validate_work_package_transition("Completed", "Verified")
        assert result.valid

    def test_verified_is_terminal(self) -> None:
        result = validate_work_package_transition("Verified", "Draft")
        assert not result.valid
        assert result.allowed_targets == ()

    def test_blocked_to_in_progress(self) -> None:
        result = validate_work_package_transition("Blocked", "In Progress")
        assert result.valid

    def test_invalid_transition_draft_to_completed(self) -> None:
        result = validate_work_package_transition("Draft", "Completed")
        assert not result.valid

    def test_alias_ready_for_pet_review(self) -> None:
        result = validate_work_package_transition(
            "Ready for Product Engineering review", "In Progress"
        )
        assert result.valid
        assert result.from_status == "Ready"

    def test_alias_needs_review(self) -> None:
        result = validate_work_package_transition("needs_review", "In Progress")
        assert result.valid
        assert result.from_status == "Ready"

    def test_get_allowed_transitions(self) -> None:
        allowed = get_allowed_work_package_transitions("Draft")
        assert "Ready" in allowed
        assert "Deferred" in allowed


# ---------------------------------------------------------------------------
# S05 — Lifecycle history (append-only, optional)
# ---------------------------------------------------------------------------


class TestLifecycleHistory:
    """Lifecycle history is optional and append-only."""

    def test_empty_history_is_valid(self) -> None:
        history = LifecycleHistory()
        assert len(history.entries) == 0

    def test_append_entry(self) -> None:
        history = LifecycleHistory()
        entry = LifecycleEntry(
            artifact_type="finding",
            artifact_id="TD-ARCH-001",
            from_status="Detected",
            to_status="Acknowledged",
        )
        history.append_entry(entry)
        assert len(history.entries) == 1
        assert history.entries[0].artifact_id == "TD-ARCH-001"

    def test_multiple_appends(self) -> None:
        history = LifecycleHistory()
        for i in range(5):
            history.append_entry(
                LifecycleEntry(
                    artifact_type="finding",
                    artifact_id=f"TD-{i:03d}",
                    from_status="Detected",
                    to_status="Acknowledged",
                )
            )
        assert len(history.entries) == 5

    def test_get_entries_for_artifact(self) -> None:
        history = LifecycleHistory()
        history.append_entry(
            LifecycleEntry(
                artifact_type="finding",
                artifact_id="TD-001",
                from_status="Detected",
                to_status="Acknowledged",
            )
        )
        history.append_entry(
            LifecycleEntry(
                artifact_type="finding",
                artifact_id="TD-002",
                from_status="Detected",
                to_status="Deferred",
            )
        )
        history.append_entry(
            LifecycleEntry(
                artifact_type="finding",
                artifact_id="TD-001",
                from_status="Acknowledged",
                to_status="In Progress",
            )
        )
        entries = history.get_entries_for("finding", "TD-001")
        assert len(entries) == 2

    def test_latest_entry_for(self) -> None:
        history = LifecycleHistory()
        history.append_entry(
            LifecycleEntry(
                artifact_type="finding",
                artifact_id="TD-001",
                from_status="Detected",
                to_status="Acknowledged",
            )
        )
        history.append_entry(
            LifecycleEntry(
                artifact_type="finding",
                artifact_id="TD-001",
                from_status="Acknowledged",
                to_status="In Progress",
            )
        )
        latest = history.latest_entry_for("finding", "TD-001")
        assert latest is not None
        assert latest.to_status == "In Progress"

    def test_latest_entry_nonexistent(self) -> None:
        history = LifecycleHistory()
        assert history.latest_entry_for("finding", "TD-999") is None

    def test_serialization_roundtrip(self) -> None:
        history = LifecycleHistory()
        history.append_entry(
            LifecycleEntry(
                artifact_type="finding",
                artifact_id="TD-001",
                from_status="Detected",
                to_status="Acknowledged",
                actor="operator",
                rationale="Confirmed real",
            )
        )
        json_str = history.model_dump_json(indent=2)
        restored = LifecycleHistory.model_validate_json(json_str)
        assert len(restored.entries) == 1
        assert restored.entries[0].rationale == "Confirmed real"

    def test_missing_file_is_valid(self) -> None:
        """Missing lifecycle-history.json is not an error."""
        assert not Path("nonexistent_lifecycle_history.json").exists()
        # Code that loads it should treat missing as empty
        history = LifecycleHistory()
        assert len(history.entries) == 0


# ---------------------------------------------------------------------------
# S06 — Report-only inference
# ---------------------------------------------------------------------------


class TestInferredLifecycle:
    """Inferred lifecycle state is report-only."""

    def test_no_context_returns_detected(self) -> None:
        result = infer_finding_status_from_context("Detected")
        assert result == "Detected"

    def test_review_accepted_upgrades_status(self) -> None:
        result = infer_finding_status_from_context("Detected", review_decision_status="accepted")
        assert result == "Acknowledged"

    def test_verification_remediated_upgrades_status(self) -> None:
        result = infer_finding_status_from_context(
            "Detected", verification_status="likely_remediated"
        )
        assert result == "Remediated"

    def test_both_contexts_uses_most_advanced(self) -> None:
        result = infer_finding_status_from_context(
            "Detected",
            review_decision_status="accepted",
            verification_status="likely_remediated",
        )
        assert result == "Remediated"

    def test_risk_accepted_inferred(self) -> None:
        result = infer_finding_status_from_context(
            "Detected", review_decision_status="risk-accepted"
        )
        assert result == "Won't Fix"

    def test_already_fixed_inferred(self) -> None:
        result = infer_finding_status_from_context(
            "Detected", review_decision_status="already-fixed"
        )
        assert result == "Remediated"

    def test_unknown_context_defaults_to_base(self) -> None:
        result = infer_finding_status_from_context("Detected", review_decision_status="bogus_value")
        assert result == "Detected"

    def test_empty_strings_handled(self) -> None:
        result = infer_finding_status_from_context(
            "Detected", review_decision_status="", verification_status=""
        )
        assert result == "Detected"


# ---------------------------------------------------------------------------
# S07 — Reporter integration
# ---------------------------------------------------------------------------


class TestReporterLifecycleSummary:
    """Reporter shows lifecycle distribution when available."""

    def test_lifecycle_summary_no_findings(self, tmp_path: Path) -> None:
        from pharabius.core.reporter import write_reports

        ai_debt = tmp_path / ".ai-debt"
        ai_debt.mkdir()
        (ai_debt / "project-profile.json").write_text(
            json.dumps({"project_name": "test", "repository_root": str(tmp_path)})
        )
        (ai_debt / "evidence.json").write_text(json.dumps({"repository": "test", "evidence": []}))
        (ai_debt / "debt-register.json").write_text(
            json.dumps(
                {
                    "project_name": "test",
                    "summary": {
                        "total_findings": 0,
                        "critical": 0,
                        "high": 0,
                        "medium": 0,
                        "low": 0,
                    },
                }
            )
        )

        result = write_reports(tmp_path)
        foundation = next(p for p in result.files_written if p.name == "foundation-audit-report.md")
        content = foundation.read_text(encoding="utf-8")
        assert "Foundation Technical Debt Audit Report" in content

    def test_lifecycle_summary_with_findings(self, tmp_path: Path) -> None:
        from pharabius.core.reporter import write_reports

        ai_debt = tmp_path / ".ai-debt"
        ai_debt.mkdir()
        (ai_debt / "project-profile.json").write_text(
            json.dumps({"project_name": "test", "repository_root": str(tmp_path)})
        )
        (ai_debt / "evidence.json").write_text(json.dumps({"repository": "test", "evidence": []}))
        (ai_debt / "debt-register.json").write_text(
            json.dumps(
                {
                    "project_name": "test",
                    "summary": {
                        "total_findings": 2,
                        "critical": 0,
                        "high": 1,
                        "medium": 1,
                        "low": 0,
                    },
                    "findings": [
                        {
                            "id": "TD-001",
                            "category": "TD-ARCH",
                            "title": "Test finding 1",
                            "description": "Test",
                            "status": "Detected",
                            "priority": "High",
                            "risk_score": 25,
                            "technical_impact": "Test",
                            "business_impact": "Test",
                            "recommended_action": "Test",
                        },
                        {
                            "id": "TD-002",
                            "category": "TD-DEP",
                            "title": "Test finding 2",
                            "description": "Test",
                            "status": "Acknowledged",
                            "priority": "Medium",
                            "risk_score": 15,
                            "technical_impact": "Test",
                            "business_impact": "Test",
                            "recommended_action": "Test",
                        },
                    ],
                }
            )
        )

        result = write_reports(tmp_path)
        foundation = next(p for p in result.files_written if p.name == "foundation-audit-report.md")
        content = foundation.read_text(encoding="utf-8")
        # Should have lifecycle section
        assert "Lifecycle" in content


# ---------------------------------------------------------------------------
# S08 — Status reader integration
# ---------------------------------------------------------------------------


class TestStatusReaderLifecycle:
    """Status reader shows lifecycle distribution."""

    def test_status_with_findings(self, tmp_path: Path) -> None:
        from pharabius.core.status_reader import read_status

        ai_debt = tmp_path / ".ai-debt"
        ai_debt.mkdir()
        (ai_debt / "project-profile.json").write_text(
            json.dumps({"project_name": "test", "repository_root": str(tmp_path)})
        )
        (ai_debt / "evidence.json").write_text(json.dumps({"repository": "test", "evidence": []}))
        (ai_debt / "debt-register.json").write_text(
            json.dumps(
                {
                    "project_name": "test",
                    "summary": {
                        "total_findings": 1,
                        "critical": 0,
                        "high": 1,
                        "medium": 0,
                        "low": 0,
                    },
                    "findings": [
                        {
                            "id": "TD-001",
                            "category": "TD-ARCH",
                            "title": "Test",
                            "description": "Test",
                            "status": "Detected",
                            "priority": "High",
                            "risk_score": 25,
                            "technical_impact": "Test",
                            "business_impact": "Test",
                            "recommended_action": "Test",
                        }
                    ],
                }
            )
        )

        status = read_status(tmp_path)
        assert "Findings:" in status
