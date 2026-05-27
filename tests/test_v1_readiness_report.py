"""Tests for v1 readiness report generator (W48-S05)."""

from __future__ import annotations

from pathlib import Path

from pharabius.core.v1_readiness import (
    generate_readiness_report,
    render_readiness_markdown,
)


def _make_ai_debt(tmp: Path, files: dict[str, str] | None = None) -> Path:
    ai = tmp / ".ai-debt"
    ai.mkdir(parents=True, exist_ok=True)
    defaults = {
        "evidence.json": '{"schema_version":"1.0","evidence":[]}',
        "debt-register.json": '{"schema_version":"1.0","findings":[]}',
        "project-profile.json": '{"schema_version":"1.0"}',
        "debt-register.md": "# Debt Register\n\nNo findings.",
        "reports/foundation-audit-report.md": "# Report",
        "remediation-roadmap.md": "# Roadmap",
        "handoff-summary.md": "# Handoff",
        "review/decisions.json": '{"decisions":[]}',
        "ticket-drafts/ticket-drafts.json": '{"drafts":[]}',
        "analysis-units.json": '{"units":[]}',
        "architecture-graph.json": '{"nodes":[]}',
        "export-bundles/manifest.json": '{"artifacts":[]}',
        "portfolio/portfolio-summary.json": '{"summary":{}}',
        "claims/operational-claims.json": '{"claims":[]}',
        "agent-handoff-contract.md": "# Handoff Contract",
    }
    all_files = {**defaults, **(files or {})}
    for rel, content in all_files.items():
        p = ai / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
    return ai


class TestReadinessGeneration:
    def test_complete_repo_is_ready(self, tmp_path: Path) -> None:
        ai = _make_ai_debt(tmp_path)
        report = generate_readiness_report(ai)
        assert report.status == "ready"
        assert report.summary["fail"] == 0

    def test_missing_required_fails(self, tmp_path: Path) -> None:
        ai = _make_ai_debt(tmp_path, {"evidence.json": "REMOVE"})
        (ai / "evidence.json").unlink()
        report = generate_readiness_report(ai)
        assert report.status == "needs_review"
        assert report.summary["fail"] >= 1

    def test_missing_optional_warns(self, tmp_path: Path) -> None:
        ai = tmp_path / ".ai-debt"
        ai.mkdir(parents=True, exist_ok=True)
        # Only required artifacts, no optional ones
        for rel, content in {
            "evidence.json": '{"schema_version":"1.0","evidence":[]}',
            "debt-register.json": '{"schema_version":"1.0","findings":[]}',
            "project-profile.json": '{"schema_version":"1.0"}',
            "debt-register.md": "# Debt Register",
            "reports/foundation-audit-report.md": "# Report",
            "remediation-roadmap.md": "# Roadmap",
            "handoff-summary.md": "# Handoff",
            "review/decisions.json": '{"decisions":[]}',
            "ticket-drafts/ticket-drafts.json": '{"drafts":[]}',
        }.items():
            p = ai / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content)
        report = generate_readiness_report(ai)
        assert report.summary["warning"] > 0

    def test_invalid_json_fails(self, tmp_path: Path) -> None:
        ai = _make_ai_debt(tmp_path, {"evidence.json": "NOT JSON"})
        report = generate_readiness_report(ai)
        assert report.summary["fail"] >= 1

    def test_empty_md_warns(self, tmp_path: Path) -> None:
        ai = _make_ai_debt(tmp_path, {"debt-register.md": "  \n"})
        report = generate_readiness_report(ai)
        assert report.summary["fail"] >= 1


class TestSafetyChecks:
    def test_safety_checks_present(self, tmp_path: Path) -> None:
        ai = _make_ai_debt(tmp_path)
        report = generate_readiness_report(ai)
        safety = [c for c in report.checks if c.name.startswith("safety:")]
        assert len(safety) == 5
        assert all(c.status == "pass" for c in safety)

    def test_safety_checks_in_markdown(self, tmp_path: Path) -> None:
        ai = _make_ai_debt(tmp_path)
        report = generate_readiness_report(ai)
        md = render_readiness_markdown(report)
        assert "Safety Boundary Checks" in md
        assert "safety:no_external_api" in md


class TestMarkdownRendering:
    def test_renders_summary_table(self, tmp_path: Path) -> None:
        ai = _make_ai_debt(tmp_path)
        report = generate_readiness_report(ai)
        md = render_readiness_markdown(report)
        assert "## Summary" in md
        assert "total_checks" in md

    def test_renders_verdict(self, tmp_path: Path) -> None:
        ai = _make_ai_debt(tmp_path)
        report = generate_readiness_report(ai)
        md = render_readiness_markdown(report)
        assert "Release Candidate Verdict" in md


class TestDeterminism:
    def test_same_input_same_checks(self, tmp_path: Path) -> None:
        ai = _make_ai_debt(tmp_path)
        r1 = generate_readiness_report(ai)
        r2 = generate_readiness_report(ai)
        assert len(r1.checks) == len(r2.checks)
        for c1, c2 in zip(r1.checks, r2.checks, strict=True):
            assert c1.name == c2.name
            assert c1.status == c2.status
