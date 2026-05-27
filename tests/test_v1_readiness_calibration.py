"""Tests for v1 readiness report calibration (W49-S04)."""

from __future__ import annotations

from pathlib import Path

from pharabius.core.v1_readiness import (
    generate_readiness_report,
    render_readiness_markdown,
)


def _make_ai_debt(tmp: Path, include_optional: bool = False, bad_json: str | None = None) -> Path:
    ai = tmp / ".ai-debt"
    ai.mkdir(parents=True, exist_ok=True)
    required = {
        "evidence.json": '{"schema_version":"1.0","evidence":[]}',
        "debt-register.json": '{"schema_version":"1.0","findings":[]}',
        "project-profile.json": '{"schema_version":"1.0"}',
        "debt-register.md": "# Debt Register",
        "reports/foundation-audit-report.md": "# Report",
        "remediation-roadmap.md": "# Roadmap",
        "handoff-summary.md": "# Handoff",
        "review/decisions.json": '{"decisions":[]}',
        "ticket-drafts/ticket-drafts.json": '{"drafts":[]}',
    }
    optional = {
        "analysis-units.json": '{"units":[]}',
        "architecture-graph.json": '{"nodes":[]}',
        "export-bundles/manifest.json": '{"artifacts":[]}',
        "portfolio/portfolio-summary.json": '{"summary":{}}',
        "portfolio/repository-index.json": '{"entries":[]}',
        "portfolio/portfolio-summary.md": "# Summary",
        "portfolio/validation-rollup.md": "# Rollup",
        "claims/operational-claims.json": '{"claims":[]}',
        "claims/operational-claims.md": "# Claims",
        "claims/confidence-report.md": "# Confidence",
        "claims/gaps.md": "# Gaps",
        "claims/questions.md": "# Questions",
        "agent-handoff-contract.md": "# Contract",
        "traceability/evidence-finding-matrix.md": "# Matrix",
        "traceability/finding-claim-matrix.md": "# Matrix",
        "traceability/claim-workpackage-matrix.md": "# Matrix",
    }
    all_files = {**required, **(optional if include_optional else {})}
    if bad_json:
        all_files[bad_json] = "NOT JSON"
    for rel, content in all_files.items():
        p = ai / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
    return ai


class TestCalibrationStatus:
    def test_ready_with_all_artifacts(self, tmp_path: Path) -> None:
        ai = _make_ai_debt(tmp_path, include_optional=True)
        report = generate_readiness_report(ai)
        assert report.status == "ready"

    def test_partial_without_optional(self, tmp_path: Path) -> None:
        ai = _make_ai_debt(tmp_path, include_optional=False)
        report = generate_readiness_report(ai)
        assert report.status == "partial"

    def test_needs_review_with_bad_json(self, tmp_path: Path) -> None:
        ai = _make_ai_debt(tmp_path, include_optional=True, bad_json="evidence.json")
        report = generate_readiness_report(ai)
        assert report.status == "needs_review"


class TestBlockingSeverity:
    def test_required_missing_is_blocking(self, tmp_path: Path) -> None:
        ai = _make_ai_debt(tmp_path, include_optional=True)
        (ai / "evidence.json").unlink()
        report = generate_readiness_report(ai)
        blocking = [c for c in report.checks if c.severity == "blocking"]
        assert len(blocking) >= 1

    def test_optional_missing_is_non_blocking(self, tmp_path: Path) -> None:
        ai = _make_ai_debt(tmp_path, include_optional=False)
        report = generate_readiness_report(ai)
        non_blocking = [
            c for c in report.checks if c.severity == "non_blocking" and c.status == "warning"
        ]
        assert len(non_blocking) >= 1


class TestRecommendedActions:
    def test_blocking_has_action(self, tmp_path: Path) -> None:
        ai = _make_ai_debt(tmp_path, include_optional=True)
        (ai / "evidence.json").unlink()
        report = generate_readiness_report(ai)
        blocking = [c for c in report.checks if c.severity == "blocking"]
        for c in blocking:
            assert c.recommended_action, f"No action for {c.name}"

    def test_non_blocking_has_action(self, tmp_path: Path) -> None:
        ai = _make_ai_debt(tmp_path, include_optional=False)
        report = generate_readiness_report(ai)
        warnings = [c for c in report.checks if c.status == "warning"]
        for c in warnings:
            assert c.recommended_action, f"No action for {c.name}"


class TestMarkdownCalibration:
    def test_blocking_section_in_md(self, tmp_path: Path) -> None:
        ai = _make_ai_debt(tmp_path, include_optional=True)
        (ai / "evidence.json").unlink()
        report = generate_readiness_report(ai)
        md = render_readiness_markdown(report)
        assert "### Blocking Issues" in md

    def test_no_blocking_shows_none(self, tmp_path: Path) -> None:
        ai = _make_ai_debt(tmp_path, include_optional=True)
        report = generate_readiness_report(ai)
        md = render_readiness_markdown(report)
        assert "None." in md
