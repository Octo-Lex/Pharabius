from __future__ import annotations

from pathlib import Path

from pharabius.core.analyzer import write_debt_register
from pharabius.core.init_workspace import initialize_workspace
from pharabius.core.profiler import write_repository_profile
from pharabius.core.reporter import write_reports
from pharabius.core.scanner import write_evidence_store


def test_write_reports_generates_expected_markdown_files(tmp_path: Path) -> None:
    initialize_workspace(tmp_path)

    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text(
        "import json\nprint('hello')\n",
        encoding="utf-8",
    )
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname = 'example'\n",
        encoding="utf-8",
    )

    write_repository_profile(tmp_path)
    write_evidence_store(tmp_path)
    write_debt_register(tmp_path)

    result = write_reports(tmp_path)

    expected_files = {
        tmp_path / ".ai-debt" / "architecture-map.md",
        tmp_path / ".ai-debt" / "dependency-health.md",
        tmp_path / ".ai-debt" / "test-health.md",
        tmp_path / ".ai-debt" / "security-exposure.md",
        tmp_path / ".ai-debt" / "business-risk-proxy.md",
        tmp_path / ".ai-debt" / "reports" / "foundation-audit-report.md",
        tmp_path / ".ai-debt" / "reports" / "external-evidence-report.md",
    }

    assert set(result.files_written) == expected_files

    for path in expected_files:
        assert path.exists()
        assert path.read_text(encoding="utf-8").startswith("#")


def test_foundation_report_is_consistent_with_debt_register(
    tmp_path: Path,
) -> None:
    initialize_workspace(tmp_path)

    (tmp_path / "package.json").write_text(
        '{"dependencies":{"express":"^4.0.0"}}',
        encoding="utf-8",
    )

    write_repository_profile(tmp_path)
    write_evidence_store(tmp_path)
    register = write_debt_register(tmp_path)
    write_reports(tmp_path)

    report = (tmp_path / ".ai-debt" / "reports" / "foundation-audit-report.md").read_text(
        encoding="utf-8"
    )

    assert "# Foundation Technical Debt Audit Report" in report
    assert f"Total findings: **{register.summary.total_findings}**" in report

    for finding in register.findings:
        assert finding.id in report
        assert finding.title in report


def test_reports_do_not_require_existing_findings(tmp_path: Path) -> None:
    initialize_workspace(tmp_path)

    write_reports(tmp_path)

    architecture_report = (tmp_path / ".ai-debt" / "architecture-map.md").read_text(
        encoding="utf-8"
    )
    foundation_report = (
        tmp_path / ".ai-debt" / "reports" / "foundation-audit-report.md"
    ).read_text(encoding="utf-8")

    assert "No deterministic architecture debt findings" in architecture_report
    assert "# Foundation Technical Debt Audit Report" in foundation_report
