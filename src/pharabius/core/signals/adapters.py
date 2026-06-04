"""Runtime signal adapters.

Translate runtime domain IR into platform-level GovernedSignal instances.
Runtime keeps its internal IR (RuntimeEvidence, RuntimeConflictGroup,
RuntimeSourceGrade). These adapters are thin translation layers.
"""

from __future__ import annotations

from pharabius.core.runtime.models import (
    RuntimeConflictGroup,
    RuntimeEcosystem,
    RuntimeEvidence,
)
from pharabius.core.signals.models import (
    GovernedSignal,
    SignalDisposition,
    SignalFamily,
    make_signal_id,
)


def runtime_conflict_to_signal(conflict: RuntimeConflictGroup) -> GovernedSignal:
    """Adapt a RuntimeConflictGroup into a GovernedSignal (FINDING).

    Runtime conflicts are always findings — they represent definite
    contradictions in runtime declarations.
    """
    evidence_ids = [e.runtime_evidence_id for e in conflict.evidence]
    signal_id = make_signal_id("runtime", conflict.conflict_kind.value, evidence_ids)

    return GovernedSignal(
        signal_id=signal_id,
        family=SignalFamily.RUNTIME,
        kind=conflict.conflict_kind.value,
        disposition=SignalDisposition.FINDING,
        category="TD-DEP",
        severity="Medium",
        confidence="High",
        evidence_ids=evidence_ids,
        source_signal_ids=[],
        title=f"{conflict.runtime_name} runtime version declarations conflict",
        summary=f"Multiple {conflict.runtime_name} runtime version declarations disagree.",
        explanation=conflict.explanation,
        metadata={
            "runtime_name": conflict.runtime_name,
            "ecosystem": conflict.ecosystem.value,
            "conflict_kind": conflict.conflict_kind.value,
        },
    )


def runtime_missing_pin_to_signal(
    runtime_name: str,
    ecosystem: RuntimeEcosystem,
    trigger_files: list[str],
    evidence_ids: list[str],
) -> GovernedSignal:
    """Adapt a missing runtime pin into a GovernedSignal (ADVISORY).

    Missing pins are advisories — hygiene observations, not actionable debt.
    They do not generate work packages.
    """
    signal_id = make_signal_id("runtime", "missing_runtime_pin", [runtime_name])

    return GovernedSignal(
        signal_id=signal_id,
        family=SignalFamily.RUNTIME,
        kind="missing_runtime_pin",
        disposition=SignalDisposition.ADVISORY,
        category="TD-DEP",
        severity="Low",
        confidence="Low",
        evidence_ids=evidence_ids,
        source_signal_ids=[],
        title=f"Missing runtime version pins for: {runtime_name}",
        summary=(
            f"Dependency manifests exist for {runtime_name} but no runtime "
            "version pinning file detected."
        ),
        explanation=(
            f"{runtime_name} manifests ({', '.join(trigger_files)}) detected "
            f"but no reproducibility pin found. Runtime drift affects builds."
        ),
        metadata={
            "runtime_name": runtime_name,
            "ecosystem": ecosystem.value,
            "trigger_files": trigger_files,
        },
    )


