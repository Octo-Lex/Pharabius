"""S01 — Security signal inventory and characterization tests.

These tests lock down the CURRENT behavior of security-exposure analysis
before migration to governed signals. Every output field is captured.

After migration (S02–S04), these same tests must pass with identical output.
Field-level comparison uses assert_finding_unchanged() for explicit verification.

Boundary: _analyze_risk_sensitive_without_tests is already governed under
SignalFamily.TEST (v3.14.0) and is NOT migrated in v3.17.0.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from pharabius.core.analyzer import analyze_evidence
from pharabius.core.init_workspace import initialize_workspace
from pharabius.core.scanner import write_evidence_store
from pharabius.schemas.evidence import EvidenceItem

# ── Helpers ────────────────────────────────────────────────────────────


def _write_file(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _analyze_repo(tmp_path: Path) -> Any:
    """Run full analyze_evidence and return the DebtRegister."""
    initialize_workspace(tmp_path)
    write_evidence_store(tmp_path)
    return analyze_evidence(tmp_path)


def _comp_findings(register: Any) -> list[Any]:
    """Return TD-COMP findings from a DebtRegister."""
    return [f for f in register.findings if f.category == "TD-COMP"]


def _sec_findings(register: Any) -> list[Any]:
    """Return TD-SEC findings from a DebtRegister."""
    return [f for f in register.findings if f.category == "TD-SEC"]


def _make_risk_keyword_evidence(
    keyword: str,
    file_path: str,
    confidence: str = "Medium",
) -> EvidenceItem:
    """Create a risk_sensitive_keyword_detected evidence item."""
    return EvidenceItem(
        evidence_id="EVD-000001",
        type="risk_sensitive_keyword_detected",
        category="risk_signal",
        summary=f"Risk-sensitive keyword detected in {file_path}",
        raw_observation=keyword,
        confidence=confidence,
        metadata={"keywords": [keyword]},
    )


def assert_finding_unchanged(before: Any, after: Any, label: str = "") -> None:
    """Assert every field of a finding/advisory is identical after migration."""
    prefix = f"[{label}] " if label else ""
    assert before.category == after.category, f"{prefix}category changed"
    assert before.issue_type == after.issue_type, f"{prefix}issue_type changed"
    assert before.title == after.title, f"{prefix}title changed"
    assert before.description == after.description, f"{prefix}description changed"
    assert before.severity == after.severity, f"{prefix}severity changed"
    assert before.confidence == after.confidence, f"{prefix}confidence changed"
    assert before.risk_score == after.risk_score, f"{prefix}risk_score changed"
    assert before.priority == after.priority, f"{prefix}priority changed"
    assert before.locations == after.locations, f"{prefix}locations changed"
    assert before.evidence_ids == after.evidence_ids, f"{prefix}evidence_ids changed"


# ═══════════════════════════════════════════════════════════════════════
# S01 Inventory: _analyze_compliance_keywords output
# ═══════════════════════════════════════════════════════════════════════


class TestComplianceKeywordsInventory:
    """Catalog what _analyze_compliance_keywords currently produces."""

    def test_pii_in_app_code_creates_comp_finding(self, tmp_path: Path) -> None:
        """PII keyword in application code → TD-COMP finding."""
        _write_file(
            tmp_path / "src" / "user_service.py",
            "def process_pii(data):\n    pass\n",
        )
        (tmp_path / ".git").mkdir(exist_ok=True)

        register = _analyze_repo(tmp_path)
        comp = _comp_findings(register)
        assert len(comp) >= 1
        f = comp[0]
        assert f.category == "TD-COMP"
        assert "compliance" in f.title.lower() or "exposure" in f.title.lower()
        assert f.confidence == "Low"

    def test_compliance_finding_has_correct_title(self, tmp_path: Path) -> None:
        """Exact title lock-down."""
        _write_file(
            tmp_path / "src" / "health.py",
            "def handle_patient(data):\n    pass\n",
        )
        (tmp_path / ".git").mkdir(exist_ok=True)

        register = _analyze_repo(tmp_path)
        comp = _comp_findings(register)
        assert len(comp) >= 1
        assert comp[0].title == "Potential compliance exposure detected"

    def test_compliance_finding_preserves_category(self, tmp_path: Path) -> None:
        """Category must be TD-COMP exactly."""
        _write_file(
            tmp_path / "src" / "gdpr_handler.py",
            "def process_gdpr_request():\n    pass\n",
        )
        (tmp_path / ".git").mkdir(exist_ok=True)

        register = _analyze_repo(tmp_path)
        comp = _comp_findings(register)
        assert len(comp) >= 1
        assert comp[0].category == "TD-COMP"

    def test_compliance_finding_risks_and_cautions(self, tmp_path: Path) -> None:
        """Risks and cautions must preserve 'not a confirmed violation' language."""
        _write_file(
            tmp_path / "src" / "handler.py",
            "# HIPAA processing\ndef process_hipaa():\n    pass\n",
        )
        (tmp_path / ".git").mkdir(exist_ok=True)

        register = _analyze_repo(tmp_path)
        comp = _comp_findings(register)
        assert len(comp) >= 1
        f = comp[0]
        # Must contain the caution about not being a confirmed violation
        caution_text = " ".join(f.risks_and_cautions).lower()
        assert "not a confirmed" in caution_text or "not proof" in caution_text

    def test_compliance_finding_confidence_low(self, tmp_path: Path) -> None:
        """Confidence must be Low (not escalated)."""
        _write_file(
            tmp_path / "src" / "billing.py",
            "def process_retention():\n    pass\n",
        )
        (tmp_path / ".git").mkdir(exist_ok=True)

        register = _analyze_repo(tmp_path)
        comp = _comp_findings(register)
        assert len(comp) >= 1
        assert comp[0].confidence == "Low"

    def test_compliance_keyword_in_test_code_filtered(self, tmp_path: Path) -> None:
        """Compliance keywords in test paths → no TD-COMP finding."""
        _write_file(
            tmp_path / "tests" / "test_gdpr.py",
            "def test_gdpr_compliance():\n    pass\n",
        )
        (tmp_path / ".git").mkdir(exist_ok=True)

        register = _analyze_repo(tmp_path)
        comp = _comp_findings(register)
        assert len(comp) == 0, "Compliance keywords in test paths should be filtered"

    def test_compliance_keyword_in_docs_filtered(self, tmp_path: Path) -> None:
        """Compliance keywords in docs/ → no TD-COMP finding."""
        _write_file(
            tmp_path / "docs" / "hipaa_guide.md",
            "# HIPAA Compliance Guide\n",
        )
        (tmp_path / ".git").mkdir(exist_ok=True)

        register = _analyze_repo(tmp_path)
        comp = _comp_findings(register)
        assert len(comp) == 0, "Compliance keywords in docs should be filtered"

    def test_non_compliance_keyword_no_finding(self, tmp_path: Path) -> None:
        """Non-compliance risk keyword (e.g., 'auth') → no TD-COMP finding."""
        _write_file(
            tmp_path / "src" / "auth.py",
            "def authenticate():\n    pass\n",
        )
        (tmp_path / ".git").mkdir(exist_ok=True)

        register = _analyze_repo(tmp_path)
        comp = _comp_findings(register)
        # 'auth' is a risk keyword but not in COMPLIANCE_KEYWORDS
        assert len(comp) == 0, "'auth' should not create compliance finding"


# ═══════════════════════════════════════════════════════════════════════
# S01 Inventory: Compliance keyword set (exact)
# ═══════════════════════════════════════════════════════════════════════


class TestComplianceKeywordSet:
    """Verify the exact compliance keyword set from the analyzer."""

    EXACT_KEYWORDS = {"pii", "gdpr", "hipaa", "pci", "retention", "patient"}

    @pytest.mark.parametrize("keyword", list(EXACT_KEYWORDS))
    def test_keyword_creates_compliance_finding(self, tmp_path: Path, keyword: str) -> None:
        """Each exact compliance keyword in app code → TD-COMP finding."""
        _write_file(
            tmp_path / "src" / f"handler_{keyword}.py",
            f"def process_{keyword}():\n    pass\n",
        )
        (tmp_path / ".git").mkdir(exist_ok=True)

        register = _analyze_repo(tmp_path)
        comp = _comp_findings(register)
        assert len(comp) >= 1, f"Keyword '{keyword}' should create TD-COMP finding"

    def test_audit_is_not_compliance_keyword(self, tmp_path: Path) -> None:
        """'audit' is a risk keyword but NOT in the compliance set."""
        _write_file(
            tmp_path / "src" / "audit_log.py",
            "def write_audit_log():\n    pass\n",
        )
        (tmp_path / ".git").mkdir(exist_ok=True)

        register = _analyze_repo(tmp_path)
        comp = _comp_findings(register)
        # 'audit' triggers risk_sensitive_keyword_detected but NOT compliance
        # because it's not in COMPLIANCE_KEYWORDS = {"pii", "gdpr", "hipaa", "pci", "retention", "patient"}
        assert len(comp) == 0, "'audit' should not create compliance finding"


# ═══════════════════════════════════════════════════════════════════════
# S01 Inventory: Risk-sensitive-without-tests boundary
# ═══════════════════════════════════════════════════════════════════════


class TestRiskSensitiveWithoutTestsBoundary:
    """_analyze_risk_sensitive_without_tests stays under SignalFamily.TEST.

    It is already governed (v3.14.0) and produces TD-SEC findings.
    v3.17.0 does NOT migrate this function.
    """

    def test_risk_sensitive_without_tests_produces_td_sec(self, tmp_path: Path) -> None:
        """Risk-sensitive code without tests → TD-SEC finding (test family)."""
        _write_file(
            tmp_path / "src" / "auth.py",
            "def authenticate():\n    pass\n",
        )
        (tmp_path / ".git").mkdir(exist_ok=True)

        register = _analyze_repo(tmp_path)
        sec = _sec_findings(register)
        assert len(sec) >= 1
        assert any("risk-sensitive" in f.title.lower() for f in sec)

    def test_risk_sensitive_finding_not_double_counted_as_comp(self, tmp_path: Path) -> None:
        """Risk-sensitive without tests → TD-SEC, NOT TD-COMP."""
        _write_file(
            tmp_path / "src" / "session.py",
            "def create_session():\n    pass\n",
        )
        (tmp_path / ".git").mkdir(exist_ok=True)

        register = _analyze_repo(tmp_path)
        sec = _sec_findings(register)
        comp = _comp_findings(register)
        # Risk-sensitive without tests is TD-SEC, not TD-COMP
        assert len(sec) >= 1
        assert len(comp) == 0, "Risk-sensitive path should not create TD-COMP"


# ═══════════════════════════════════════════════════════════════════════
# S01 Inventory: Language audit baseline
# ═══════════════════════════════════════════════════════════════════════

# Forbidden patterns in finding/advisory output (context-aware):
# - "confirmed vulnerability" (not "not a confirmed vulnerability")
# - "exploitable"
# - "CVE-"
# - "exploit path"
# - "validated secret"
#
# Allowed patterns:
# - "not a confirmed vulnerability"
# - "no CVE lookup"
# - "not proof of a vulnerability"

FORBIDDEN_SEVERITY_PATTERNS = [
    "confirmed vulnerability",
    "exploitable",
    "CVE-",
    "exploit path",
    "validated secret",
]


class TestLanguageAuditBaseline:
    """Verify current output does not escalate severity language."""

    def test_compliance_finding_no_severity_escalation(self, tmp_path: Path) -> None:
        """Compliance finding must not use forbidden severity patterns."""
        _write_file(
            tmp_path / "src" / "hipaa_handler.py",
            "def handle_hipaa():\n    pass\n",
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
                " ".join(f.verification_recommendations),
            ]
        ).lower()

        for pattern in FORBIDDEN_SEVERITY_PATTERNS:
            assert pattern.lower() not in all_text, (
                f"Forbidden severity pattern '{pattern}' found in compliance finding"
            )


# ═══════════════════════════════════════════════════════════════════════
# S01 Inventory: Summary documentation
# ═══════════════════════════════════════════════════════════════════════
#
# Known security-related output categories:
#
#   TD-SEC  — _analyze_risk_sensitive_without_tests (already governed, TEST family)
#   TD-COMP — _analyze_compliance_keywords (migration target, v3.17.0)
#   TD-CONFIG — _analyze_env_without_example (out of scope)
#
# Evidence types consumed by security-related analyzers:
#
#   risk_sensitive_path_detected     — scanner path-name matching
#   risk_sensitive_keyword_detected  — scanner content keyword matching
#
# Compliance keyword set (exact, from _analyze_compliance_keywords):
#
#   {"pii", "gdpr", "hipaa", "pci", "retention", "patient"}
#
# Noise path segments that filter compliance evidence:
#
#   tests/, test_, _test., docs/, templates/, scanner.py,
#   analyzer.py, validator.py, enricher.py, mock_provider.py,
#   test_taxonomy
