"""Security signal adapters.

Translate security-exposure evidence into platform-level GovernedSignal
instances. Security signals answer: what security/compliance exposure
indicators exist in this repository?

v3.17.0: Adoption release — adapters match existing behavior exactly.
No promotion upgrades, no new dispositions.

Security exposure signals are repository-local indicators.
They are NOT confirmed vulnerabilities, CVE lookups, exploitability claims,
or SAST/DAST results.
"""

from __future__ import annotations

from pharabius.core.signals.models import (
    GovernedSignal,
    SignalDisposition,
    SignalFamily,
    make_signal_id,
)

# ── Finding adapters (match existing behavior) ───────────────────────


def security_compliance_exposure_to_signal(
    evidence_items: list[object],
) -> GovernedSignal:
    """Adapt compliance keyword evidence into a GovernedSignal (FINDING).

    Compliance exposure findings represent potential exposure based on
    keyword evidence, not confirmed compliance gaps or vulnerabilities.
    Disposition matches existing _analyze_compliance_keywords behavior exactly.
    """
    ev_ids = [getattr(e, "evidence_id", "unknown") for e in evidence_items]

    # Extract keyword and location context
    keywords: list[str] = []
    locations: list[str] = []
    for item in evidence_items:
        raw = getattr(item, "raw_observation", "")
        if raw:
            for kw in raw.split(", "):
                if kw.strip() and kw.strip() not in keywords:
                    keywords.append(kw.strip())
        loc = getattr(getattr(item, "location", None), "file", "")
        if loc:
            locations.append(loc)

    signal_id = make_signal_id("security", "compliance_exposure", ev_ids)

    return GovernedSignal(
        signal_id=signal_id,
        family=SignalFamily.SECURITY,
        kind="compliance_exposure",
        disposition=SignalDisposition.FINDING,
        category="TD-COMP",
        severity="Medium",
        confidence="Low",
        evidence_ids=ev_ids,
        source_signal_ids=[],
        title="Potential compliance exposure detected",
        summary=(
            f"Compliance-related keywords detected in {len(evidence_items)} location(s). "
            "Areas handling PII, healthcare, financial, or regulatory data may require "
            "additional controls, audit logging, or policy documentation."
        ),
        explanation=(
            "Compliance-sensitive code areas may lack explicit data handling policies, "
            "audit trails, or retention controls. "
            "This is a potential exposure, not a confirmed violation."
        ),
        metadata={
            "keywords": keywords[:50],
            "locations": locations,
            "item_count": len(evidence_items),
        },
    )


# ── Informational adapters (summary-only, non-actionable) ────────────


def security_sensitive_path_to_signal(
    evidence_item: object,
) -> GovernedSignal:
    """Adapt a risk-sensitive path detection into a GovernedSignal (INFORMATIONAL).

    Risk-sensitive path evidence provides coverage context — informational only.
    Appears in signal summaries but does not create findings, advisories,
    or work packages.
    """
    ev_id = getattr(evidence_item, "evidence_id", "unknown")
    file_path = getattr(getattr(evidence_item, "location", None), "file", "")
    meta = getattr(evidence_item, "metadata", {}) or {}
    keywords = meta.get("keywords", []) if isinstance(meta, dict) else []

    signal_id = make_signal_id("security", "sensitive_path", [ev_id])

    return GovernedSignal(
        signal_id=signal_id,
        family=SignalFamily.SECURITY,
        kind="sensitive_path",
        disposition=SignalDisposition.INFORMATIONAL,
        category="risk_signal",
        severity="Low",
        confidence="Medium",
        evidence_ids=[ev_id],
        source_signal_ids=[],
        title=f"Risk-sensitive path detected: {file_path or 'unknown'}",
        summary=f"Path-based risk signal found at {file_path or 'unknown'}.",
        explanation=(
            "Risk-sensitive path detection provides security coverage context. "
            "It is not a confirmed vulnerability."
        ),
        metadata={"source_file": file_path, "keywords": keywords},
    )


def security_sensitive_keyword_to_signal(
    evidence_item: object,
) -> GovernedSignal:
    """Adapt a risk-sensitive keyword detection into a GovernedSignal (INFORMATIONAL).

    Risk-sensitive keyword evidence provides coverage context — informational only.
    Appears in signal summaries but does not create findings, advisories,
    or work packages.
    """
    ev_id = getattr(evidence_item, "evidence_id", "unknown")
    file_path = getattr(getattr(evidence_item, "location", None), "file", "")
    raw = getattr(evidence_item, "raw_observation", "")
    meta = getattr(evidence_item, "metadata", {}) or {}
    keywords = meta.get("keywords", []) if isinstance(meta, dict) else []

    signal_id = make_signal_id("security", "sensitive_keyword", [ev_id])

    return GovernedSignal(
        signal_id=signal_id,
        family=SignalFamily.SECURITY,
        kind="sensitive_keyword",
        disposition=SignalDisposition.INFORMATIONAL,
        category="risk_signal",
        severity="Low",
        confidence="Medium",
        evidence_ids=[ev_id],
        source_signal_ids=[],
        title=f"Risk-sensitive keyword detected in {file_path or 'unknown'}",
        summary=f"Keyword-based risk signal found: {raw or 'unknown'}.",
        explanation=(
            "Risk-sensitive keyword detection provides security coverage context. "
            "It is not proof of a vulnerability."
        ),
        metadata={"source_file": file_path, "keywords": keywords, "raw_observation": raw},
    )