def runtime_evidence_to_signal(evidence: RuntimeEvidence) -> GovernedSignal:
    """Adapt a RuntimeEvidence item into a GovernedSignal (INFORMATIONAL).

    Individual evidence items that are neither conflicts nor missing pins
    are informational — they provide context and coverage visibility.
    """
    signal_id = make_signal_id(
        "runtime",
        "evidence",
        [evidence.runtime_evidence_id],
    )

    version = evidence.raw_version or evidence.constraint.value or "?"

    return GovernedSignal(
        signal_id=signal_id,
        family=SignalFamily.RUNTIME,
        kind=f"runtime_evidence_{evidence.constraint.kind.value}",
        disposition=SignalDisposition.INFORMATIONAL,
        category="TD-DEP",
        severity="Low",
        confidence=evidence.confidence.value,
        evidence_ids=[evidence.runtime_evidence_id],
        source_signal_ids=[],
        title=f"{evidence.runtime_name} runtime evidence: {version}",
        summary=(
            f"{evidence.runtime_name} runtime version {evidence.constraint.kind.value} "
            f"from {evidence.source_path}"
        ),
        explanation=(
            f"{evidence.runtime_name} {version} detected in {evidence.source_path} "
            f"(grade={evidence.source_grade.value}, "
            f"constraint={evidence.constraint.kind.value})."
        ),
        metadata={
            "runtime_name": evidence.runtime_name,
            "ecosystem": evidence.ecosystem.value,
            "source_grade": evidence.source_grade.value,
            "constraint_kind": evidence.constraint.kind.value,
            "source_path": evidence.source_path,
            "source_detail": evidence.source_detail,
        },
    )


# ── Evidence-based adapters (for analyzer consumption) ────────────────


def runtime_conflict_to_signal_from_evidence(evidence_item: object) -> GovernedSignal:
    """Adapt a conflict EvidenceItem into a GovernedSignal (FINDING).

    Used by the analyzer which consumes EvidenceItems, not RuntimeConflictGroup.
    """
    # EvidenceItem is a Pydantic model — access via attributes
    ev_id = getattr(evidence_item, "evidence_id", "unknown")
    meta = getattr(evidence_item, "metadata", {}) or {}
    runtime = meta.get("runtime", "unknown")
    conflict_kind = meta.get("conflict_reason", "unknown")

    signal_id = make_signal_id("runtime", conflict_kind, [ev_id])

    return GovernedSignal(
        signal_id=signal_id,
        family=SignalFamily.RUNTIME,
        kind=conflict_kind,
        disposition=SignalDisposition.FINDING,
        category="TD-DEP",
        severity="Medium",
        confidence="High",
        evidence_ids=[ev_id],
        source_signal_ids=[],
        title=f"{runtime} runtime version declarations conflict",
        summary=f"Multiple {runtime} runtime version declarations disagree.",
        explanation=getattr(evidence_item, "summary", ""),
        metadata={
            "runtime_name": runtime,
            "conflict_kind": conflict_kind,
        },
    )


def runtime_missing_pin_to_signal_from_evidence(
    evidence_items: list[object],
) -> GovernedSignal:
    """Adapt missing-pin EvidenceItems into a GovernedSignal (ADVISORY).

    Used by the analyzer which consumes EvidenceItems.
    """
    ev_ids = [getattr(e, "evidence_id", "unknown") for e in evidence_items]
    runtimes = []
    for e in evidence_items:
        meta = getattr(e, "metadata", {}) or {}
        rt = meta.get("runtime", "unknown")
        if rt not in runtimes:
            runtimes.append(rt)

    signal_id = make_signal_id("runtime", "missing_runtime_pin", runtimes)

    return GovernedSignal(
        signal_id=signal_id,
        family=SignalFamily.RUNTIME,
        kind="missing_runtime_pin",
        disposition=SignalDisposition.ADVISORY,
        category="TD-DEP",
        severity="Low",
        confidence="Low",
        evidence_ids=ev_ids,
        source_signal_ids=[],
        title=f"Missing runtime version pins for: {', '.join(runtimes)}",
        summary=(
            f"Dependency manifests exist for {', '.join(runtimes)} but no runtime "
            "version pinning file detected."
        ),
        explanation=(f"{', '.join(runtimes)} manifests detected but no reproducibility pin found."),
        metadata={
            "runtimes": runtimes,
        },
    )


# ── Documentation signal adapters (v3.13.0) ───────────────────────────


