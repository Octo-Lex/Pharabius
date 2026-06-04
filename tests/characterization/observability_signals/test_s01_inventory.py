"""S01 — Observability signal inventory and characterization tests.

Locks down the CURRENT behavior of TD-OBS analysis before migration
to governed signals.

Boundary: _analyze_missing_observability() is the ONLY TD-OBS producer.
Trigger: deployment/infra evidence exists, CI-only filtered out,
         AND no risk_sensitive_keyword_detected items matching the
         observability keyword set {logging, monitoring, tracing, alert, metrics}.
"""

from __future__ import annotations

import pytest

from pharabius.core.analyzer import FindingBuilder, _analyze_missing_observability
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


def _make_store(items: list[EvidenceItem]) -> EvidenceStore:
    return EvidenceStore(evidence=items)


def _analyze_obs(items: list[EvidenceItem]) -> list:
    """Run _analyze_missing_observability and return builder findings."""
    store = _make_store(items)
    builder = FindingBuilder()
    _analyze_missing_observability(store, builder)
    return builder.findings


# ═══════════════════════════════════════════════════════════════════════
# Trigger conditions
# ═══════════════════════════════════════════════════════════════════════


class TestTriggerConditions:
    """Exact trigger/skip conditions for TD-OBS.

    TD-OBS fires when deployment/infra evidence exists and there are no
    risk_sensitive_keyword_detected evidence items matching the observability
    keyword set. v3.20.0 does NOT add new keyword scanning.
    """

    def test_deployment_without_observability_produces_finding(self) -> None:
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

    def test_infra_without_observability_produces_finding(self) -> None:
        findings = _analyze_obs(
            [
                _make_item(
                    eid="EVD-001", etype="infrastructure_file_detected", file="terraform/main.tf"
                ),
            ]
        )
        assert len(findings) == 1
        assert findings[0].category == "TD-OBS"

    def test_deployment_with_logging_keyword_no_finding(self) -> None:
        findings = _analyze_obs(
            [
                _make_item(eid="EVD-001", file="Dockerfile"),
                _make_keyword_item("EVD-002", "logging"),
            ]
        )
        assert len(findings) == 0

    def test_deployment_with_monitoring_keyword_no_finding(self) -> None:
        findings = _analyze_obs(
            [
                _make_item(eid="EVD-001", file="Dockerfile"),
                _make_keyword_item("EVD-002", "monitoring"),
            ]
        )
        assert len(findings) == 0

    def test_deployment_with_tracing_keyword_no_finding(self) -> None:
        findings = _analyze_obs(
            [
                _make_item(eid="EVD-001", file="Dockerfile"),
                _make_keyword_item("EVD-002", "tracing"),
            ]
        )
        assert len(findings) == 0

    def test_deployment_with_alert_keyword_no_finding(self) -> None:
        findings = _analyze_obs(
            [
                _make_item(eid="EVD-001", file="Dockerfile"),
                _make_keyword_item("EVD-002", "alert"),
            ]
        )
        assert len(findings) == 0

    def test_deployment_with_metrics_keyword_no_finding(self) -> None:
        findings = _analyze_obs(
            [
                _make_item(eid="EVD-001", file="Dockerfile"),
                _make_keyword_item("EVD-002", "metrics"),
            ]
        )
        assert len(findings) == 0

    def test_no_deployment_no_finding(self) -> None:
        findings = _analyze_obs(
            [
                _make_item(eid="EVD-001", etype="file_detected", file="main.py"),
            ]
        )
        assert len(findings) == 0

    def test_ci_only_deployment_no_finding(self) -> None:
        """CI-only deployment evidence is excluded from TD-OBS."""
        findings = _analyze_obs(
            [
                _make_item(eid="EVD-001", file=".github/workflows/ci.yml"),
            ]
        )
        assert len(findings) == 0

    def test_gitlab_ci_only_deployment_no_finding(self) -> None:
        findings = _analyze_obs(
            [
                _make_item(eid="EVD-001", file=".gitlab-ci.yml"),
            ]
        )
        assert len(findings) == 0


# ═══════════════════════════════════════════════════════════════════════
# Evidence cap at 5
# ═══════════════════════════════════════════════════════════════════════


class TestEvidenceCap:
    """TD-OBS evidence_ids capped at 5."""

    def test_evidence_capped_at_5(self) -> None:
        items = [_make_item(eid=f"EVD-{i:03d}", file=f"deploy{i}.yml") for i in range(8)]
        findings = _analyze_obs(items)
        assert len(findings) == 1
        assert len(findings[0].evidence_ids) == 5
        # Preserves ordering — first 5 items
        assert findings[0].evidence_ids == ["EVD-000", "EVD-001", "EVD-002", "EVD-003", "EVD-004"]


# ═══════════════════════════════════════════════════════════════════════
# Field lock-down
# ═══════════════════════════════════════════════════════════════════════


class TestFieldLockdown:
    """Exact TD-OBS finding field values."""

    @pytest.fixture()
    def obs_finding(self) -> object:
        findings = _analyze_obs(
            [
                _make_item(eid="EVD-001", file="Dockerfile"),
                _make_item(
                    eid="EVD-002", etype="deployment_file_detected", file="docker-compose.yml"
                ),
            ]
        )
        assert len(findings) == 1
        return findings[0]

    def test_category(self, obs_finding: object) -> None:
        assert obs_finding.category == "TD-OBS"

    def test_title(self, obs_finding: object) -> None:
        assert obs_finding.title == "Deployment without observability evidence"

    def test_description(self, obs_finding: object) -> None:
        assert (
            "no logging, monitoring, tracing, or alerting keywords found" in obs_finding.description
        )

    def test_confidence_low(self, obs_finding: object) -> None:
        assert obs_finding.confidence == "Low"

    def test_remediation_effort(self, obs_finding: object) -> None:
        assert obs_finding.remediation_effort == "Medium"

    def test_suggested_owner_area(self, obs_finding: object) -> None:
        assert obs_finding.suggested_owner_area == "Platform / SRE"

    def test_risks_and_cautions(self, obs_finding: object) -> None:
        assert (
            "Observability may exist outside repository files" in obs_finding.risks_and_cautions[0]
        )

    def test_risk_breakdown(self, obs_finding: object) -> None:
        rb = obs_finding.risk_breakdown
        assert rb["technical_severity"] == 3
        assert rb["operational_exposure"] == 5
        assert rb["blast_radius"] == 3
        assert rb["business_critical_proxy"] == 3
        assert rb["remediation_simplicity"] == -2

    def test_evidence_ids(self, obs_finding: object) -> None:
        assert "EVD-001" in obs_finding.evidence_ids
        assert "EVD-002" in obs_finding.evidence_ids


# ═══════════════════════════════════════════════════════════════════════
# Language audit
# ═══════════════════════════════════════════════════════════════════════


class TestLanguageAudit:
    """TD-OBS output must not escalate to operational-readiness claims.

    Forbidden: 'production readiness failure', 'SLO/SLA breach',
    'monitoring noncompliance', 'observability maturity score'.
    """

    @pytest.fixture()
    def obs_finding(self) -> object:
        findings = _analyze_obs(
            [
                _make_item(eid="EVD-001", file="Dockerfile"),
            ]
        )
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
        # Should use 'inferred' language
        assert "inferred" in all_text.lower()
