"""v3.19.0 — Configuration boundary and regression fixtures.

Protects behavior and prevents promotion drift with fixture-based tests.
Covers env-without-example, skip conditions, and family boundary.
"""

from __future__ import annotations

import pytest

from pharabius.core.analyzer import FindingBuilder, _analyze_env_without_example
from pharabius.core.signals.configuration_adapters import (
    configuration_env_without_example_to_signal,
)
from pharabius.core.signals.models import SignalDisposition, SignalFamily
from pharabius.core.signals.policy import output_behavior
from pharabius.core.signals.validation import validate_governed_signal
from pharabius.schemas.evidence import EvidenceItem, EvidenceLocation, EvidenceStore


def _make_item(
    eid: str = "EVD-001",
    file: str = ".env",
    obs: str = "environment config",
) -> EvidenceItem:
    return EvidenceItem(
        evidence_id=eid,
        type="configuration_file_detected",
        category="configuration",
        summary=obs,
        location=EvidenceLocation(file=file),
        raw_observation=obs,
        metadata={},
    )


def _analyze_config(items: list[EvidenceItem]) -> list:
    store = EvidenceStore(evidence=items)
    builder = FindingBuilder()
    _analyze_env_without_example(store, builder)
    return builder.findings


# ═══════════════════════════════════════════════════════════════════════
# Adapter disposition correctness
# ═══════════════════════════════════════════════════════════════════════


class TestAdapterDispositions:
    """Configuration adapter produces correct disposition."""

    def test_env_without_example_is_finding(self) -> None:
        items = [_make_item(file=".env")]
        sig = configuration_env_without_example_to_signal(items)
        assert sig.disposition == SignalDisposition.FINDING
        assert sig.family == SignalFamily.CONFIGURATION
        behav = output_behavior(sig)
        assert behav.creates_finding is True
        assert behav.creates_work_package is True

    def test_finding_only_in_v319(self) -> None:
        """v3.19.0: Configuration emits FINDING only."""
        items = [_make_item(file=".env")]
        sig = configuration_env_without_example_to_signal(items)
        assert sig.disposition == SignalDisposition.FINDING


# ═══════════════════════════════════════════════════════════════════════
# Adapter validation
# ═══════════════════════════════════════════════════════════════════════


class TestAdapterValidation:
    """Configuration adapter produces valid GovernedSignal."""

    def test_validates(self) -> None:
        items = [_make_item(file=".env")]
        sig = configuration_env_without_example_to_signal(items)
        result = validate_governed_signal(sig)
        assert result.valid

    def test_signal_id_deterministic(self) -> None:
        items = [_make_item(file=".env")]
        sig1 = configuration_env_without_example_to_signal(items)
        sig2 = configuration_env_without_example_to_signal(items)
        assert sig1.signal_id == sig2.signal_id

    def test_metadata_has_spec_kind(self) -> None:
        items = [_make_item(file=".env")]
        sig = configuration_env_without_example_to_signal(items)
        assert sig.metadata["spec_kind"] == "env_without_example"


# ═══════════════════════════════════════════════════════════════════════
# Fixture: env_without_example
# ═══════════════════════════════════════════════════════════════════════


class TestFixtureEnvWithoutExample:
    """.env without .env.example → TD-CONFIG finding."""

    def test_produces_finding(self) -> None:
        findings = _analyze_config([_make_item(file=".env")])
        assert len(findings) == 1
        assert findings[0].category == "TD-CONFIG"

    def test_env_local_produces_finding(self) -> None:
        findings = _analyze_config([_make_item(eid="EVD-002", file=".env.local")])
        assert len(findings) == 1
        assert findings[0].category == "TD-CONFIG"


# ═══════════════════════════════════════════════════════════════════════
# Fixture: env_with_example
# ═══════════════════════════════════════════════════════════════════════


class TestFixtureEnvWithExample:
    """.env AND .env.example → no finding."""

    def test_no_finding(self) -> None:
        findings = _analyze_config(
            [
                _make_item(eid="EVD-001", file=".env"),
                _make_item(eid="EVD-002", file=".env.example", obs="example"),
            ]
        )
        assert len(findings) == 0


# ═══════════════════════════════════════════════════════════════════════
# Fixture: example_only (skip condition)
# ═══════════════════════════════════════════════════════════════════════