def docs_missing_to_signal(
    evidence_ids: list[str],
    category: str = "TD-DOC",
    title: str = "No documentation evidence detected",
    summary: str = (
        "The repository scan did not detect common documentation files such as README, "
        "docs, ADRs, changelog, or contributing guidance."
    ),
    explanation: str = (
        "Missing documentation increases onboarding cost and makes architectural intent, "
        "setup steps, and operational procedures harder to verify."
    ),
) -> GovernedSignal:
    """Adapt missing documentation into a GovernedSignal (ADVISORY).

    Missing documentation is advisory — it does not generate work packages.
    The analyzer preserves its own title/description/severity/risk fields;
    this adapter provides the signal-level representation.
    """
    signal_id = make_signal_id("documentation", "missing_documentation", evidence_ids[:1])

    return GovernedSignal(
        signal_id=signal_id,
        family=SignalFamily.DOCUMENTATION,
        kind="missing_documentation",
        disposition=SignalDisposition.ADVISORY,
        category=category,
        severity="Low",
        confidence="Low",
        evidence_ids=evidence_ids,
        source_signal_ids=[],
        title=title,
        summary=summary,
        explanation=explanation,
        metadata={"missing_docs": True},
    )


def docs_evidence_to_signal(
    evidence_item: object,
) -> GovernedSignal:
    """Adapt a detected documentation file into a GovernedSignal (INFORMATIONAL).

    Detected documentation provides coverage context — informational only.
    """
    ev_id = getattr(evidence_item, "evidence_id", "unknown")
    file_path = getattr(getattr(evidence_item, "location", None), "file", "")

    signal_id = make_signal_id("documentation", "documentation_evidence", [ev_id])

    return GovernedSignal(
        signal_id=signal_id,
        family=SignalFamily.DOCUMENTATION,
        kind="documentation_evidence",
        disposition=SignalDisposition.INFORMATIONAL,
        category="TD-DOC",
        severity="Low",
        confidence="Medium",
        evidence_ids=[ev_id],
        source_signal_ids=[],
        title=f"Documentation file detected: {file_path or 'unknown'}",
        summary=f"Documentation evidence found at {file_path or 'unknown'}.",
        explanation="Detected documentation file provides coverage context.",
        metadata={"source_file": file_path},
    )


# ── Build signal adapters (v3.13.0) ────────────────────────────────────


def build_missing_ci_to_signal(
    evidence_ids: list[str],
    category: str = "TD-BUILD",
    title: str = "No CI/CD workflow evidence detected",
    summary: str = (
        "The repository scan did not detect common CI/CD workflow files such as GitHub "
        "Actions, GitLab CI, Jenkins, Bitbucket Pipelines, or Azure Pipelines."
    ),
    explanation: str = (
        "Without automated quality gates, formatting, linting, type checking, tests, and "
        "architecture checks may not be enforced consistently before merge."
    ),
) -> GovernedSignal:
    """Adapt missing CI/CD into a GovernedSignal (ADVISORY).

    Missing CI/CD is advisory — it does not generate work packages.
    """
    signal_id = make_signal_id("build", "missing_ci_cd", evidence_ids[:1])

    return GovernedSignal(
        signal_id=signal_id,
        family=SignalFamily.BUILD,
        kind="missing_ci_cd",
        disposition=SignalDisposition.ADVISORY,
        category=category,
        severity="Low",
        confidence="Low",
        evidence_ids=evidence_ids,
        source_signal_ids=[],
        title=title,
        summary=summary,
        explanation=explanation,
        metadata={"missing_ci": True},
    )


def build_ci_evidence_to_signal(
    evidence_item: object,
) -> GovernedSignal:
    """Adapt a detected CI/deployment file into a GovernedSignal (INFORMATIONAL).

    Detected CI evidence provides coverage context — informational only.
    """
    ev_id = getattr(evidence_item, "evidence_id", "unknown")
    file_path = getattr(getattr(evidence_item, "location", None), "file", "")

    signal_id = make_signal_id("build", "ci_evidence", [ev_id])

    return GovernedSignal(
        signal_id=signal_id,
        family=SignalFamily.BUILD,
        kind="ci_evidence",
        disposition=SignalDisposition.INFORMATIONAL,
        category="TD-BUILD",
        severity="Low",
        confidence="Medium",
        evidence_ids=[ev_id],
        source_signal_ids=[],
        title=f"CI/CD evidence detected: {file_path or 'unknown'}",
        summary=f"CI/CD evidence found at {file_path or 'unknown'}.",
        explanation="Detected CI/CD file provides coverage context.",
        metadata={"source_file": file_path},
    )


