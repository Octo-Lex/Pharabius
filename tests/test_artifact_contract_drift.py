"""Tests for artifact contract drift checks (W49-S02)."""

from __future__ import annotations

from pathlib import Path

from pharabius.core.artifact_contract import (
    check_artifact_contract_drift,
)


def _make_ai_debt(tmp: Path, files: list[str] | None = None) -> Path:
    ai = tmp / ".ai-debt"
    ai.mkdir(parents=True, exist_ok=True)
    all_files = files or [
        "evidence.json",
        "debt-register.json",
        "project-profile.json",
        "debt-register.md",
        "reports/foundation-audit-report.md",
        "remediation-roadmap.md",
        "handoff-summary.md",
        "analysis-units.json",
        "architecture-graph.json",
        "review/decisions.json",
        "ticket-drafts/ticket-drafts.json",
        "portfolio/portfolio-summary.json",
        "portfolio/repository-index.json",
        "portfolio/portfolio-summary.md",
        "portfolio/validation-rollup.md",
        "claims/operational-claims.json",
        "claims/operational-claims.md",
        "claims/confidence-report.md",
        "claims/gaps.md",
        "claims/questions.md",
        "agent-handoff-contract.md",
        "traceability/evidence-finding-matrix.md",
        "traceability/finding-claim-matrix.md",
        "traceability/claim-workpackage-matrix.md",
    ]
    for rel in all_files:
        p = ai / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("test")
    return ai


class TestDriftReport:
    def test_complete_fixture_passes(self, tmp_path: Path) -> None:
        ai = _make_ai_debt(tmp_path)
        report = check_artifact_contract_drift(ai)
        assert report.status == "pass"
        assert report.errors == 0

    def test_missing_required_is_error(self, tmp_path: Path) -> None:
        ai = _make_ai_debt(tmp_path, files=["debt-register.json"])
        report = check_artifact_contract_drift(ai)
        assert report.errors >= 1
        assert report.status == "fail"
        codes = [i.code for i in report.issues]
        assert "required_artifact_missing" in codes

    def test_missing_optional_is_warning(self, tmp_path: Path) -> None:
        # Only required files, no optional ones
        ai = _make_ai_debt(
            tmp_path,
            files=[
                "evidence.json",
                "debt-register.json",
                "project-profile.json",
                "debt-register.md",
                "reports/foundation-audit-report.md",
                "remediation-roadmap.md",
                "handoff-summary.md",
            ],
        )
        report = check_artifact_contract_drift(ai)
        assert report.warnings > 0
        codes = [i.code for i in report.issues]
        assert "optional_artifact_missing" in codes

    def test_missing_optional_no_error(self, tmp_path: Path) -> None:
        ai = _make_ai_debt(
            tmp_path,
            files=[
                "evidence.json",
                "debt-register.json",
                "project-profile.json",
                "debt-register.md",
                "reports/foundation-audit-report.md",
                "remediation-roadmap.md",
                "handoff-summary.md",
            ],
        )
        report = check_artifact_contract_drift(ai)
        assert report.errors == 0
        assert report.status == "pass_with_warnings"

    def test_undocumented_artifact_warns(self, tmp_path: Path) -> None:
        ai = _make_ai_debt(tmp_path)
        (ai / "unknown-artifact.dat").write_text("x")
        report = check_artifact_contract_drift(ai)
        codes = [i.code for i in report.issues]
        assert "undocumented_artifact" in codes


class TestMissingDir:
    def test_missing_dir_fails(self, tmp_path: Path) -> None:
        report = check_artifact_contract_drift(tmp_path / "nonexistent")
        assert report.status == "fail"
        assert report.errors == 1
        assert report.issues[0].code == "missing_ai_debt_dir"


class TestDeterminism:
    def test_same_input_same_result(self, tmp_path: Path) -> None:
        ai = _make_ai_debt(tmp_path)
        r1 = check_artifact_contract_drift(ai)
        r2 = check_artifact_contract_drift(ai)
        assert r1.errors == r2.errors
        assert r1.warnings == r2.warnings
        assert r1.status == r2.status
