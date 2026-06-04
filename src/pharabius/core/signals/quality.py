"""Governance quality metrics.

Read-only metrics that describe governance health without enforcing it.
No quality gates, no pass/fail thresholds, no signal promotion or demotion.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class GovernanceQualityDiagnostic:
    """Threshold-free diagnostic about governance quality.

    Diagnostics are NOT findings, NOT advisories, NOT work packages.
    They do not change signal dispositions or output behavior.
    """

    code: str  # GQM-001 through GQM-005
    severity: str  # "info" or "warning" only — never "critical"
    message: str
    family: str | None = None


@dataclass(frozen=True)
class GovernanceQualityMetrics:
    """Read-only governance quality metrics for a set of governed signals.

    No quality gates. No pass/fail thresholds. No behavior changes.
    """

    total_signals: int
    by_family: dict[str, int] = field(default_factory=dict)
    by_disposition: dict[str, int] = field(default_factory=dict)
    by_severity: dict[str, int] = field(default_factory=dict)
    by_confidence: dict[str, int] = field(default_factory=dict)
    finding_evidence_coverage: float = 1.0
    finding_metadata_coverage: float = 1.0
    advisory_evidence_coverage: float = 1.0
    informational_evidence_coverage: float = 1.0
    diagnostics: list[GovernanceQualityDiagnostic] = field(default_factory=list)


def build_governance_quality_metrics(
    signals: list,
) -> GovernanceQualityMetrics:
    """Compute governance quality metrics from a list of GovernedSignal instances.

    Pure function. Does not mutate signals or change output behavior.
    Coverage uses 1.0 when denominator is 0 (no uncovered signals observed).
    """
    diagnostics: list[GovernanceQualityDiagnostic] = []

    total = len(signals)
    by_family: dict[str, int] = {}
    by_disposition: dict[str, int] = {}
    by_severity: dict[str, int] = {}
    by_confidence: dict[str, int] = {}

    findings_with_evidence = 0
    findings_total = 0
    findings_with_metadata = 0
    advisories_with_basis = 0
    advisories_total = 0
    informational_with_evidence = 0
    informational_total = 0

    valid_severities = {"Critical", "High", "Medium", "Low"}

    for sig in signals:
        fam = sig.family.value
        disp = sig.disposition.value
        sev = sig.severity
        conf = sig.confidence

        by_family[fam] = by_family.get(fam, 0) + 1
        by_disposition[disp] = by_disposition.get(disp, 0) + 1
        by_severity[sev] = by_severity.get(sev, 0) + 1
        by_confidence[conf] = by_confidence.get(conf, 0) + 1

        has_evidence = bool(sig.evidence_ids)
        has_metadata = bool(sig.metadata)

        if disp == "finding":
            findings_total += 1
            if has_evidence:
                findings_with_evidence += 1
            if has_metadata:
                findings_with_metadata += 1
        elif disp == "advisory":
            advisories_total += 1
            # Advisory has "basis" if it has evidence OR non-empty metadata
            if has_evidence or has_metadata:
                advisories_with_basis += 1
        elif disp == "informational":
            informational_total += 1
            if has_evidence:
                informational_with_evidence += 1

        # GQM-005: Unexpected severity/confidence label
        if sev not in valid_severities:
            diagnostics.append(
                GovernanceQualityDiagnostic(
                    code="GQM-005",
                    severity="warning",
                    message=f"Unexpected severity '{sev}' on signal {sig.signal_id}",
                    family=fam,
                )
            )

    # GQM-001: Finding without evidence
    findings_without_evidence = findings_total - findings_with_evidence
    if findings_without_evidence > 0:
        diagnostics.append(
            GovernanceQualityDiagnostic(
                code="GQM-001",
                severity="warning",
                message=f"{findings_without_evidence} finding(s) without evidence",
            )
        )

    # GQM-002: Advisory without evidence and without metadata (no basis)
    advisories_without_basis = advisories_total - advisories_with_basis
    if advisories_without_basis > 0:
        diagnostics.append(
            GovernanceQualityDiagnostic(
                code="GQM-002",
                severity="info",
                message=f"{advisories_without_basis} advisory/advisories without evidence or metadata basis",  # noqa: E501
            )
        )

    # GQM-003: Informational without evidence
    informational_without_evidence = informational_total - informational_with_evidence
    if informational_without_evidence > 0:
        diagnostics.append(
            GovernanceQualityDiagnostic(
                code="GQM-003",
                severity="info",
                message=f"{informational_without_evidence} informational signal(s) without evidence",  # noqa: E501
            )
        )

    # GQM-004: Finding with empty metadata
    findings_without_metadata = findings_total - findings_with_metadata
    if findings_without_metadata > 0:
        diagnostics.append(
            GovernanceQualityDiagnostic(
                code="GQM-004",
                severity="info",
                message=f"{findings_without_metadata} finding(s) with empty metadata",
            )
        )

    # Coverage ratios — 1.0 when denominator is 0
    finding_evidence_coverage = (
        findings_with_evidence / findings_total if findings_total > 0 else 1.0
    )
    finding_metadata_coverage = (
        findings_with_metadata / findings_total if findings_total > 0 else 1.0
    )
    advisory_evidence_coverage = (
        advisories_with_basis / advisories_total if advisories_total > 0 else 1.0
    )
    informational_evidence_coverage = (
        informational_with_evidence / informational_total if informational_total > 0 else 1.0
    )

    return GovernanceQualityMetrics(
        total_signals=total,
        by_family=by_family,
        by_disposition=by_disposition,
        by_severity=by_severity,
        by_confidence=by_confidence,
        finding_evidence_coverage=finding_evidence_coverage,
        finding_metadata_coverage=finding_metadata_coverage,
        advisory_evidence_coverage=advisory_evidence_coverage,
        informational_evidence_coverage=informational_evidence_coverage,
        diagnostics=diagnostics,
    )


def governance_quality_metrics_to_dict(metrics: GovernanceQualityMetrics) -> dict:
    """Serialize governance quality metrics to JSON-compatible dict.

    All fields preserved without data loss.
    """
    return {
        "total_signals": metrics.total_signals,
        "by_family": dict(metrics.by_family),
        "by_disposition": dict(metrics.by_disposition),
        "by_severity": dict(metrics.by_severity),
        "by_confidence": dict(metrics.by_confidence),
        "finding_evidence_coverage": metrics.finding_evidence_coverage,
        "finding_metadata_coverage": metrics.finding_metadata_coverage,
        "advisory_evidence_coverage": metrics.advisory_evidence_coverage,
        "informational_evidence_coverage": metrics.informational_evidence_coverage,
        "diagnostics": [
            {
                "code": d.code,
                "severity": d.severity,
                "message": d.message,
                "family": d.family,
            }
            for d in metrics.diagnostics
        ],
    }