# ── Process signal adapters (v3.13.0) ─────────────────────────────────


def process_missing_artifacts_to_signal(
    missing_artifacts: list[str],
    evidence_ids: list[str],
    category: str = "TD-PROCESS",
    title: str = "Missing repository process artifacts",
    summary: str = "",
    explanation: str = (
        "Missing process artifacts weaken code review, onboarding, and release governance. "
        "Impact depends on team size and repository criticality."
    ),
) -> GovernedSignal:
    """Adapt missing process artifacts into a GovernedSignal (ADVISORY).

    Missing CODEOWNERS/CONTRIBUTING/PR templates are process advisories.
    They do not generate work packages.
    """
    signal_id = make_signal_id("process", "missing_process_artifacts", evidence_ids[:1])

    if not summary:
        summary = (
            f"{len(missing_artifacts)} process artifact(s) missing: "
            f"{', '.join(missing_artifacts[:5])}. "
            "These artifacts support code review quality, onboarding, and release governance."
        )

    return GovernedSignal(
        signal_id=signal_id,
        family=SignalFamily.PROCESS,
        kind="missing_process_artifacts",
        disposition=SignalDisposition.ADVISORY,
        category=category,
        severity="Low",
        confidence="Low",
        evidence_ids=evidence_ids,
        source_signal_ids=[],
        title=title,
        summary=summary,
        explanation=explanation,
        metadata={"missing_artifacts": missing_artifacts},
    )


# ── Test signal adapters (v3.14.0) ───────────────────────────────────


def scan_test_missing_to_signal(
    evidence_ids: list[str],
    has_risk_signals: bool = False,
    category: str = "TD-TEST",
    title: str = "No test evidence detected",
    summary: str = (
        "The repository scan did not detect test files or package test scripts. "
        "This increases regression risk and weakens confidence in future remediation work."
    ),
    explanation: str = (
        "Without detectable tests, changes to existing behavior are harder to verify and "
        "technical debt remediation becomes riskier."
    ),
) -> GovernedSignal:
    """Adapt missing tests into a GovernedSignal (FINDING).

    Missing tests are a finding — they represent actionable technical debt.
    """
    severity = "High" if has_risk_signals else "Medium"
    signal_id = make_signal_id("test", "missing_tests", evidence_ids[:1])

    return GovernedSignal(
        signal_id=signal_id,
        family=SignalFamily.TEST,
        kind="missing_tests",
        disposition=SignalDisposition.FINDING,
        category=category,
        severity=severity,
        confidence="Medium",
        evidence_ids=evidence_ids,
        source_signal_ids=[],
        title=title,
        summary=summary,
        explanation=explanation,
        metadata={"has_risk_signals": has_risk_signals},
    )


def scan_test_risk_sensitive_without_tests_to_signal(
    evidence_ids: list[str],
    category: str = "TD-SEC",
    title: str = "Risk-sensitive areas detected without test evidence",
    summary: str = (
        "The repository contains security, compliance, operational, or business-sensitive "
        "signals, but the scan did not detect automated test evidence."
    ),
    explanation: str = (
        "Risk-sensitive paths without detectable tests increase the probability of unsafe "
        "behavioral changes during maintenance or remediation."
    ),
) -> GovernedSignal:
    """Adapt risk-sensitive-without-tests into a GovernedSignal (FINDING).

    This is a higher-severity finding — risk-sensitive areas need test coverage.
    """
    signal_id = make_signal_id("test", "risk_sensitive_without_tests", evidence_ids[:1])

    return GovernedSignal(
        signal_id=signal_id,
        family=SignalFamily.TEST,
        kind="risk_sensitive_without_tests",
        disposition=SignalDisposition.FINDING,
        category=category,
        severity="High",
        confidence="Medium",
        evidence_ids=evidence_ids,
        source_signal_ids=[],
        title=title,
        summary=summary,
        explanation=explanation,
        metadata={"risk_sensitive": True},
    )


