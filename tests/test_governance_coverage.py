"""Additional governance coverage tests — covers untested paths."""

from __future__ import annotations

import warnings
from pathlib import Path

import yaml

from pharabius.core.governance import load_governance
from pharabius.core.template_engine import (
    load_resolved_template,
    load_template_file,
    render_template,
    resolve_template_path,
)
from pharabius.schemas.finding import DebtFinding, DebtRegister, DebtRegisterSummary
from pharabius.schemas.governance import GovernanceConfig
from pharabius.schemas.repository import RepositoryProfile
from pharabius.schemas.work_package import WorkPackage


def _finding(
    fid: str = "TD-TEST-001",
    severity: str = "Medium",
    score: int = 10,
) -> DebtFinding:
    return DebtFinding(
        id=fid,
        category="TD-TEST",
        issue_type="technical_debt",
        title="Test finding",
        description="Test",
        severity=severity,
        confidence="High",
        status="Detected",
        locations=["src/test.py"],
        evidence_ids=["EVD-000001"],
        technical_impact="Test",
        business_impact="Test",
        business_impact_basis="Inferred",
        risk_score=score,
        priority="Medium",
        remediation_effort="Small",
        recommended_action="Fix",
        verification_recommendations=["Verify"],
        risks_and_cautions=["Caution"],
        suggested_owner_area="Engineering",
    )


def _pkg() -> WorkPackage:
    return WorkPackage(
        id="WP-001",
        title="Test package",
        status="Ready",
        linked_debt_items=["TD-TEST-001"],
        objective="Fix",
        current_risk="Risk",
        recommended_engineering_approach=["Step 1"],
        expected_affected_areas=["src/"],
        preconditions=[],
        verification_recommendations=["Verify"],
        risks_and_cautions=["Caution"],
        definition_of_done=["Done"],
        estimated_effort="Small",
        expected_risk_reduction="Significant",
        suggested_owner_area="Engineering",
    )


def _register(
    tmp_path: Path,
    findings: list[DebtFinding] | None = None,
) -> DebtRegister:
    f = findings or [_finding()]
    n = len(f)
    return DebtRegister(
        project_name="test",
        repository=str(tmp_path),
        branch="main",
        commit="abc",
        findings=f,
        summary=DebtRegisterSummary(
            total_findings=n,
            critical=sum(1 for x in f if x.severity == "Critical"),
            high=sum(1 for x in f if x.severity == "High"),
            medium=sum(1 for x in f if x.severity == "Medium"),
            low=sum(1 for x in f if x.severity == "Low"),
        ),
        schema_version="1.0",
    )


def _profile(
    tmp_path: Path,
    *,
    limitations: list[str] | None = None,
) -> RepositoryProfile:
    return RepositoryProfile(
        project_name="test",
        repository=str(tmp_path),
        branch="main",
        commit="abc",
        detected_languages=["Python"],
        detected_frameworks=[],
        package_managers=[],
        analysis_confidence="High",
        limitations=limitations or [],
    )


ROADMAP_TEMPLATE = (
    "# Roadmap\n\n{{ summary_section }}\n\n{{ roadmap_buckets }}\n\n{{ work_package_list }}"
)

HANDOFF_TEMPLATE = (
    "# Handoff\n{{ executive_summary }}\n{{ top_risks_table }}\n{{ recommended_first_actions }}"
)


# ── Roadmap template coverage ────────────────────────────────────────


