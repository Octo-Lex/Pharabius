"""v3.20.0 — Observability boundary and regression fixtures.

Protects behavior and prevents promotion drift with fixture-based tests.
Covers deployment-without-observability, CI-only filtering, keyword
suppression, and family boundaries.
"""

from __future__ import annotations

import pytest

from pharabius.core.analyzer import FindingBuilder, _analyze_missing_observability
from pharabius.core.signals.models import SignalDisposition, SignalFamily
from pharabius.core.signals.observability_adapters import (
    observability_missing_to_signal,
)
from pharabius.core.signals.policy import output_behavior
from pharabius.core.signals.validation import validate_governed_signal
from pharabius.schemas.evidence import EvidenceItem, EvidenceLocation, EvidenceStore


def _make_item(
    eid: str = "EVD-001",
    etype: str = "deployment_file_detected",
    file: str = "Dockerfile",
    obs: str = "FROM python",
) -> EvidenceItem:
    return EvidenceItem(
        evidence_id=eid,
        type=etype,
        category="deployment",
        summary=obs,
        location=EvidenceLocation(file=file),
        raw_observation=obs,
        metadata={},
    )


def _make_keyword_item(eid: str, keyword: str) -> EvidenceItem:
    return EvidenceItem(
        evidence_id=eid,
        type="risk_sensitive_keyword_detected",
        category="risk_signal",
        summary=f"keyword: {keyword}",
        location=EvidenceLocation(file="src/main.py"),
        raw_observation=keyword,
        metadata={},
    )


def _analyze_obs(items: list[EvidenceItem]) -> list:
    store = EvidenceStore(evidence=items)
    builder = FindingBuilder()
    _analyze_missing_observability(store, builder)
    return builder.findings


# ═══════════════════════════════════════════════════════════════════════
# Adapter disposition correctness
# ═══════════════════════════════════════════════════════════════════════


class TestAdapterDispositions:
    """Observability adapter produces correct disposition."""

    def test_missing_observability_is_finding(self) -> None:
        items = [_make_item(file="Dockerfile")]
        sig = observability_missing_to_signal(items)
        assert sig.disposition == SignalDisposition.FINDING
        assert sig.family == SignalFamily.OBSERVABILITY
        behav = output_behavior(sig)
        assert behav.creates_finding is True
        assert behav.creates_work_package is True

    def test_finding_only_in_v320(self) -> None:
        """v3.20.0: Observability emits FINDING only."""
        items = [_make_item(file="Dockerfile")]
        sig = observability_missing_to_signal(items)
        assert sig.disposition == SignalDisposition.FINDING


# ═══════════════════════════════════════════════════════════════════════
# Adapter validation
# ═══════════════════════════════════════════════════════════════════════


class TestAdapterValidation:
    """Observability adapter produces valid GovernedSignal."""

    def test_validates(self) -> None:
        items = [_make_item(file="Dockerfile")]
        sig = observability_missing_to_signal(items)
        result = validate_governed_signal(sig)
        assert result.valid

    def test_signal_id_deterministic(self) -> None:
        items = [_make_item(file="Dockerfile")]
        sig1 = observability_missing_to_signal(items)
        sig2 = observability_missing_to_signal(items)
        assert sig1.signal_id == sig2.signal_id

    def test_metadata_has_spec_kind(self) -> None:
        items = [_make_item(file="Dockerfile")]
        sig = observability_missing_to_signal(items)
        assert sig.metadata["spec_kind"] == "missing_observability"


# ═══════════════════════════════════════════════════════════════════════
# Fixture: deployment_without_observability
# ═══════════════════════════════════════════════════════════════════════


class TestFixtureDeploymentWithoutObservability:
    """Deployment without observability keywords → TD-OBS finding."""

    def test_produces_finding(self) -> None:
        findings = _analyze_obs(
            [
                _make_item(eid="EVD-001", file="Dockerfile"),
                _make_item(
                    eid="EVD-002", etype="deployment_file_detected", file="docker-compose.yml"
                ),
            ]
        )
        assert len(findings) == 1
        assert findings[0].category == "TD-OBS"


# ═══════════════════════════════════════════════════════════════════════
# Fixture: infra_without_observability
# ═══════════════════════════════════════════════════════════════════════


class TestFixtureInfraWithoutObservability:
    """Infrastructure file without observability → TD-OBS finding."""

    def test_produces_finding(self) -> None:
        findings = _analyze_obs(
            [
                _make_item(
                    eid="EVD-001", etype="infrastructure_file_detected", file="terraform/main.tf"
                ),
            ]
        )
        assert len(findings) == 1
        assert findings[0].category == "TD-OBS"


# ═══════════════════════════════════════════════════════════════════════
# Fixture: deployment_with_logging_keyword
# ═══════════════════════════════════════════════════════════════════════


class TestFixtureDeploymentWithLogging:
    """Deployment with logging keyword → no TD-OBS finding."""

    def test_no_finding(self) -> None:
        findings = _analyze_obs(
            [
                _make_item(eid="EVD-001", file="Dockerfile"),
                _make_keyword_item("EVD-002", "logging"),
            ]
        )
        assert len(findings) == 0


# ═══════════════════════════════════════════════════════════════════════
# Fixture: ci_only_deployment
# ═══════════════════════════════════════════════════════════════════════


