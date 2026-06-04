"""Governance quality metrics.

Read-only descriptive analytics over the governed signal surface.
Does not create findings, advisories, work packages, or alter behavior.

Coverage ratios use 1.0 when no signals of that disposition exist,
meaning "no uncovered signals observed," not "coverage proven."
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pharabius.core.signals.models import GovernedSignal, SignalDisposition


@dataclass(frozen=True)
class GovernanceQualityDiagnostic:
    """A descriptive diagnostic about governance surface quality.

    Diagnostics are NOT findings, advisories, or work packages.
    They do not alter signal disposition, output behavior, or run outcome.
    """

    code: str  # GQM-001 through GQM-005
    severity: str  # "info" or "warning" — reuse SignalValidationSeverity values
    message: str
    family: str | None = None


@dataclass(frozen=True)
class GovernanceQualityMetrics:
    """Read-only governance quality metrics.

    Computed from GovernedSignal instances. Does not mutate signals
    or change output_behavior().
    """

    total_signals: int
    by_family: dict[str, int]
    by_disposition: dict[str, int]
    by_severity: dict[str, int]
    by_confidence: dict[str, int]
    finding_evidence_coverage: float  # 0.0–1.0; 1.0 when no FINDING signals
    finding_metadata_coverage: float  # 0.0–1.0; 1.0 when no FINDING signals
    advisory_evidence_coverage: float  # 0.0–1.0; 1.0 when no ADVISORY signals
    informational_evidence_coverage: float  # 0.0–1.0; 1.0 when no INFORMATIONAL signals
    diagnostics: list[GovernanceQualityDiagnostic] = field(default_factory=list)


def build_governance_quality_metrics(
    signals: list[GovernedSignal],
) -> GovernanceQualityMetrics:
    """Compute read-only quality metrics from governed signals.

    Metrics are descriptive. They do not alter findings, advisories,
    risk scores, signal dispositions, or work-package behavior.
    """
    from collections import Counter

    if not signals:
        return GovernanceQualityMetrics(
            total_signals=0,
            by_family={},
            by_disposition={},
            by_severity={},
            by_confidence={},
            finding_evidence_coverage=1.0,
            finding_metadata_coverage=1.0,
            advisory_evidence_coverage=1.0,
            informational_evidence_coverage=1.0,
            diagnostics=[],
        )

    family_counts: Counter[str] = Counter()
    disposition_counts: Counter[str] = Counter()
    severity_counts: Counter[str] = Counter()
    confidence_counts: Counter[str] = Counter()

    for signal in signals:
        family_counts[signal.family.value] += 1
        disposition_counts[signal.disposition.value] += 1
        severity_counts[signal.severity] += 1
        confidence_counts[signal.confidence] += 1

    # Separate by disposition for coverage calculations
    findings = [s for s in signals if s.disposition == SignalDisposition.FINDING]
    advisories = [s for s in signals if s.disposition == SignalDisposition.ADVISORY]
    informational = [s for s in signals if s.disposition == SignalDisposition.INFORMATIONAL]

    # Evidence coverage: signals with non-empty evidence_ids / total
    # Zero denominator → 1.0 ("no uncovered signals observed")
    def _coverage(subset: list[GovernedSignal]) -> float:
        if not subset:
            return 1.0
        covered = sum(1 for s in subset if s.evidence_ids)
        return covered / len(subset)

    # Metadata coverage: signals with non-empty metadata / total
    def _meta_coverage(subset: list[GovernedSignal]) -> float:
        if not subset:
            return 1.0
        covered = sum(1 for s in subset if s.metadata)
        return covered / len(subset)

    # Build diagnostics
    diagnostics: list[GovernanceQualityDiagnostic] = []
    _build_diagnostics(signals, diagnostics)

    return GovernanceQualityMetrics(
        total_signals=len(signals),
        by_family=dict(family_counts),
        by_disposition=dict(disposition_counts),
        by_severity=dict(severity_counts),
        by_confidence=dict(confidence_counts),
        finding_evidence_coverage=_coverage(findings),
        finding_metadata_coverage=_meta_coverage(findings),
        advisory_evidence_coverage=_coverage(advisories),
        informational_evidence_coverage=_coverage(informational),
        diagnostics=diagnostics,
    )


def _build_diagnostics(
    signals: list[GovernedSignal],
    diagnostics: list[GovernanceQualityDiagnostic],
) -> None:
    """Scan signals for quality conditions. Diagnostics are info/warning only."""
    for signal in signals:
        family = signal.family.value

        # GQM-001: Finding signal lacks evidence IDs
        if signal.disposition == SignalDisposition.FINDING and not signal.evidence_ids:
            diagnostics.append(GovernanceQualityDiagnostic(
                code="GQM-001",
                severity="warning",
                message=f"FINDING signal in {family} family has no evidence IDs",
                family=family,
            ))

        # GQM-002: Advisory signal lacks evidence IDs or metadata basis
        # For v3.23.0, any non-empty metadata counts as basis.
        if signal.disposition == SignalDisposition.ADVISORY:
            if not signal.evidence_ids and not signal.metadata:
                diagnostics.append(GovernanceQualityDiagnostic(
                    code="GQM-002",
                    severity="info",
                    message=f"ADVISORY signal in {family} family has no evidence IDs or metadata basis",
                    family=family,
                ))

        # GQM-003: Informational signal lacks evidence IDs
        if signal.disposition == SignalDisposition.INFORMATIONAL and not signal.evidence_ids:
            diagnostics.append(GovernanceQualityDiagnostic(
                code="GQM-003",
                severity="info",
                message=f"INFORMATIONAL signal in {family} family has no evidence IDs",
                family=family,
            ))

        # GQM-004: Signal metadata empty (info only)
        if not signal.metadata and signal.disposition != SignalDisposition.SUPPRESSED:
            diagnostics.append(GovernanceQualityDiagnostic(
                code="GQM-004",
                severity="info",
                message=f"Signal in {family} family has empty metadata",
                family=family,
            ))

        # GQM-005: Unexpected severity or confidence label
        valid_severities = {"Low", "Medium", "High", "Critical"}
        valid_confidences = {"Low", "Medium", "High"}
        if signal.severity not in valid_severities:
            diagnostics.append(GovernanceQualityDiagnostic(
                code="GQM-005",
                severity="warning",
                message=f"Signal in {family} family has unexpected severity: {signal.severity}",
                family=family,
            ))
        if signal.confidence not in valid_confidences:
            diagnostics.append(GovernanceQualityDiagnostic(
                code="GQM-005",
                severity="warning",
                message=f"Signal in {family} family has unexpected confidence: {signal.confidence}",
                family=family,
            ))


def governance_quality_metrics_to_dict(metrics: GovernanceQualityMetrics) -> dict:
    """Serialize governance quality metrics to a JSON-compatible dict.

    All fields are preserved without data loss.
    """
    return {
        "total_signals": metrics.total_signals,
        "by_family": metrics.by_family,
        "by_disposition": metrics.by_disposition,
        "by_severity": metrics.by_severity,
        "by_confidence": metrics.by_confidence,
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


# ── Governance quality trend (v3.24.0) ─────────────────────────────


_GOVERNANCE_QUALITY_TREND_SCHEMA = "governance_quality_trend.v1"


@dataclass(frozen=True)
class GovernanceQualityTrend:
    """Descriptive trend/delta between governance quality snapshots.

    No gates. No thresholds. No enforcement. Descriptive only.
    """

    schema_version: str
    has_previous: bool
    total_signals_delta: int
    evidence_coverage_delta: float
    metadata_coverage_delta: float
    finding_evidence_coverage_delta: float
    advisory_basis_coverage_delta: float
    diagnostic_count_delta: int
    notes: tuple[str, ...]


def _metrics_payload(value: GovernanceQualityMetrics | dict) -> GovernanceQualityMetrics | dict:
    """Normalize nested governance_quality.metrics dict."""
    if isinstance(value, dict) and isinstance(value.get("metrics"), dict):
        return value["metrics"]
    return value


def _metric_value(metrics: GovernanceQualityMetrics | dict, key: str, default: float | int = 0) -> float | int:
    """Extract metric value from dataclass or dict, default on missing."""
    if isinstance(metrics, dict):
        return metrics.get(key, default)
    return getattr(metrics, key, default)


def _diagnostic_count(value: GovernanceQualityMetrics | dict) -> int:
    """Count diagnostics from list length or field, fallback 0."""
    if isinstance(value, dict):
        diagnostics = value.get("diagnostics")
        if isinstance(diagnostics, list):
            return len(diagnostics)
        return int(value.get("diagnostic_count", 0) or 0)
    diagnostics = getattr(value, "diagnostics", None)
    if isinstance(diagnostics, list):
        return len(diagnostics)
    return int(getattr(value, "diagnostic_count", 0) or 0)


def build_governance_quality_trend(
    *,
    current: GovernanceQualityMetrics | dict,
    previous: GovernanceQualityMetrics | dict | None,
) -> GovernanceQualityTrend:
    """Build descriptive trend between current and previous governance quality.

    Pure, non-throwing. Supports dataclass, flat dict, and nested dict inputs.
    No gates. No thresholds. Descriptive only.
    """
    if previous is None:
        return GovernanceQualityTrend(
            schema_version=_GOVERNANCE_QUALITY_TREND_SCHEMA,
            has_previous=False,
            total_signals_delta=0,
            evidence_coverage_delta=0.0,
            metadata_coverage_delta=0.0,
            finding_evidence_coverage_delta=0.0,
            advisory_basis_coverage_delta=0.0,
            diagnostic_count_delta=0,
            notes=("No previous governance quality snapshot available.",),
        )

    cur = _metrics_payload(current)
    prev = _metrics_payload(previous)

    cur_signals = int(_metric_value(cur, "total_signals", 0) or 0)
    prev_signals = int(_metric_value(prev, "total_signals", 0) or 0)

    # Evidence coverage: average of finding, advisory, informational
    def _avg_coverage(m) -> float:
        vals = [
            float(_metric_value(m, "finding_evidence_coverage", 1.0) or 1.0),
            float(_metric_value(m, "advisory_evidence_coverage", 1.0) or 1.0),
            float(_metric_value(m, "informational_evidence_coverage", 1.0) or 1.0),
        ]
        return sum(vals) / len(vals)

    def _metadata_cov(m) -> float:
        return float(_metric_value(m, "finding_metadata_coverage", 1.0) or 1.0)

    cur_ev = _avg_coverage(cur)
    prev_ev = _avg_coverage(prev)
    cur_meta = _metadata_cov(cur)
    prev_meta = _metadata_cov(prev)

    cur_finding_ev = float(_metric_value(cur, "finding_evidence_coverage", 1.0) or 1.0)
    prev_finding_ev = float(_metric_value(prev, "finding_evidence_coverage", 1.0) or 1.0)

    # Advisory basis coverage: advisory_evidence_coverage serves as proxy
    cur_adv = float(_metric_value(cur, "advisory_evidence_coverage", 1.0) or 1.0)
    prev_adv = float(_metric_value(prev, "advisory_evidence_coverage", 1.0) or 1.0)

    cur_diag = _diagnostic_count(current)
    prev_diag = _diagnostic_count(previous)

    notes_list: list[str] = []

    return GovernanceQualityTrend(
        schema_version=_GOVERNANCE_QUALITY_TREND_SCHEMA,
        has_previous=True,
        total_signals_delta=cur_signals - prev_signals,
        evidence_coverage_delta=round(cur_ev - prev_ev, 6),
        metadata_coverage_delta=round(cur_meta - prev_meta, 6),
        finding_evidence_coverage_delta=round(cur_finding_ev - prev_finding_ev, 6),
        advisory_basis_coverage_delta=round(cur_adv - prev_adv, 6),
        diagnostic_count_delta=cur_diag - prev_diag,
        notes=tuple(notes_list),
    )


def governance_quality_trend_to_dict(trend: GovernanceQualityTrend) -> dict:
    """Serialize governance quality trend to a JSON-compatible dict.

    All fields preserved losslessly.
    """
    return {
        "schema_version": trend.schema_version,
        "has_previous": trend.has_previous,
        "total_signals_delta": trend.total_signals_delta,
        "evidence_coverage_delta": trend.evidence_coverage_delta,
        "metadata_coverage_delta": trend.metadata_coverage_delta,
        "finding_evidence_coverage_delta": trend.finding_evidence_coverage_delta,
        "advisory_basis_coverage_delta": trend.advisory_basis_coverage_delta,
        "diagnostic_count_delta": trend.diagnostic_count_delta,
        "notes": list(trend.notes),
    }
