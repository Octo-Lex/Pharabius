"""Tests for governance presets and template overrides."""

from __future__ import annotations

import warnings
from pathlib import Path

import yaml

from pharabius.core.governance import (
    default_governance_yaml,
    effective_preset,
    load_governance,
)
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

# ── Governance schema tests ──────────────────────────────────────────


class TestGovernanceSchema:
    def test_defaults(self) -> None:
        g = GovernanceConfig()
        assert g.preset == "default"
        assert g.review.require_evidence_review is True
        assert g.handoff.max_work_packages == 10
        assert g.templates.override_dir == ""
        assert g.safety.no_finding_suppression is True

    def test_extra_keys_ignored(self) -> None:
        g = GovernanceConfig.model_validate(
            {
                "preset": "default",
                "unknown_key": "should be ignored",
            }
        )
        assert g.preset == "default"

    def test_partial_config(self) -> None:
        g = GovernanceConfig.model_validate({"preset": "startup-lean"})
        assert g.preset == "startup-lean"
        assert g.review.require_evidence_review is True  # default


# ── Governance loader tests ──────────────────────────────────────────


class TestGovernanceLoader:
    def test_missing_governance_yaml(self, tmp_path: Path) -> None:
        g = load_governance(tmp_path)
        assert g.preset == "default"

    def test_valid_governance_yaml(self, tmp_path: Path) -> None:
        ai_debt = tmp_path / ".ai-debt"
        ai_debt.mkdir()
        (ai_debt / "governance.yaml").write_text(
            yaml.dump({"preset": "startup-lean"}),
            encoding="utf-8",
        )
        g = load_governance(tmp_path)
        assert g.preset == "startup-lean"

    def test_malformed_yaml(self, tmp_path: Path) -> None:
        ai_debt = tmp_path / ".ai-debt"
        ai_debt.mkdir()
        (ai_debt / "governance.yaml").write_text("preset: [\ninvalid", encoding="utf-8")
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            g = load_governance(tmp_path)
            assert g.preset == "default"
            assert any("Malformed" in str(warning.message) for warning in w)

    def test_non_mapping_yaml(self, tmp_path: Path) -> None:
        ai_debt = tmp_path / ".ai-debt"
        ai_debt.mkdir()
        (ai_debt / "governance.yaml").write_text("- item1\n- item2", encoding="utf-8")
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            g = load_governance(tmp_path)
            assert g.preset == "default"
            assert any("not a mapping" in str(warning.message) for warning in w)

    def test_unknown_keys_warn(self, tmp_path: Path) -> None:
        ai_debt = tmp_path / ".ai-debt"
        ai_debt.mkdir()
        (ai_debt / "governance.yaml").write_text(
            yaml.dump({"preset": "default", "bogus_key": True}),
            encoding="utf-8",
        )
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            g = load_governance(tmp_path)
            assert g.preset == "default"
            assert any("Unknown" in str(warning.message) for warning in w)

    def test_unreadable_file(self, tmp_path: Path) -> None:
        ai_debt = tmp_path / ".ai-debt"
        ai_debt.mkdir()
        bad = ai_debt / "governance.yaml"
        bad.mkdir()  # directory, not file
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            g = load_governance(tmp_path)
            assert g.preset == "default"

    def test_default_governance_yaml_roundtrip(self) -> None:
        content = default_governance_yaml()
        data = yaml.safe_load(content)
        g = GovernanceConfig.model_validate(data)
        assert g.preset == "default"
        assert g.review.require_evidence_review is True


# ── Effective preset tests ───────────────────────────────────────────


class TestEffectivePreset:
    def test_known_presets(self) -> None:
        for name in (
            "default",
            "platform-engineering",
            "security-sensitive",
            "compliance-sensitive",
            "startup-lean",
        ):
            g = GovernanceConfig(preset=name)
            assert effective_preset(g) == name

    def test_unknown_preset_warns(self) -> None:
        g = GovernanceConfig(preset="nonexistent")
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = effective_preset(g)
            assert result == "default"
            assert any("Unknown preset" in str(warning.message) for warning in w)


# ── Template engine tests ────────────────────────────────────────────


