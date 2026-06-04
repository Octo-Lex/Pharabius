"""v3.21.0 — Signal family-boundary regression matrix.

Prevents overlap drift between adjacent families.
Each test covers a known ambiguous case and asserts correct routing.
"""

from __future__ import annotations

from pharabius.core.signals.models import SignalFamily

# ═══════════════════════════════════════════════════════════════════════
# Boundary matrix tests
# ═══════════════════════════════════════════════════════════════════════


class TestRuntimeDependencyBoundary:
    """package.json engines.node vs dependencies."""

    def test_runtime_not_dependency(self) -> None:
        """Runtime signals answer 'what runtime/toolchain is selected?'."""
        assert SignalFamily.RUNTIME != SignalFamily.DEPENDENCY

    def test_engines_field_is_runtime_not_dependency(self) -> None:
        """engines.node is a runtime selection concern, not a dependency condition."""
        from pharabius.core.signals.adapters import runtime_missing_pin_to_signal_from_evidence

        class FakeEvidence:
            evidence_id = "EVD-001"
            raw_observation = "engines.node=18"
            location = type("L", (), {"file": "package.json"})()
            metadata = {"runtime_name": "node", "grade": "pinned", "source": "engines"}

        sig = runtime_missing_pin_to_signal_from_evidence([FakeEvidence()])
        assert sig.family == SignalFamily.RUNTIME
        assert sig.family != SignalFamily.DEPENDENCY

    def test_lockfile_conflict_is_dependency_not_runtime(self) -> None:
        """Lockfile conflicts are dependency conditions, not runtime."""
        from pharabius.core.signals.dependency_adapters import (
            dependency_lockfile_conflict_to_signal,
        )

        class FakeItem:
            evidence_id = "EVD-001"
            raw_observation = "lockfile conflict"
            location = type("L", (), {"file": "package-lock.json"})()
            metadata = {"package_manager": "npm"}

        sig = dependency_lockfile_conflict_to_signal([FakeItem()])
        assert sig.family == SignalFamily.DEPENDENCY
        assert sig.family != SignalFamily.RUNTIME


class TestConfigurationSecurityBoundary:
    """.env with token-like keys."""

    def test_env_without_example_is_configuration_not_security(self) -> None:
        from pharabius.core.signals.configuration_adapters import (
            configuration_env_without_example_to_signal,
        )

        class FakeItem:
            evidence_id = "EVD-001"
            location = type("L", (), {"file": ".env"})()

        sig = configuration_env_without_example_to_signal([FakeItem()])
        assert sig.family == SignalFamily.CONFIGURATION
        assert sig.family != SignalFamily.SECURITY
        assert sig.category == "TD-CONFIG"
        assert sig.category != "TD-SEC"


class TestBuildObservabilityBoundary:
    """CI workflow with monitoring step."""

    def test_ci_workflow_is_build_not_observability(self) -> None:
        """CI workflows are build evidence, not deployment for observability."""
        from pharabius.core.signals.adapters import build_missing_ci_to_signal

        sig = build_missing_ci_to_signal(evidence_ids=["EVD-001"])
        assert sig.family == SignalFamily.BUILD
        assert sig.family != SignalFamily.OBSERVABILITY


class TestDeploymentObservabilityBoundary:
    """Deployment without observability."""

    def test_deployment_without_obs_is_observability_not_build(self) -> None:
        from pharabius.core.signals.observability_adapters import observability_missing_to_signal

        class FakeItem:
            evidence_id = "EVD-001"
            location = type("L", (), {"file": "Dockerfile"})()

        sig = observability_missing_to_signal([FakeItem()])
        assert sig.family == SignalFamily.OBSERVABILITY
        assert sig.family != SignalFamily.BUILD


class TestTestSecurityBoundary:
    """Risk-sensitive code without tests."""

    def test_risk_sensitive_without_tests_is_test_not_security(self) -> None:
        from pharabius.core.signals.adapters import scan_test_risk_sensitive_without_tests_to_signal

        sig = scan_test_risk_sensitive_without_tests_to_signal(
            evidence_ids=["EVD-001"],
        )
        assert sig.family == SignalFamily.TEST
        assert sig.family != SignalFamily.SECURITY


class TestSecurityComplianceBoundary:
    """Compliance keywords."""

    def test_compliance_keywords_are_security(self) -> None:
        from pharabius.core.signals.security_adapters import security_compliance_exposure_to_signal

        class FakeItem:
            evidence_id = "EVD-001"
            raw_observation = "hipaa"
            location = type("L", (), {"file": "src/handler.py"})()
            metadata = {"keyword": "hipaa"}

        sig = security_compliance_exposure_to_signal([FakeItem()])
        assert sig.family == SignalFamily.SECURITY
        assert sig.category == "TD-COMP"


class TestArchitectureBoundary:
    """Architecture graph cycles."""

    def test_cycles_are_architecture_only(self) -> None:
        from pharabius.core.signals.architecture_adapters import architecture_cycle_to_signal

        class FakeSpec:
            kind = "cycle"
            category = "TD-ARCH"
            title = "Cycle"
            description = "Circular dep"
            evidence_ids = ["EVD-001"]
            locations = []
            analysis_unit_ids = []
            severity = "Medium"
            confidence = "High"
            technical_impact = ""
            suggested_owner_area = ""

        sig = architecture_cycle_to_signal(FakeSpec())
        assert sig.family == SignalFamily.ARCHITECTURE
        assert sig.family != SignalFamily.RUNTIME
        assert sig.family != SignalFamily.DEPENDENCY

    def test_boundary_violations_are_architecture_only(self) -> None:
        from pharabius.core.signals.architecture_adapters import (
            architecture_boundary_violation_to_signal,
        )

        class FakeSpec:
            kind = "boundary_violation"
            category = "TD-ARCH"
            title = "Violation"
            description = "Layer violation"
            evidence_ids = ["EVD-001"]
            locations = []
            analysis_unit_ids = []
            severity = "Medium"
            confidence = "High"
            technical_impact = ""
            suggested_owner_area = ""

        sig = architecture_boundary_violation_to_signal(FakeSpec())
        assert sig.family == SignalFamily.ARCHITECTURE


class TestProcessDocumentationBoundary:
    """CODEOWNERS / CONTRIBUTING."""

    def test_missing_process_artifacts_is_process_not_documentation(self) -> None:
        from pharabius.core.signals.adapters import process_missing_artifacts_to_signal

        sig = process_missing_artifacts_to_signal(
            missing_artifacts=["CODEOWNERS", "CONTRIBUTING.md"],
            evidence_ids=["EVD-001"],
        )
        assert sig.family == SignalFamily.PROCESS
        assert sig.family != SignalFamily.DOCUMENTATION


class TestDockerfileRuntimeBuildBoundary:
    """Dockerfile runtime tags."""

    def test_dockerfile_runtime_is_runtime_not_build(self) -> None:
        from pharabius.core.signals.adapters import runtime_conflict_to_signal_from_evidence

        class FakeEvidence:
            evidence_id = "EVD-001"
            raw_observation = "FROM python:3.11"
            location = type("L", (), {"file": "Dockerfile"})()
            metadata = {"runtime_name": "python", "grade": "pinned", "source": "dockerfile"}

        sig = runtime_conflict_to_signal_from_evidence(FakeEvidence())
        assert sig.family == SignalFamily.RUNTIME
        assert sig.family != SignalFamily.BUILD