class TestRoadmapTemplateCov:
    def test_roadmap_with_template(self, tmp_path: Path) -> None:
        from pharabius.core.planner import render_remediation_roadmap

        t = tmp_path / ".ai-debt" / "templates"
        t.mkdir(parents=True)
        (t / "remediation-roadmap.md").write_text(
            ROADMAP_TEMPLATE,
            encoding="utf-8",
        )
        result = render_remediation_roadmap(
            _register(tmp_path),
            [_pkg()],
            repository_root=tmp_path,
        )
        assert "# Roadmap" in result
        assert "Total findings" in result
        assert "WP-001" in result

    def test_roadmap_template_no_packages(self, tmp_path: Path) -> None:
        from pharabius.core.planner import render_remediation_roadmap

        t = tmp_path / ".ai-debt" / "templates"
        t.mkdir(parents=True)
        (t / "remediation-roadmap.md").write_text(
            ROADMAP_TEMPLATE,
            encoding="utf-8",
        )
        reg = DebtRegister(
            project_name="test",
            repository=str(tmp_path),
            branch="main",
            commit="abc",
            findings=[],
            summary=DebtRegisterSummary(
                total_findings=0,
                critical=0,
                high=0,
                medium=0,
                low=0,
            ),
            schema_version="1.0",
        )
        result = render_remediation_roadmap(
            reg,
            [],
            repository_root=tmp_path,
        )
        assert "# Roadmap" in result
        assert "No work packages" in result

    def test_roadmap_builtin_no_override(self, tmp_path: Path) -> None:
        from pharabius.core.planner import render_remediation_roadmap

        result = render_remediation_roadmap(
            _register(tmp_path),
            [_pkg()],
            repository_root=tmp_path,
        )
        assert "# Remediation Roadmap" in result


# ── Handoff template coverage ────────────────────────────────────────


class TestHandoffTemplateCov:
    def test_handoff_with_template_findings(self, tmp_path: Path) -> None:
        from pharabius.core.planner import render_handoff_summary

        t = tmp_path / ".ai-debt" / "templates"
        t.mkdir(parents=True)
        (t / "handoff-summary.md").write_text(
            HANDOFF_TEMPLATE,
            encoding="utf-8",
        )
        result = render_handoff_summary(
            _profile(tmp_path),
            _register(tmp_path),
            [_pkg()],
            repository_root=tmp_path,
        )
        assert "# Handoff" in result
        assert "TD-TEST-001" in result

    def test_handoff_template_no_findings(self, tmp_path: Path) -> None:
        from pharabius.core.planner import render_handoff_summary

        t = tmp_path / ".ai-debt" / "templates"
        t.mkdir(parents=True)
        (t / "handoff-summary.md").write_text(
            HANDOFF_TEMPLATE,
            encoding="utf-8",
        )
        reg = DebtRegister(
            project_name="test",
            repository=str(tmp_path),
            branch="main",
            commit="abc",
            findings=[],
            summary=DebtRegisterSummary(
                total_findings=0,
                critical=0,
                high=0,
                medium=0,
                low=0,
            ),
            schema_version="1.0",
        )
        result = render_handoff_summary(
            _profile(tmp_path),
            reg,
            [],
            repository_root=tmp_path,
        )
        assert "# Handoff" in result
        assert "No findings" in result

    def test_handoff_template_with_limitations(self, tmp_path: Path) -> None:
        from pharabius.core.planner import render_handoff_summary

        t = tmp_path / ".ai-debt" / "templates"
        t.mkdir(parents=True)
        (t / "handoff-summary.md").write_text(
            "# H\n{{ uncertainties }}",
            encoding="utf-8",
        )
        result = render_handoff_summary(
            _profile(tmp_path, limitations=["No coverage"]),
            _register(tmp_path),
            [_pkg()],
            repository_root=tmp_path,
        )
        assert "No coverage" in result

    def test_handoff_template_no_packages(self, tmp_path: Path) -> None:
        from pharabius.core.planner import render_handoff_summary

        t = tmp_path / ".ai-debt" / "templates"
        t.mkdir(parents=True)
        (t / "handoff-summary.md").write_text(
            "# H\n{{ recommended_first_actions }}",
            encoding="utf-8",
        )
        result = render_handoff_summary(
            _profile(tmp_path),
            _register(tmp_path),
            [],
            repository_root=tmp_path,
        )
        assert "Validate that repository evidence" in result

    def test_handoff_builtin_no_override(self, tmp_path: Path) -> None:
        from pharabius.core.planner import render_handoff_summary

        result = render_handoff_summary(
            _profile(tmp_path),
            _register(tmp_path),
            [_pkg()],
            repository_root=tmp_path,
        )
        assert "# AI Technical Debt Handoff Summary" in result


