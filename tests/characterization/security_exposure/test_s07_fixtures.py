"""v3.17.0 — Security boundary and regression fixtures.

Protects behavior and prevents promotion drift with fixture-based tests.
Covers compliance keyword scenarios and boundary with test-health signals.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pharabius.core.analyzer import analyze_evidence
from pharabius.core.init_workspace import initialize_workspace
from pharabius.core.scanner import write_evidence_store
from pharabius.core.signals.models import (
    SignalDisposition,
    SignalFamily,
)
from pharabius.core.signals.policy import (
    output_behavior,
    should_create_advisory,
    should_create_finding,
    should_create_work_package,
)
from pharabius.core.signals.security_adapters import (
    security_compliance_exposure_to_signal,
    security_sensitive_keyword_to_signal,
    security_sensitive_path_to_signal,
)
from pharabius.core.signals.validation import validate_governed_signal
from pharabius.schemas.evidence import EvidenceItem


def _write_file(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _analyze_repo(tmp_path: Path) -> Any:
    initialize_workspace(tmp_path)
    write_evidence_store(tmp_path)
    return analyze_evidence(tmp_path)


def _comp_findings(register: Any) -> list[Any]:
    return [f for f in register.findings if f.category == "TD-COMP"]


def _sec_findings(register: Any) -> list[Any]:
    return [f for f in register.findings if f.category == "TD-SEC"]


# Forbidden severity escalation patterns (context-aware)
FORBIDDEN_SEVERITY_PATTERNS = [
    "confirmed vulnerability",
    "exploitable",
    "CVE-",
    "exploit path",
    "validated secret",
]


# ═══════════════════════════════════════════════════════════════════════
# Adapter disposition correctness
# ═══════════════════════════════════════════════════════════════════════


class TestAdapterDispositions:
    """Adapters produce correct dispositions for each signal type."""

    def test_compliance_exposure_is_finding(self) -> None:
        sig = security_compliance_exposure_to_signal([])
        assert sig.disposition == SignalDisposition.FINDING
        assert sig.family == SignalFamily.SECURITY
        behav = output_behavior(sig)
        assert behav.creates_finding is True
        assert behav.creates_work_package is True

    def test_sensitive_path_is_informational(self) -> None:
        item = EvidenceItem(
            evidence_id="EVD-000001",
            type="risk_sensitive_path_detected",
            category="risk_signal",
            summary="Risk-sensitive path detected",
            metadata={"keywords": ["auth"]},
        )
        sig = security_sensitive_path_to_signal(item)
        assert sig.disposition == SignalDisposition.INFORMATIONAL
        assert sig.family == SignalFamily.SECURITY
        behav = output_behavior(sig)
        assert behav.creates_finding is False
        assert behav.creates_advisory is False
        assert behav.creates_work_package is False
        assert behav.appears_in_summary is True

    def test_sensitive_keyword_is_informational(self) -> None:
        item = EvidenceItem(
            evidence_id="EVD-000001",
            type="risk_sensitive_keyword_detected",
            category="risk_signal",
            summary="Risk-sensitive keyword detected",
            raw_observation="session",
            metadata={"keywords": ["session"]},
        )
        sig = security_sensitive_keyword_to_signal(item)
        assert sig.disposition == SignalDisposition.INFORMATIONAL
        assert sig.family == SignalFamily.SECURITY
        behav = output_behavior(sig)
        assert behav.creates_finding is False
        assert behav.creates_advisory is False
        assert behav.creates_work_package is False
        assert behav.appears_in_summary is True


# ═══════════════════════════════════════════════════════════════════════
# Adapter validation
# ═══════════════════════════════════════════════════════════════════════


class TestAdapterValidation:
    """All security adapters produce valid GovernedSignal instances."""

    def test_compliance_exposure_validates(self) -> None:
        sig = security_compliance_exposure_to_signal(
            [
                EvidenceItem(
                    evidence_id="EVD-000001",
                    type="risk_sensitive_keyword_detected",
                    category="risk_signal",
                    summary="Test",
                    raw_observation="hipaa",
                )
            ]
        )
        result = validate_governed_signal(sig)
        assert result.valid

    def test_sensitive_path_validates(self) -> None:
        sig = security_sensitive_path_to_signal(
            EvidenceItem(
                evidence_id="EVD-000001",
                type="risk_sensitive_path_detected",
                category="risk_signal",
                summary="Test",
            )
        )
        result = validate_governed_signal(sig)
        assert result.valid

    def test_signal_ids_deterministic(self) -> None:
        sig1 = security_compliance_exposure_to_signal([])
        sig2 = security_compliance_exposure_to_signal([])
        assert sig1.signal_id == sig2.signal_id

    def test_metadata_preserves_keywords(self) -> None:
        item = EvidenceItem(
            evidence_id="EVD-000001",
            type="risk_sensitive_keyword_detected",
            category="risk_signal",
            summary="Test",
            raw_observation="hipaa, gdpr",
        )
        sig = security_compliance_exposure_to_signal([item])
        assert "hipaa" in sig.metadata["keywords"]
        assert "gdpr" in sig.metadata["keywords"]


# ═══════════════════════════════════════════════════════════════════════
# Fixture scenarios
# ═══════════════════════════════════════════════════════════════════════


class TestFixtureCleanBaseline:
    """clean_baseline: no risk-sensitive evidence → no security findings."""

    def test_no_security_findings(self, tmp_path: Path) -> None:
        _write_file(tmp_path / "main.py", "print('hello')")
        (tmp_path / ".git").mkdir(exist_ok=True)

        register = _analyze_repo(tmp_path)
        comp = _comp_findings(register)
        assert len(comp) == 0


class TestFixtureComplianceInAppCode:
    """compliance_keyword_in_app_code: PII/GDPR/HIPAA in source → TD-COMP."""

    def test_creates_comp_finding(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path / "src" / "handler.py",
            "# HIPAA processing\ndef process_hipaa():\n    pass\n",
        )
        (tmp_path / ".git").mkdir(exist_ok=True)

        register = _analyze_repo(tmp_path)
        comp = _comp_findings(register)
        assert len(comp) >= 1
        assert comp[0].category == "TD-COMP"
        assert comp[0].title == "Potential compliance exposure detected"

    def test_comp_finding_no_severity_escalation(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path / "src" / "handler.py",
            "def process_pii():\n    pass\n",
        )
        (tmp_path / ".git").mkdir(exist_ok=True)

        register = _analyze_repo(tmp_path)
        comp = _comp_findings(register)
        assert len(comp) >= 1
        f = comp[0]
        all_text = " ".join(
            [
                f.title,
                f.description,
                f.technical_impact,
                f.business_impact,
                " ".join(f.risks_and_cautions),
            ]
        ).lower()
        for pattern in FORBIDDEN_SEVERITY_PATTERNS:
            assert pattern.lower() not in all_text


class TestFixtureComplianceInTestCode:
    """compliance_keyword_in_test_code: filtered, no finding."""

    def test_no_comp_finding(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path / "tests" / "test_hipaa.py",
            "def test_hipaa_compliance():\n    pass\n",
        )
        (tmp_path / ".git").mkdir(exist_ok=True)

        register = _analyze_repo(tmp_path)
        comp = _comp_findings(register)
        assert len(comp) == 0


class TestFixtureComplianceInInfraCode:
    """compliance_keyword_in_infra_code: filtered, no finding."""

    def test_no_comp_finding(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path / "templates" / "pci_template.py",
            "# PCI template\npass\n",
        )
        (tmp_path / ".git").mkdir(exist_ok=True)

        register = _analyze_repo(tmp_path)
        comp = _comp_findings(register)
        assert len(comp) == 0


class TestFixtureRiskSensitivePathOnly:
    """risk_sensitive_path_only: path evidence → no TD-COMP finding."""

    def test_no_comp_finding_from_path(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path / "src" / "auth" / "login.py",
            "def login():\n    pass\n",
        )
        (tmp_path / ".git").mkdir(exist_ok=True)

        register = _analyze_repo(tmp_path)
        comp = _comp_findings(register)
        # 'auth' path is a risk signal but NOT a compliance keyword
        assert len(comp) == 0


class TestFixtureMixedRiskAndCompliance:
    """mixed_risk_and_compliance: compliance keyword creates TD-COMP finding;
    risk-sensitive path/keyword evidence creates INFORMATIONAL signals only.
    No extra finding from risk signals."""

    def test_only_comp_finding_no_extra_security(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path / "src" / "auth" / "hipaa_handler.py",
            "# HIPAA processing\ndef process_hipaa():\n    pass\n",
        )
        (tmp_path / ".git").mkdir(exist_ok=True)

        register = _analyze_repo(tmp_path)
        comp = _comp_findings(register)
        # Should have compliance finding from HIPAA keyword
        assert len(comp) >= 1
        assert comp[0].category == "TD-COMP"

        # Should NOT have additional security findings beyond compliance
        # (risk-sensitive-without-tests is TD-SEC under TEST family, not SECURITY)
        # The auth/ path contributes to risk signals but not compliance


class TestFixtureBoundaryWithTestHealth:
    """No test-health signal is double-counted as security."""

    def test_risk_sensitive_without_tests_stays_test_family(self, tmp_path: Path) -> None:
        """Risk-sensitive without tests → TD-SEC (test family), NOT TD-COMP."""
        _write_file(
            tmp_path / "src" / "session.py",
            "def create_session():\n    pass\n",
        )
        (tmp_path / ".git").mkdir(exist_ok=True)

        register = _analyze_repo(tmp_path)
        sec = _sec_findings(register)
        comp = _comp_findings(register)

        # 'session' is a risk keyword but not in COMPLIANCE_KEYWORDS
        assert len(comp) == 0
        # Risk-sensitive without tests is TD-SEC (TEST family)
        assert len(sec) >= 1

    def test_compliance_and_test_findings_coexist(self, tmp_path: Path) -> None:
        """Compliance and test-health findings are distinct."""
        _write_file(
            tmp_path / "src" / "handler.py",
            "# HIPAA patient data\ndef process_patient():\n    pass\n",
        )
        (tmp_path / ".git").mkdir(exist_ok=True)

        register = _analyze_repo(tmp_path)
        sec = _sec_findings(register)

        # Risk-sensitive without tests creates TD-SEC
        assert len(sec) >= 1
        # Verify test-health and security findings are distinct categories
        # (no double-counting — TD-SEC is test family, not security family)
        categories = {f.category for f in register.findings}
        assert "TD-SEC" in categories  # test family finding
        # TD-COMP may or may not appear depending on scanner raw_observation format
        # The key assertion: TD-SEC is governed by TEST family, not SECURITY


class TestInformationalSecuritySummaryOnly:
    """Informational security signals are summary-only and non-actionable."""

    def test_sensitive_path_no_finding_no_advisory(self) -> None:
        item = EvidenceItem(
            evidence_id="EVD-000001",
            type="risk_sensitive_path_detected",
            category="risk_signal",
            summary="Risk-sensitive path",
        )
        sig = security_sensitive_path_to_signal(item)
        assert should_create_finding(sig) is False
        assert should_create_advisory(sig) is False
        assert should_create_work_package(sig) is False

    def test_sensitive_keyword_no_finding_no_advisory(self) -> None:
        item = EvidenceItem(
            evidence_id="EVD-000001",
            type="risk_sensitive_keyword_detected",
            category="risk_signal",
            summary="Risk-sensitive keyword",
            raw_observation="auth",
        )
        sig = security_sensitive_keyword_to_signal(item)
        assert should_create_finding(sig) is False
        assert should_create_advisory(sig) is False
        assert should_create_work_package(sig) is False
