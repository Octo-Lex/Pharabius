from __future__ import annotations

from pathlib import Path

from pharabius.core.analyzer import write_debt_register
from pharabius.core.init_workspace import initialize_workspace
from pharabius.core.planner import write_plan
from pharabius.core.profiler import write_repository_profile
from pharabius.core.scanner import write_evidence_store


def test_write_plan_generates_roadmap_handoff_and_work_packages(
    tmp_path: Path,
) -> None:
    initialize_workspace(tmp_path)

    (tmp_path / "package.json").write_text(
        '{"dependencies":{"express":"^4.0.0"}}',
        encoding="utf-8",
    )

    write_repository_profile(tmp_path)
    write_evidence_store(tmp_path)
    write_debt_register(tmp_path)

    result = write_plan(tmp_path)

    roadmap = tmp_path / ".ai-debt" / "remediation-roadmap.md"
    handoff = tmp_path / ".ai-debt" / "handoff-summary.md"

    assert roadmap.exists()
    assert handoff.exists()
    assert result.work_package_paths

    roadmap_text = roadmap.read_text(encoding="utf-8")
    handoff_text = handoff.read_text(encoding="utf-8")

    assert "# Remediation Roadmap" in roadmap_text
    assert "# AI Technical Debt Handoff Summary" in handoff_text
    assert "TD-TEST" in roadmap_text

    for package_path in result.work_package_paths:
        path = Path(package_path)
        text = path.read_text(encoding="utf-8")

        assert path.exists()
        assert text.startswith("# Work Package:")
        assert "## Linked Debt Items" in text
        assert "## Evidence" in text
        assert "## Definition of Done" in text


def test_write_plan_handles_no_findings(tmp_path: Path) -> None:
    initialize_workspace(tmp_path)

    # Do NOT profile/scan/analyze — leave evidence empty
    # so the debt register has zero findings.

    result = write_plan(tmp_path)

    roadmap = tmp_path / ".ai-debt" / "remediation-roadmap.md"
    handoff = tmp_path / ".ai-debt" / "handoff-summary.md"

    assert roadmap.exists()
    assert handoff.exists()
    assert result.work_package_paths == []
    assert result.work_packages == []

    assert "No work packages generated" in roadmap.read_text(encoding="utf-8")
    assert "did not generate deterministic technical debt findings" in handoff.read_text(
        encoding="utf-8"
    )


def test_write_plan_respects_max_work_packages(tmp_path: Path) -> None:
    initialize_workspace(tmp_path)

    (tmp_path / "package.json").write_text(
        '{"dependencies":{"express":"^4.0.0"}}',
        encoding="utf-8",
    )
    (tmp_path / ".env").write_text(
        "SECRET=value\n",
        encoding="utf-8",
    )

    write_repository_profile(tmp_path)
    write_evidence_store(tmp_path)
    write_debt_register(tmp_path)

    result = write_plan(tmp_path, max_work_packages=1)

    assert len(result.work_package_paths) <= 1
    assert len(result.work_packages) <= 1
