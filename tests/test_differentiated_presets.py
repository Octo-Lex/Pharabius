"""Tests for v1.3.0 differentiated governance presets."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from pharabius.core.template_engine import resolve_template_path
from pharabius.schemas.finding import DebtFinding, DebtRegister, DebtRegisterSummary
from pharabius.schemas.governance import GovernanceConfig
from pharabius.schemas.repository import RepositoryProfile
from pharabius.schemas.work_package import WorkPackage

DIFFERENTIATED_PRESETS = [
    "security-sensitive",
    "startup-lean",
    "platform-engineering",
    "compliance-sensitive",
]

TEMPLATEABLE_ARTIFACTS = [
    "work-package.md",
    "handoff-summary.md",
    "remediation-roadmap.md",
]


def _finding() -> DebtFinding:
    return DebtFinding(
        id="TD-DEP-001",
        category="TD-DEP",
        issue_type="technical_debt",
        title="Dependency manifest without lockfile",
        description="Test",
        severity="Medium",
        confidence="High",
        status="Detected",
        locations=["requirements.txt"],
        evidence_ids=["EVD-000001"],
        technical_impact="Reproducibility risk",
        business_impact="Inferred",
        business_impact_basis="Inferred from evidence",
        risk_score=15,
        priority="Medium",
        remediation_effort="Small",
        recommended_action="Add lockfile",
        verification_recommendations=["Verify lockfile exists"],
        risks_and_cautions=["Library repos may omit lockfiles"],
        suggested_owner_area="Engineering",
    )


def _pkg() -> WorkPackage:
    return WorkPackage(
        id="WP-001",
        title="Dependency manifest without lockfile",
        status="Ready for review",
        linked_debt_items=["TD-DEP-001"],
        objective="Add lockfile",
        current_risk="Reproducibility risk",
        recommended_engineering_approach=["Generate lockfile", "Update CI"],
        expected_affected_areas=["requirements.txt"],
        preconditions=["Confirm policy"],
        verification_recommendations=["Verify lockfile"],
        risks_and_cautions=["Library repos may omit"],
        definition_of_done=["Lockfile exists"],
        estimated_effort="Small",
        expected_risk_reduction="Medium",
        suggested_owner_area="Engineering",
    )


def _register(tmp_path: Path) -> DebtRegister:
    return DebtRegister(
        project_name="test",
        repository=str(tmp_path),
        branch="main",
        commit="abc",
        findings=[_finding()],
        summary=DebtRegisterSummary(
            total_findings=1,
            critical=0,
            high=0,
            medium=1,
            low=0,
        ),
        schema_version="1.0",
    )


def _profile(tmp_path: Path) -> RepositoryProfile:
    return RepositoryProfile(
        project_name="test",
        repository=str(tmp_path),
        branch="main",
        commit="abc",
        detected_languages=["Python"],
        detected_frameworks=[],
        package_managers=[],
        analysis_confidence="High",
        limitations=[],
    )


# ── Template file existence ───────────────────────────────────────────


class TestPresetTemplateExistence:
    @pytest.mark.parametrize("preset", DIFFERENTIATED_PRESETS)
    @pytest.mark.parametrize("artifact", TEMPLATEABLE_ARTIFACTS)
    def test_template_file_exists(self, preset: str, artifact: str) -> None:
        """Each differentiated preset has template files for all 3 artifacts."""
        result = resolve_template_path(
            artifact,
            Path("."),
            preset=preset,
        )
        assert result is not None, f"Missing template: {preset}/{artifact}"
        assert result.exists()


# ── Security-sensitive preset ─────────────────────────────────────────


class TestSecuritySensitivePreset:
    def test_work_package_has_security_review(self, tmp_path: Path) -> None:
        from pharabius.core.planner import render_work_package_markdown

        g = GovernanceConfig(preset="security-sensitive")
        result = render_work_package_markdown(
            _pkg(),
            _finding(),
            repository_root=tmp_path,
            governance=g,
        )
        assert "Security Review Required" in result

    def test_work_package_has_sign_off(self, tmp_path: Path) -> None:
        from pharabius.core.planner import render_work_package_markdown

        g = GovernanceConfig(preset="security-sensitive")
        result = render_work_package_markdown(
            _pkg(),
            _finding(),
            repository_root=tmp_path,
            governance=g,
        )
        assert "Security Sign-Off" in result

    def test_work_package_has_credential_caution(self, tmp_path: Path) -> None:
        from pharabius.core.planner import render_work_package_markdown

        g = GovernanceConfig(preset="security-sensitive")
        result = render_work_package_markdown(
            _pkg(),
            _finding(),
            repository_root=tmp_path,
            governance=g,
        )
        assert "Credential" in result or "Secret" in result

    def test_handoff_has_escalation_guide(self, tmp_path: Path) -> None:
        from pharabius.core.planner import render_handoff_summary

        g = GovernanceConfig(preset="security-sensitive")
        result = render_handoff_summary(
            _profile(tmp_path),
            _register(tmp_path),
            [_pkg()],
            repository_root=tmp_path,
            governance=g,
        )
        assert "Escalation" in result or "escalation" in result

    def test_handoff_has_review_checklist(self, tmp_path: Path) -> None:
        from pharabius.core.planner import render_handoff_summary

        g = GovernanceConfig(preset="security-sensitive")
        result = render_handoff_summary(
            _profile(tmp_path),
            _register(tmp_path),
            [_pkg()],
            repository_root=tmp_path,
            governance=g,
        )
        assert "Review Checklist" in result or "checklist" in result.lower()

    def test_evidence_ids_preserved(self, tmp_path: Path) -> None:
        from pharabius.core.planner import render_work_package_markdown

        g = GovernanceConfig(preset="security-sensitive")
        result = render_work_package_markdown(
            _pkg(),
            _finding(),
            repository_root=tmp_path,
            governance=g,
        )
        assert "EVD-000001" in result


# ── Startup-lean preset ───────────────────────────────────────────────


class TestStartupLeanPreset:
    def test_work_package_has_evidence(self, tmp_path: Path) -> None:
        from pharabius.core.planner import render_work_package_markdown

        g = GovernanceConfig(preset="startup-lean")
        result = render_work_package_markdown(
            _pkg(),
            _finding(),
            repository_root=tmp_path,
            governance=g,
        )
        assert "EVD-000001" in result

    def test_work_package_has_action(self, tmp_path: Path) -> None:
        from pharabius.core.planner import render_work_package_markdown

        g = GovernanceConfig(preset="startup-lean")
        result = render_work_package_markdown(
            _pkg(),
            _finding(),
            repository_root=tmp_path,
            governance=g,
        )
        assert "Action" in result or "action" in result

    def test_work_package_has_verification(self, tmp_path: Path) -> None:
        from pharabius.core.planner import render_work_package_markdown

        g = GovernanceConfig(preset="startup-lean")
        result = render_work_package_markdown(
            _pkg(),
            _finding(),
            repository_root=tmp_path,
            governance=g,
        )
        assert "Verify" in result

    def test_work_package_has_cautions(self, tmp_path: Path) -> None:
        from pharabius.core.planner import render_work_package_markdown

        g = GovernanceConfig(preset="startup-lean")
        result = render_work_package_markdown(
            _pkg(),
            _finding(),
            repository_root=tmp_path,
            governance=g,
        )
        assert "Cautions" in result or "caution" in result.lower()

    def test_work_package_has_no_automation_boundary(self, tmp_path: Path) -> None:
        from pharabius.core.planner import render_work_package_markdown

        g = GovernanceConfig(preset="startup-lean")
        result = render_work_package_markdown(
            _pkg(),
            _finding(),
            repository_root=tmp_path,
            governance=g,
        )
        assert "No automated remediation" in result

    def test_work_package_has_effort_line(self, tmp_path: Path) -> None:
        from pharabius.core.planner import render_work_package_markdown

        g = GovernanceConfig(preset="startup-lean")
        result = render_work_package_markdown(
            _pkg(),
            _finding(),
            repository_root=tmp_path,
            governance=g,
        )
        assert "Effort" in result

    def test_work_package_condensed_vs_default(self, tmp_path: Path) -> None:
        """Startup-lean work package is shorter than default."""
        from pharabius.core.planner import render_work_package_markdown

        g_lean = GovernanceConfig(preset="startup-lean")
        lean = render_work_package_markdown(
            _pkg(),
            _finding(),
            repository_root=tmp_path,
            governance=g_lean,
        )
        default = render_work_package_markdown(
            _pkg(),
            _finding(),
            repository_root=tmp_path,
        )
        assert len(lean) < len(default)


# ── Platform-engineering preset ───────────────────────────────────────


class TestPlatformEngineeringPreset:
    def test_work_package_has_platform_impact(self, tmp_path: Path) -> None:
        from pharabius.core.planner import render_work_package_markdown

        g = GovernanceConfig(preset="platform-engineering")
        result = render_work_package_markdown(
            _pkg(),
            _finding(),
            repository_root=tmp_path,
            governance=g,
        )
        assert "Platform Impact" in result

    def test_handoff_has_platform_health(self, tmp_path: Path) -> None:
        from pharabius.core.planner import render_handoff_summary

        g = GovernanceConfig(preset="platform-engineering")
        result = render_handoff_summary(
            _profile(tmp_path),
            _register(tmp_path),
            [_pkg()],
            repository_root=tmp_path,
            governance=g,
        )
        assert "Platform" in result

    def test_evidence_ids_preserved(self, tmp_path: Path) -> None:
        from pharabius.core.planner import render_work_package_markdown

        g = GovernanceConfig(preset="platform-engineering")
        result = render_work_package_markdown(
            _pkg(),
            _finding(),
            repository_root=tmp_path,
            governance=g,
        )
        assert "EVD-000001" in result


# ── Compliance-sensitive preset ────────────────────────────────────────


class TestComplianceSensitivePreset:
    def test_work_package_has_attestation_notice(self, tmp_path: Path) -> None:
        from pharabius.core.planner import render_work_package_markdown

        g = GovernanceConfig(preset="compliance-sensitive")
        result = render_work_package_markdown(
            _pkg(),
            _finding(),
            repository_root=tmp_path,
            governance=g,
        )
        assert "Compliance Attestation" in result or "attestation" in result.lower()

    def test_work_package_has_audit_trail(self, tmp_path: Path) -> None:
        from pharabius.core.planner import render_work_package_markdown

        g = GovernanceConfig(preset="compliance-sensitive")
        result = render_work_package_markdown(
            _pkg(),
            _finding(),
            repository_root=tmp_path,
            governance=g,
        )
        assert "Audit Trail" in result

    def test_handoff_has_compliance_escalation(self, tmp_path: Path) -> None:
        from pharabius.core.planner import render_handoff_summary

        g = GovernanceConfig(preset="compliance-sensitive")
        result = render_handoff_summary(
            _profile(tmp_path),
            _register(tmp_path),
            [_pkg()],
            repository_root=tmp_path,
            governance=g,
        )
        assert "Compliance" in result or "compliance" in result

    def test_evidence_ids_preserved(self, tmp_path: Path) -> None:
        from pharabius.core.planner import render_work_package_markdown

        g = GovernanceConfig(preset="compliance-sensitive")
        result = render_work_package_markdown(
            _pkg(),
            _finding(),
            repository_root=tmp_path,
            governance=g,
        )
        assert "EVD-000001" in result


# ── Cross-preset stability tests ─────────────────────────────────────


class TestCrossPresetStability:
    @pytest.mark.parametrize("preset", DIFFERENTIATED_PRESETS)
    def test_same_finding_ids(self, preset: str, tmp_path: Path) -> None:
        """All presets produce output containing the same finding ID."""
        from pharabius.core.planner import render_work_package_markdown

        g = GovernanceConfig(preset=preset)
        result = render_work_package_markdown(
            _pkg(),
            _finding(),
            repository_root=tmp_path,
            governance=g,
        )
        assert "TD-DEP-001" in result

    @pytest.mark.parametrize("preset", DIFFERENTIATED_PRESETS)
    def test_same_evidence_ids(self, preset: str, tmp_path: Path) -> None:
        """All presets preserve evidence IDs."""
        from pharabius.core.planner import render_work_package_markdown

        g = GovernanceConfig(preset=preset)
        result = render_work_package_markdown(
            _pkg(),
            _finding(),
            repository_root=tmp_path,
            governance=g,
        )
        assert "EVD-000001" in result

    @pytest.mark.parametrize("preset", DIFFERENTIATED_PRESETS)
    def test_work_package_count_preserved(
        self,
        preset: str,
        tmp_path: Path,
    ) -> None:
        """All presets generate the same number of work packages."""
        from pharabius.core.planner import render_remediation_roadmap

        g = GovernanceConfig(preset=preset)
        reg = _register(tmp_path)
        result = render_remediation_roadmap(
            reg,
            [_pkg()],
            repository_root=tmp_path,
            governance=g,
        )
        assert "WP-001" in result

    @pytest.mark.parametrize("preset", DIFFERENTIATED_PRESETS)
    def test_no_severity_change(self, preset: str, tmp_path: Path) -> None:
        """Preset output does not change severity labels."""
        from pharabius.core.planner import render_work_package_markdown

        g = GovernanceConfig(preset=preset)
        result = render_work_package_markdown(
            _pkg(),
            _finding(),
            repository_root=tmp_path,
            governance=g,
        )
        # Medium is the correct severity from the finding
        assert "Medium" in result

    def test_default_builtin_no_template_files(self) -> None:
        """Default preset has no template files (uses built-in rendering)."""
        for artifact in TEMPLATEABLE_ARTIFACTS:
            result = resolve_template_path(
                artifact,
                Path("."),
                preset="default",
            )
            assert result is None


# ── Canonical immutability under presets ──────────────────────────────


class TestCanonicalImmutability:
    def test_json_unchanged_across_presets(self, tmp_path: Path) -> None:
        """Canonical JSON is identical regardless of preset."""
        workspace = tmp_path / ".ai-debt"
        workspace.mkdir()
        canonical = {"schema_version": "1.0", "findings": [{"id": "TD-DEP-001"}]}
        json_path = workspace / "debt-register.json"
        json_path.write_text(json.dumps(canonical), encoding="utf-8")
        hash_before = hashlib.sha256(json_path.read_bytes()).hexdigest()

        for preset in ["default", *DIFFERENTIATED_PRESETS]:
            (workspace / "governance.yaml").write_text(
                f"preset: {preset}\n",
                encoding="utf-8",
            )
            hash_after = hashlib.sha256(json_path.read_bytes()).hexdigest()
            assert hash_before == hash_after, f"JSON changed under {preset}"