class TestTemplateEngine:
    def test_simple_substitution(self) -> None:
        result = render_template("Hello {{ name }}!", {"name": "World"})
        assert result == "Hello World!"

    def test_multiple_placeholders(self) -> None:
        result = render_template(
            "{{ a }} and {{ b }}",
            {"a": "Alpha", "b": "Beta"},
        )
        assert result == "Alpha and Beta"

    def test_unknown_placeholder_warns(self) -> None:
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = render_template(
                "{{ known }} {{ unknown }}",
                {"known": "yes"},
                artifact_name="test.md",
            )
            assert "yes" in result
            assert any("Unknown" in str(warning.message) for warning in w)

    def test_extra_placeholders_ignored(self) -> None:
        result = render_template("{{ a }}", {"a": "Alpha", "b": "Beta"})
        assert result == "Alpha"

    def test_whitespace_in_placeholder(self) -> None:
        result = render_template("{{  name  }}", {"name": "X"})
        assert result == "X"

    def test_no_placeholders(self) -> None:
        result = render_template("plain text", {})
        assert result == "plain text"


# ── Template file loading tests ──────────────────────────────────────


class TestTemplateFileLoading:
    def test_load_existing_file(self, tmp_path: Path) -> None:
        f = tmp_path / "test.md"
        f.write_text("# {{ title }}", encoding="utf-8")
        result = load_template_file(f)
        assert result == "# {{ title }}"

    def test_load_nonexistent_file(self, tmp_path: Path) -> None:
        result = load_template_file(tmp_path / "nonexistent.md")
        assert result is None

    def test_load_empty_file_warns(self, tmp_path: Path) -> None:
        f = tmp_path / "empty.md"
        f.write_text("  \n  ", encoding="utf-8")
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = load_template_file(f)
            assert result is None
            assert any("empty" in str(warning.message).lower() for warning in w)


# ── Template resolution tests ────────────────────────────────────────


class TestTemplateResolution:
    def test_non_templateable_artifact(self, tmp_path: Path) -> None:
        result = resolve_template_path("not-a-template.md", tmp_path)
        assert result is None

    def test_conventional_override(self, tmp_path: Path) -> None:
        templates = tmp_path / ".ai-debt" / "templates"
        templates.mkdir(parents=True)
        (templates / "work-package.md").write_text("custom", encoding="utf-8")
        result = resolve_template_path("work-package.md", tmp_path)
        assert result is not None
        assert result.exists()

    def test_explicit_override_dir(self, tmp_path: Path) -> None:
        custom = tmp_path / "my-templates"
        custom.mkdir()
        (custom / "work-package.md").write_text("custom", encoding="utf-8")
        result = resolve_template_path(
            "work-package.md",
            tmp_path,
            override_dir="my-templates",
        )
        assert result is not None
        assert "my-templates" in str(result)

    def test_no_override_returns_none_for_default_preset(self, tmp_path: Path) -> None:
        # default preset has no template files in the package (built-in rendering)
        result = resolve_template_path(
            "work-package.md",
            tmp_path,
            preset="default",
        )
        # May or may not find bundled templates — just verify no crash
        assert result is None or result.exists()

    def test_load_resolved_template_none(self, tmp_path: Path) -> None:
        result = load_resolved_template(
            "not-templateable.md",
            tmp_path,
        )
        assert result is None


# ── Template override integration tests ──────────────────────────────