def scan_test_coverage_gap_to_signal(
    evidence_ids: list[str],
    low_count: int = 0,
    threshold_pct: float = 0.0,
    category: str = "TD-TEST",
    title: str = "",
    summary: str = "",
    explanation: str = "Low test coverage means changes are more likely to introduce undetected regressions.",
) -> GovernedSignal:
    """Adapt coverage gaps into a GovernedSignal (FINDING).

    Low coverage is a finding — it represents actionable test debt.
    """
    if not title:
        title = f"Low test coverage detected ({low_count} metric(s) below {threshold_pct:.0f}%)"
    if not summary:
        summary = (
            f"Coverage report shows {low_count} metric(s) below "
            f"{threshold_pct:.0f}%. "
            "Low coverage increases regression risk."
        )

    signal_id = make_signal_id("test", "coverage_gap", evidence_ids[:1])

    return GovernedSignal(
        signal_id=signal_id,
        family=SignalFamily.TEST,
        kind="coverage_gap",
        disposition=SignalDisposition.FINDING,
        category=category,
        severity="Medium",
        confidence="Medium",
        evidence_ids=evidence_ids,
        source_signal_ids=[],
        title=title,
        summary=summary,
        explanation=explanation,
        metadata={"low_count": low_count, "threshold_pct": threshold_pct},
    )


def scan_test_evidence_to_signal(
    evidence_item: object,
) -> GovernedSignal:
    """Adapt a detected test file into a GovernedSignal (INFORMATIONAL).

    Detected test files provide coverage context — informational only.
    """
    ev_id = getattr(evidence_item, "evidence_id", "unknown")
    file_path = getattr(getattr(evidence_item, "location", None), "file", "")

    signal_id = make_signal_id("test", "test_evidence", [ev_id])

    return GovernedSignal(
        signal_id=signal_id,
        family=SignalFamily.TEST,
        kind="test_evidence",
        disposition=SignalDisposition.INFORMATIONAL,
        category="TD-TEST",
        severity="Low",
        confidence="Medium",
        evidence_ids=[ev_id],
        source_signal_ids=[],
        title=f"Test file detected: {file_path or 'unknown'}",
        summary=f"Test evidence found at {file_path or 'unknown'}.",
        explanation="Detected test file provides coverage context.",
        metadata={"source_file": file_path},
    )


def scan_test_coverage_evidence_to_signal(
    evidence_item: object,
) -> GovernedSignal:
    """Adapt a detected coverage report/metric into a GovernedSignal (INFORMATIONAL).

    Detected coverage evidence provides context — informational only.
    """
    ev_id = getattr(evidence_item, "evidence_id", "unknown")
    file_path = getattr(getattr(evidence_item, "location", None), "file", "")
    ev_type = getattr(evidence_item, "type", "unknown")

    signal_id = make_signal_id("test", "coverage_evidence", [ev_id])

    return GovernedSignal(
        signal_id=signal_id,
        family=SignalFamily.TEST,
        kind="coverage_evidence",
        disposition=SignalDisposition.INFORMATIONAL,
        category="TD-TEST",
        severity="Low",
        confidence="Medium",
        evidence_ids=[ev_id],
        source_signal_ids=[],
        title=f"Coverage evidence detected: {file_path or ev_type}",
        summary=f"Coverage evidence found: {ev_type}.",
        explanation="Detected coverage report/metric provides test coverage context.",
        metadata={"source_file": file_path, "evidence_type": ev_type},
    )
