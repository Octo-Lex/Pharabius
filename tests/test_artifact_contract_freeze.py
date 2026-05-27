"""Tests for final artifact contract freeze checks (W51-S02)."""

from __future__ import annotations

from pathlib import Path

from pharabius.core.artifact_contract import (
    KNOWN_DIRS,
    OPTIONAL_ARTIFACTS,
    REQUIRED_ARTIFACTS,
    ArtifactContractDriftIssue,
    check_artifact_contract_drift,
)


class TestRequiredArtifacts:
    def test_missing_required_is_error(self, tmp_path: Path) -> None:
        ai = tmp_path / ".ai-debt"
        ai.mkdir()
        report = check_artifact_contract_drift(ai)
        assert report.status == "fail"
        required_issues = [i for i in report.issues if i.code == "required_artifact_missing"]
        assert len(required_issues) == len(REQUIRED_ARTIFACTS)

    def test_all_required_present_passes(self, tmp_path: Path) -> None:
        ai = tmp_path / ".ai-debt"
        ai.mkdir()
        for rel in REQUIRED_ARTIFACTS:
            p = ai / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("{}")
        report = check_artifact_contract_drift(ai)
        required_missing = [i for i in report.issues if i.code == "required_artifact_missing"]
        assert len(required_missing) == 0


class TestOptionalArtifacts:
    def test_missing_optional_is_warning(self, tmp_path: Path) -> None:
        ai = tmp_path / ".ai-debt"
        ai.mkdir()
        for rel in REQUIRED_ARTIFACTS:
            p = ai / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("{}")
        report = check_artifact_contract_drift(ai)
        assert report.status == "pass_with_warnings"
        opt_missing = [i for i in report.issues if i.code == "optional_artifact_missing"]
        assert len(opt_missing) > 0

    def test_all_present_passes(self, tmp_path: Path) -> None:
        ai = tmp_path / ".ai-debt"
        ai.mkdir()
        for rel in REQUIRED_ARTIFACTS + OPTIONAL_ARTIFACTS:
            p = ai / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("{}")
        report = check_artifact_contract_drift(ai)
        assert report.status == "pass"
        assert report.errors == 0


class TestUndocumentedArtifacts:
    def test_undocumented_is_warning(self, tmp_path: Path) -> None:
        ai = tmp_path / ".ai-debt"
        ai.mkdir()
        for rel in REQUIRED_ARTIFACTS:
            p = ai / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("{}")
        (ai / "unknown-artifact.xyz").write_text("test")
        report = check_artifact_contract_drift(ai)
        undoc = [i for i in report.issues if i.code == "undocumented_artifact"]
        assert len(undoc) == 1
        assert undoc[0].artifact_path == "unknown-artifact.xyz"


class TestContractLists:
    def test_required_count_stable(self) -> None:
        assert len(REQUIRED_ARTIFACTS) == 7

    def test_optional_count_stable(self) -> None:
        assert len(OPTIONAL_ARTIFACTS) >= 17

    def test_known_dirs_includes_all_required(self) -> None:
        for rel in REQUIRED_ARTIFACTS:
            name = rel.split("/")[0] if "/" in rel else rel
            assert name in KNOWN_DIRS, f"{name} not in KNOWN_DIRS"

    def test_no_duplicate_paths(self) -> None:
        all_paths = REQUIRED_ARTIFACTS + OPTIONAL_ARTIFACTS
        assert len(all_paths) == len(set(all_paths))


class TestMissingAiDebtDir:
    def test_missing_dir_is_fail(self, tmp_path: Path) -> None:
        report = check_artifact_contract_drift(tmp_path / "nonexistent")
        assert report.status == "fail"
        assert any(i.code == "missing_ai_debt_dir" for i in report.issues)