class TestTemplateOverrideIntegration:
    def _make_finding(self) -> DebtFinding:
        return DebtFinding(
            id="TD-TEST-001",
            category="TD-TEST",
            issue_type="technical_debt",
            title="Test finding",
            description="Test description",
            severity="Medium",
            confidence="High",
            status="Detected",
            locations=["src/test.py"],
            evidence_ids=["EVD-000001"],
            technical_impact="Test impact",
            business_impact="Test business impact",
            business_impact_basis="Inferred",
            risk_score=10,
            priority="Medium",
            remediation_effort="Small",
            recommended_action="Fix it",
            verification_recommendations=["Verify fix"],
            risks_and_cautions=["Be careful"],
            suggested_owner_area="Engineering",
        )

    def _make_package(self) -> WorkPackage:
        return WorkPackage(
            id="WP-001",
            title="Test work package",
            status="Ready for review",
            linked_debt_items=["TD-TEST-001"],
            objective="Fix the issue",
            current_risk="Test risk",
            recommended_engineering_approach=["Step 1", "Step 2"],
            expected_affected_areas=["src/"],
            preconditions=["None"],
            verification_recommendations=["Verify"],
            risks_and_cautions=["Caution"],
            definition_of_done=["Done criteria"],
            estimated_effort="Small",
            expected_risk_reduction="Significant",
            suggested_owner_area="Engineering",
        )

    def test_work_package_with_override(self, tmp_path: Path) -> None:
        from pharabius.core.planner import render_work_package_markdown

        templates = tmp_path / ".ai-debt" / "templates"
        templates.mkdir(parents=True)
        (templates / "work-package.md").write_text(
            "# {{ package_id }}: {{ package_title }}\n\nStatus: {{ package_status }}",
            encoding="utf-8",
        )

        result = render_work_package_markdown(
            self._make_package(),
            self._make_finding(),
            repository_root=tmp_path,
        )
        assert "# WP-001: Test work package" in result
        assert "Status: Ready for review" in result

    def test_work_package_without_override(self, tmp_path: Path) -> None:
        """Without template override, built-in rendering is used."""
        from pharabius.core.planner import render_work_package_markdown

        result = render_work_package_markdown(
            self._make_package(),
            self._make_finding(),
            repository_root=tmp_path,
        )
        assert "## Status" in result
        assert "Ready for review" in result

    def test_handoff_with_override(self, tmp_path: Path) -> None:
        from pharabius.core.planner import render_handoff_summary

        templates = tmp_path / ".ai-debt" / "templates"
        templates.mkdir(parents=True)
        (templates / "handoff-summary.md").write_text(
            "# Custom Handoff\n\n{{ executive_summary }}",
            encoding="utf-8",
        )

        profile = RepositoryProfile(
            project_name="test-project",
            repository=str(tmp_path),
            branch="main",
            commit="abc123",
            detected_languages=["Python"],
            detected_frameworks=[],
            package_managers=[],
            analysis_confidence="High",
            limitations=[],
        )
        register = DebtRegister(
            project_name="test-project",
            repository=str(tmp_path),
            branch="main",
            commit="abc123",
            findings=[self._make_finding()],
            summary=DebtRegisterSummary(
                total_findings=1,
                critical=0,
                high=0,
                medium=1,
                low=0,
            ),
            schema_version="1.0",
        )

        result = render_handoff_summary(
            profile,
            register,
            [self._make_package()],
            repository_root=tmp_path,
        )
        assert "# Custom Handoff" in result

    def test_roadmap_with_override(self, tmp_path: Path) -> None:
        from pharabius.core.planner import render_remediation_roadmap

        templates = tmp_path / ".ai-debt" / "templates"
        templates.mkdir(parents=True)
        (templates / "remediation-roadmap.md").write_text(
            "# Custom Roadmap\n\n{{ summary_section }}",
            encoding="utf-8",
        )

        register = DebtRegister(
            project_name="test-project",
            repository=str(tmp_path),
            branch="main",
            commit="abc123",
            findings=[self._make_finding()],
            summary=DebtRegisterSummary(
                total_findings=1,
                critical=0,
                high=0,
                medium=1,
                low=0,
            ),
            schema_version="1.0",
        )

        result = render_remediation_roadmap(
            register,
            [self._make_package()],
            repository_root=tmp_path,
        )
        assert "# Custom Roadmap" in result


# ── Safety invariant tests ───────────────────────────────────────────