class TestFixtureExampleOnly:
    """.env.example alone → no finding, no signal."""

    def test_no_finding(self) -> None:
        findings = _analyze_config(
            [
                _make_item(eid="EVD-001", file=".env.example", obs="example"),
            ]
        )
        assert len(findings) == 0


# ═══════════════════════════════════════════════════════════════════════
# Fixture: clean_baseline
# ═══════════════════════════════════════════════════════════════════════


class TestFixtureCleanBaseline:
    """No config files → no TD-CONFIG finding."""

    def test_no_finding(self) -> None:
        findings = _analyze_config([])
        assert len(findings) == 0


# ═══════════════════════════════════════════════════════════════════════
# Fixture: multiple_env_files
# ═══════════════════════════════════════════════════════════════════════


class TestFixtureMultipleEnvFiles:
    """Both .env and .env.local without .env.example → single finding."""

    def test_single_finding(self) -> None:
        findings = _analyze_config(
            [
                _make_item(eid="EVD-001", file=".env"),
                _make_item(eid="EVD-002", file=".env.local"),
            ]
        )
        assert len(findings) == 1
        # Both evidence IDs should be included
        ev_ids = findings[0].evidence_ids
        assert "EVD-001" in ev_ids
        assert "EVD-002" in ev_ids


# ═══════════════════════════════════════════════════════════════════════
# Fixture: security_keyword_in_env_file (boundary)
# ═══════════════════════════════════════════════════════════════════════


class TestFixtureSecurityKeywordBoundary:
    """Env file with token-like keys → config finding only, no new security finding.

    Configuration handles config hygiene. Security does not gain new
    secret-detection behavior from this path.
    """

    def test_config_finding_only(self) -> None:
        items = [
            EvidenceItem(
                evidence_id="EVD-001",
                type="configuration_file_detected",
                category="configuration",
                summary="env config with API_KEY=secret",
                location=EvidenceLocation(file=".env"),
                raw_observation="API_KEY=sk-xxxx",
                metadata={"contains_keywords": True},
            ),
        ]
        findings = _analyze_config(items)
        assert len(findings) == 1
        assert findings[0].category == "TD-CONFIG"
        # No new security finding created by configuration path
        assert findings[0].category != "TD-SEC"


# ═══════════════════════════════════════════════════════════════════════
# Fixture: deployment_config_overlap (boundary)
# ═══════════════════════════════════════════════════════════════════════


class TestFixtureDeploymentOverlap:
    """Deployment config + .env → only TD-CONFIG for env, build paths unchanged."""

    def test_env_triggers_config_only(self) -> None:
        items = [
            _make_item(eid="EVD-001", file=".env"),
            EvidenceItem(
                evidence_id="EVD-002",
                type="configuration_file_detected",
                category="configuration",
                summary="deployment config",
                location=EvidenceLocation(file="deploy.yaml"),
                raw_observation="deployment config",
                metadata={},
            ),
        ]
        findings = _analyze_config(items)
        assert len(findings) == 1
        assert findings[0].category == "TD-CONFIG"


# ═══════════════════════════════════════════════════════════════════════
# Language audit
# ═══════════════════════════════════════════════════════════════════════


class TestLanguageAudit:
    """Configuration output must not escalate to security claims."""

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
        """The word 'credentials' in risks_and_cautions is allowed."""
        cautions = " ".join(config_finding.risks_and_cautions)
        assert "credentials" in cautions.lower()


# ═══════════════════════════════════════════════════════════════════════
# Family boundary
# ═══════════════════════════════════════════════════════════════════════


class TestFamilyBoundary:
    """Configuration is distinct from security, build, and process."""

    def test_configuration_not_security_family(self) -> None:
        items = [_make_item(file=".env")]
        sig = configuration_env_without_example_to_signal(items)
        assert sig.family == SignalFamily.CONFIGURATION
        assert sig.family != SignalFamily.SECURITY

    def test_configuration_not_build_family(self) -> None:
        items = [_make_item(file=".env")]
        sig = configuration_env_without_example_to_signal(items)
        assert sig.family != SignalFamily.BUILD

    def test_configuration_not_process_family(self) -> None:
        items = [_make_item(file=".env")]
        sig = configuration_env_without_example_to_signal(items)
        assert sig.family != SignalFamily.PROCESS
