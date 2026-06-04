"""S01 — Configuration/environment signal inventory and characterization tests.

Locks down the CURRENT behavior of TD-CONFIG analysis before migration
to governed signals.

Boundary: _analyze_env_without_example() is the ONLY TD-CONFIG producer.
Single evidence type: configuration_file_detected.
Single trigger: .env or .env.local present AND .env.example absent.
"""

from __future__ import annotations

import pytest

from pharabius.core.analyzer import FindingBuilder, _analyze_env_without_example
from pharabius.schemas.evidence import EvidenceItem, EvidenceLocation, EvidenceStore


def _make_item(
    eid: str = "EVD-001",
    etype: str = "configuration_file_detected",
    file: str = ".env",
    obs: str = "environment config",
) -> EvidenceItem:
    return EvidenceItem(
        evidence_id=eid,
        type=etype,
        category="configuration",
        summary=obs,
        location=EvidenceLocation(file=file),
        raw_observation=obs,
        metadata={},
    )


def _make_store(items: list[EvidenceItem]) -> EvidenceStore:
    return EvidenceStore(evidence=items)


def _analyze_config(items: list[EvidenceItem]) -> list:
    """Run _analyze_env_without_example and return builder findings."""
    store = _make_store(items)
    builder = FindingBuilder()
    _analyze_env_without_example(store, builder)
    return builder.findings


# ═══════════════════════════════════════════════════════════════════════
# Trigger conditions
# ═══════════════════════════════════════════════════════════════════════


class TestTriggerConditions:
    """Exact trigger/skip conditions for TD-CONFIG."""

    def test_env_without_example_produces_finding(self) -> None:
        findings = _analyze_config([_make_item(file=".env")])
        assert len(findings) == 1
        assert findings[0].category == "TD-CONFIG"

    def test_env_local_without_example_produces_finding(self) -> None:
        findings = _analyze_config([_make_item(eid="EVD-002", file=".env.local")])
        assert len(findings) == 1
        assert findings[0].category == "TD-CONFIG"

    def test_env_with_example_no_finding(self) -> None:
        findings = _analyze_config(
            [
                _make_item(eid="EVD-001", file=".env"),
                _make_item(
                    eid="EVD-002",
                    etype="configuration_file_detected",
                    file=".env.example",
                    obs="example",
                ),
            ]
        )
        assert len(findings) == 0

    def test_no_env_no_finding(self) -> None:
        findings = _analyze_config([])
        assert len(findings) == 0

    def test_example_only_no_finding(self) -> None:
        """v3.19.0: .env.example alone is a skip/no-signal condition."""
        findings = _analyze_config(
            [
                _make_item(eid="EVD-001", file=".env.example", obs="example config"),
            ]
        )
        assert len(findings) == 0

    def test_multiple_env_files_single_finding(self) -> None:
        """Both .env and .env.local without .env.example → one finding."""
        findings = _analyze_config(
            [
                _make_item(eid="EVD-001", file=".env"),
                _make_item(eid="EVD-002", file=".env.local"),
            ]
        )
        assert len(findings) == 1
        assert findings[0].category == "TD-CONFIG"


# ═══════════════════════════════════════════════════════════════════════
# Field lock-down
# ═══════════════════════════════════════════════════════════════════════


class TestFieldLockdown:
    """Exact TD-CONFIG finding field values."""

    @pytest.fixture()
    def config_finding(self) -> object:
        findings = _analyze_config([_make_item(file=".env")])
        assert len(findings) == 1
        return findings[0]

    def test_category(self, config_finding: object) -> None:
        assert config_finding.category == "TD-CONFIG"

    def test_title(self, config_finding: object) -> None:
        assert config_finding.title == "Environment configuration detected without example file"

    def test_description(self, config_finding: object) -> None:
        assert config_finding.description == (
            "An environment configuration file was detected, but no `.env.example` file was found."
        )

    def test_technical_impact(self, config_finding: object) -> None:
        assert config_finding.technical_impact == (
            "Missing environment examples make setup, onboarding, and environment parity harder "
            "to verify."
        )

    def test_business_impact(self, config_finding: object) -> None:
        assert config_finding.business_impact == (
            "Operational setup risk is inferred from environment configuration evidence."
        )

    def test_remediation_effort(self, config_finding: object) -> None:
        assert config_finding.remediation_effort == "Small"

    def test_recommended_action(self, config_finding: object) -> None:
        assert config_finding.recommended_action == (
            "Add a sanitized `.env.example` documenting required variables without secrets."
        )

    def test_verification_recommendations(self, config_finding: object) -> None:
        assert config_finding.verification_recommendations == [
            "Verify `.env.example` contains no real secrets.",
            "Confirm local setup works from documented environment variables.",
        ]

    def test_risks_and_cautions(self, config_finding: object) -> None:
        assert config_finding.risks_and_cautions == [
            "Never commit real credentials or production secrets.",
        ]

    def test_suggested_owner_area(self, config_finding: object) -> None:
        assert config_finding.suggested_owner_area == "Platform / Product Engineering"

    def test_evidence_ids(self, config_finding: object) -> None:
        assert "EVD-001" in config_finding.evidence_ids

    def test_risk_breakdown(self, config_finding: object) -> None:
        rb = config_finding.risk_breakdown
        assert rb["technical_severity"] == 3
        assert rb["security_exposure"] == 3
        assert rb["operational_exposure"] == 3
        assert rb["business_critical_proxy"] == 3
        assert rb["remediation_simplicity"] == -2


# ═══════════════════════════════════════════════════════════════════════
# Language audit
# ═══════════════════════════════════════════════════════════════════════


class TestLanguageAudit:
    """TD-CONFIG output must not escalate to security claims.

    Forbidden: 'confirmed secret', 'credential leak', 'vulnerability',
    'exploitable', 'CVE-'.
    Allowed: 'credentials' in caution text (existing behavior).
    """

    @pytest.fixture()
    def config_finding(self) -> object:
        findings = _analyze_config([_make_item(file=".env")])
        assert len(findings) == 1
        return findings[0]

    @pytest.mark.parametrize(
        "forbidden",
        [
            "confirmed secret",
            "credential leak",
            "vulnerability",
            "exploitable",
            "CVE-",
        ],
    )
    def test_no_escalation_claims(self, config_finding: object, forbidden: str) -> None:
        f = config_finding
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

    def test_existing_credentials_caution_preserved(self, config_finding: object) -> None:
        """The word 'credentials' in risks_and_cautions is allowed — existing caution text."""
        cautions = " ".join(config_finding.risks_and_cautions)
        assert "credentials" in cautions.lower()