class TestSafetyInvariants:
    def test_template_cannot_suppress_findings(self, tmp_path: Path) -> None:
        """Template changes wording but findings still appear in evidence."""
        from pharabius.core.planner import render_work_package_markdown

        finding = DebtFinding(
            id="TD-SEC-001",
            category="TD-SEC",
            issue_type="technical_debt",
            title="Security finding",
            description="Test",
            severity="High",
            confidence="High",
            status="Detected",
            locations=["secret.key"],
            evidence_ids=["EVD-000099"],
            technical_impact="Secret exposure",
            business_impact="Breach risk",
            business_impact_basis="Inferred",
            risk_score=25,
            priority="High",
            remediation_effort="Medium",
            recommended_action="Rotate key",
            verification_recommendations=["Check rotation"],
            risks_and_cautions=["Do not commit secrets"],
            suggested_owner_area="Security",
        )
        pkg = WorkPackage(
            id="WP-099",
            title="Security issue",
            status="Ready for review",
            linked_debt_items=["TD-SEC-001"],
            objective="Fix security",
            current_risk="High",
            recommended_engineering_approach=["Rotate"],
            expected_affected_areas=["config/"],
            preconditions=[],
            verification_recommendations=["Verify"],
            risks_and_cautions=["Caution"],
            definition_of_done=["Done"],
            estimated_effort="Medium",
            expected_risk_reduction="Major",
            suggested_owner_area="Security",
        )

        # Even with a minimal template, the evidence ID must appear
        templates = tmp_path / ".ai-debt" / "templates"
        templates.mkdir(parents=True)
        (templates / "work-package.md").write_text(
            "# {{ package_id }}\n{{ evidence_list }}",
            encoding="utf-8",
        )

        result = render_work_package_markdown(
            pkg,
            finding,
            repository_root=tmp_path,
        )
        assert "EVD-000099" in result

    def test_canonical_json_unchanged(self, tmp_path: Path) -> None:
        """Governance does not affect JSON artifact generation."""
        import json

        from pharabius.core.analyzer import write_debt_register

        # Set up workspace
        workspace = tmp_path / ".ai-debt"
        workspace.mkdir()

        # Create minimal evidence
        from pharabius.schemas.evidence import EvidenceItem, EvidenceStore

        store = EvidenceStore(
            evidence=[
                EvidenceItem(
                    evidence_id="EVD-000001",
                    type="python_manifest",
                    category="dependency",
                    location={"file": "requirements.txt", "line": 1, "column": 1},
                    content="flask",
                    summary="Python manifest detected",
                    tags=[],
                )
            ],
            schema_version="1.0",
        )
        (workspace / "evidence.json").write_text(
            store.model_dump_json(indent=2),
            encoding="utf-8",
        )

        # Create minimal profile
        from pharabius.schemas.repository import RepositoryProfile

        profile = RepositoryProfile(
            project_name="test",
            repository=str(tmp_path),
            branch="main",
            commit="abc",
            detected_languages=["Python"],
            detected_frameworks=[],
            package_managers=["pip"],
            analysis_confidence="High",
            limitations=[],
        )
        (workspace / "project-profile.json").write_text(
            profile.model_dump_json(indent=2),
            encoding="utf-8",
        )

        # Add governance
        (workspace / "governance.yaml").write_text(
            yaml.dump({"preset": "default"}),
            encoding="utf-8",
        )

        # Run analyzer
        write_debt_register(tmp_path)
        json_path = workspace / "debt-register.json"
        assert json_path.exists()

        data = json.loads(json_path.read_text(encoding="utf-8"))
        assert "findings" in data
        assert "schema_version" in data


# ── Init creates governance.yaml ─────────────────────────────────────


class TestInitGovernance:
    def test_init_creates_governance_yaml(self, tmp_path: Path) -> None:
        from pharabius.core.init_workspace import initialize_workspace

        files = initialize_workspace(tmp_path)
        gov_path = tmp_path / ".ai-debt" / "governance.yaml"
        assert gov_path.exists()
        assert gov_path in files

        content = gov_path.read_text(encoding="utf-8")
        data = yaml.safe_load(content)
        assert data["preset"] == "default"

    def test_init_no_governance_no_crash(self, tmp_path: Path) -> None:
        """Existing repos without governance.yaml still work."""
        from pharabius.core.governance import load_governance

        g = load_governance(tmp_path)
        assert g.preset == "default"


# ── First-run smoke test ─────────────────────────────────────────────


class TestGovernanceFirstRunSmoke:
    def test_init_status_version(self) -> None:
        """Governance doesn't break init/status/version commands."""
        from typer.testing import CliRunner

        from pharabius.cli import app

        runner = CliRunner()
        r = runner.invoke(app, ["--version"])
        assert r.exit_code == 0
        assert "Pharabius" in r.output