# ── write_plan coverage ──────────────────────────────────────────────


class TestWritePlanCov:
    def test_write_plan_with_governance_file(self, tmp_path: Path) -> None:
        from pharabius.core.planner import write_plan
        from pharabius.schemas.evidence import EvidenceItem, EvidenceStore

        workspace = tmp_path / ".ai-debt"
        workspace.mkdir()

        store = EvidenceStore(
            evidence=[
                EvidenceItem(
                    evidence_id="EVD-000001",
                    type="python_manifest",
                    category="dependency",
                    summary="Manifest",
                    tags=[],
                )
            ],
            schema_version="1.0",
        )
        (workspace / "evidence.json").write_text(
            store.model_dump_json(indent=2),
            encoding="utf-8",
        )
        (workspace / "project-profile.json").write_text(
            _profile(tmp_path).model_dump_json(indent=2),
            encoding="utf-8",
        )

        reg = _register(tmp_path, [_finding("TD-DEP-001", score=15)])
        (workspace / "debt-register.json").write_text(
            reg.model_dump_json(indent=2),
            encoding="utf-8",
        )
        (workspace / "governance.yaml").write_text(
            yaml.dump({"preset": "default"}),
            encoding="utf-8",
        )

        result = write_plan(tmp_path)
        assert Path(result.handoff_summary_path).exists()
        assert Path(result.remediation_roadmap_path).exists()
        assert len(result.work_package_paths) >= 1


# ── Template engine edge cases ───────────────────────────────────────


class TestTemplateEngineEdgeCov:
    def test_load_template_read_error(self, tmp_path: Path) -> None:
        f = tmp_path / "test.md"
        f.mkdir()  # directory causes read error
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = load_template_file(f)
            assert result is None
            assert any("Could not read" in str(x.message) for x in w)

    def test_unknown_placeholder_no_artifact(self) -> None:
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            render_template("{{ unknown }}", {})
            assert any("Unknown" in str(x.message) for x in w)

    def test_non_templateable_returns_none(self, tmp_path: Path) -> None:
        assert load_resolved_template("random.md", tmp_path) is None

    def test_resolve_default_no_override(self, tmp_path: Path) -> None:
        result = resolve_template_path(
            "work-package.md",
            tmp_path,
            preset="default",
        )
        assert result is None or result.exists()


# ── Governance loader edge case ──────────────────────────────────────


class TestGovernanceLoaderEdgeCov:
    def test_unreadable_directory_as_governance(self, tmp_path: Path) -> None:
        ai_debt = tmp_path / ".ai-debt"
        ai_debt.mkdir()
        (ai_debt / "governance.yaml").mkdir()
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            g = load_governance(tmp_path)
            assert g.preset == "default"


# ── Work package built-in with repository_root ───────────────────────


class TestWorkPackageBuiltinCov:
    def test_builtin_no_template(self, tmp_path: Path) -> None:
        from pharabius.core.planner import render_work_package_markdown

        result = render_work_package_markdown(
            _pkg(),
            _finding(),
            repository_root=tmp_path,
        )
        assert "## Status" in result

    def test_with_governance_object(self, tmp_path: Path) -> None:
        from pharabius.core.planner import render_work_package_markdown

        gov = GovernanceConfig(preset="default")
        result = render_work_package_markdown(
            _pkg(),
            _finding(),
            repository_root=tmp_path,
            governance=gov,
        )
        assert "## Status" in result

    def test_no_root(self) -> None:
        from pharabius.core.planner import render_work_package_markdown

        result = render_work_package_markdown(_pkg(), _finding())
        assert "## Status" in result