class TestFixtureCIOnly:
    """CI-only deployment evidence → no TD-OBS, no observability signal."""

    def test_github_actions_no_finding(self) -> None:
        findings = _analyze_obs(
            [
                _make_item(eid="EVD-001", file=".github/workflows/ci.yml"),
            ]
        )
        assert len(findings) == 0

    def test_gitlab_ci_no_finding(self) -> None:
        findings = _analyze_obs(
            [
                _make_item(eid="EVD-001", file=".gitlab-ci.yml"),
            ]
        )
        assert len(findings) == 0


# ═══════════════════════════════════════════════════════════════════════
# Fixture: clean_baseline
# ═══════════════════════════════════════════════════════════════════════


class TestFixtureCleanBaseline:
    """No deployment evidence → no TD-OBS finding."""

    def test_no_finding(self) -> None:
        findings = _analyze_obs(
            [
                _make_item(eid="EVD-001", etype="file_detected", file="main.py"),
            ]
        )
        assert len(findings) == 0


# ═══════════════════════════════════════════════════════════════════════
# Fixture: evidence cap at 5
# ═══════════════════════════════════════════════════════════════════════


class TestFixtureEvidenceCap:
    """TD-OBS evidence_ids remain capped at 5 with existing ordering."""

    def test_capped_at_5(self) -> None:
        items = [_make_item(eid=f"EVD-{i:03d}", file=f"deploy{i}.yml") for i in range(8)]
        findings = _analyze_obs(items)
        assert len(findings) == 1
        assert len(findings[0].evidence_ids) == 5
        assert findings[0].evidence_ids == ["EVD-000", "EVD-001", "EVD-002", "EVD-003", "EVD-004"]


# ═══════════════════════════════════════════════════════════════════════
# Fixture: config_overlap (boundary)
# ═══════════════════════════════════════════════════════════════════════


class TestFixtureConfigOverlap:
    """.env with monitoring variables → config stays config, observability not triggered."""

    def test_env_file_does_not_trigger_obs(self) -> None:
        """An .env file is config evidence, not deployment/infra for TD-OBS."""
        items = [
            EvidenceItem(
                evidence_id="EVD-001",
                type="configuration_file_detected",
                category="configuration",
                summary="env config",
                location=EvidenceLocation(file=".env"),
                raw_observation="MONITORING_URL=http://...",
                metadata={},
            ),
        ]
        findings = _analyze_obs(items)
        assert len(findings) == 0


# ═══════════════════════════════════════════════════════════════════════
# Fixture: security_keyword_overlap (boundary)
# ═══════════════════════════════════════════════════════════════════════


class TestFixtureSecurityKeywordOverlap:
    """Logging code near security keywords → observability suppressed, security unchanged."""

    def test_deployment_with_logging_and_security_keywords(self) -> None:
        findings = _analyze_obs(
            [
                _make_item(eid="EVD-001", file="Dockerfile"),
                _make_keyword_item("EVD-002", "logging"),
                _make_keyword_item("EVD-003", "audit"),
            ]
        )
        assert len(findings) == 0  # logging keyword suppresses TD-OBS


# ═══════════════════════════════════════════════════════════════════════
# Language audit
# ═══════════════════════════════════════════════════════════════════════


class TestLanguageAudit:
    """Observability output must not escalate to operational-readiness claims."""

    @pytest.fixture()
    def obs_finding(self) -> object:
        findings = _analyze_obs([_make_item(file="Dockerfile")])
        assert len(findings) == 1
        return findings[0]

    @pytest.mark.parametrize(
        "forbidden",
        [
            "production readiness failure",
            "SLO/SLA breach",
            "monitoring noncompliance",
            "observability maturity score",
        ],
    )
    def test_no_operational_claims(self, obs_finding: object, forbidden: str) -> None:
        f = obs_finding
        all_text = " ".join(
            [
                f.title,
                f.description,
                f.technical_impact,
                f.business_impact,
                f.recommended_action,
                *f.risks_and_cautions,
                *f.verification_recommendations,
            ]
        )
        assert forbidden.lower() not in all_text.lower(), f"Forbidden term found: {forbidden}"

    def test_inferred_not_confirmed(self, obs_finding: object) -> None:
        """TD-OBS uses 'inferred' language, not 'confirmed'."""
        f = obs_finding
        all_text = " ".join([f.technical_impact, f.business_impact])
        assert "inferred" in all_text.lower()


# ═══════════════════════════════════════════════════════════════════════
# Family boundary
# ═══════════════════════════════════════════════════════════════════════


class TestFamilyBoundary:
    """Observability is distinct from build, configuration, and security."""

    def test_observability_not_build_family(self) -> None:
        items = [_make_item(file="Dockerfile")]
        sig = observability_missing_to_signal(items)
        assert sig.family == SignalFamily.OBSERVABILITY
        assert sig.family != SignalFamily.BUILD

    def test_observability_not_configuration_family(self) -> None:
        items = [_make_item(file="Dockerfile")]
        sig = observability_missing_to_signal(items)
        assert sig.family != SignalFamily.CONFIGURATION

    def test_observability_not_security_family(self) -> None:
        items = [_make_item(file="Dockerfile")]
        sig = observability_missing_to_signal(items)
        assert sig.family != SignalFamily.SECURITY
