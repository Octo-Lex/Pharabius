"""Dependency signal adapters.

Translate dependency-health evidence into platform-level GovernedSignal
instances. Dependency signals answer: what dependency-management condition
exists?

v3.16.0: Adoption release — adapters match existing behavior exactly.
No promotion upgrades, no new dispositions.
"""

from __future__ import annotations

from pharabius.core.signals.models import (
    GovernedSignal,
    SignalDisposition,
    SignalFamily,
    make_signal_id,
)

# ── Informational adapters ────────────────────────────────────────────


def dependency_manifest_detected_to_signal(
    evidence_item: object,
) -> GovernedSignal:
    """Adapt a detected manifest into a GovernedSignal (INFORMATIONAL).

    Manifest detection provides coverage context — informational only.
    """
    ev_id = getattr(evidence_item, "evidence_id", "unknown")
    file_path = getattr(getattr(evidence_item, "location", None), "file", "")
    ecosystem = ""
    meta = getattr(evidence_item, "metadata", {}) or {}
    if isinstance(meta, dict):
        ecosystem = meta.get("ecosystem", "")

    signal_id = make_signal_id("dependency", "manifest_detected", [ev_id])

    return GovernedSignal(
        signal_id=signal_id,
        family=SignalFamily.DEPENDENCY,
        kind="manifest_detected",
        disposition=SignalDisposition.INFORMATIONAL,
        category="TD-DEP",
        severity="Low",
        confidence="Medium",
        evidence_ids=[ev_id],
        source_signal_ids=[],
        title=f"Dependency manifest detected: {file_path or 'unknown'}",
        summary=f"Dependency manifest found at {file_path or 'unknown'}.",
        explanation="Detected manifest provides dependency coverage context.",
        metadata={"source_file": file_path, "ecosystem": ecosystem},
    )


# ── Advisory adapters (match existing behavior) ──────────────────────


def dependency_missing_lockfile_to_signal(
    evidence_items: list[object],
    *,
    ecosystem: str = "",
    package_root: str = ".",
) -> GovernedSignal:
    """Adapt missing lockfile evidence into a GovernedSignal (ADVISORY).

    Missing lockfiles are advisories — they do not generate work packages.
    Disposition copied from existing _emit_lockfile_finding behavior
    (issue_type="advisory"). No new ecosystem-specific lockfile policy.
    """
    ev_ids = [getattr(e, "evidence_id", "unknown") for e in evidence_items]
    trigger_files = []
    for e in evidence_items:
        loc = getattr(e, "location", None)
        if loc:
            f = getattr(loc, "file", "")
            if f:
                trigger_files.append(f)

    signal_id = make_signal_id("dependency", "missing_lockfile", ev_ids)

    root_label = "repository root" if package_root == "." else package_root

    return GovernedSignal(
        signal_id=signal_id,
        family=SignalFamily.DEPENDENCY,
        kind="missing_lockfile",
        disposition=SignalDisposition.ADVISORY,
        category="TD-DEP",
        severity="Medium",
        confidence="High",
        evidence_ids=ev_ids,
        source_signal_ids=[],
        title=(f"{ecosystem or 'Unknown'} dependency manifest detected without lockfile evidence"),
        summary=(
            f"The repository contains {ecosystem or ''} dependency manifest(s) in "
            f"{root_label}, but the scan did not detect corresponding "
            f"lockfile evidence for that package root."
        ),
        explanation=(
            "Missing lockfile evidence may reduce dependency reproducibility "
            "across local, CI, and deployment environments."
        ),
        metadata={
            "ecosystem": ecosystem,
            "package_root": package_root,
            "trigger_files": trigger_files,
        },
    )


def dependency_manifest_without_lockfile_to_signal(
    evidence_item: object,
) -> GovernedSignal:
    """Adapt poetry/pipfile manifest-without-lockfile into a GovernedSignal (ADVISORY).

    Used for parser-level signals like poetry_manifest_without_lockfile
    and pipfile_without_lockfile.
    """
    ev_id = getattr(evidence_item, "evidence_id", "unknown")
    meta = getattr(evidence_item, "metadata", {}) or {}
    ecosystem = meta.get("ecosystem", "") if isinstance(meta, dict) else ""
    signal_type = meta.get("signal", "manifest_without_lockfile") if isinstance(meta, dict) else ""

    signal_id = make_signal_id("dependency", signal_type, [ev_id])

    return GovernedSignal(
        signal_id=signal_id,
        family=SignalFamily.DEPENDENCY,
        kind=signal_type,
        disposition=SignalDisposition.ADVISORY,
        category="TD-DEP",
        severity="Medium",
        confidence="High",
        evidence_ids=[ev_id],
        source_signal_ids=[],
        title=getattr(evidence_item, "summary", f"{ecosystem} manifest without lockfile"),
        summary=getattr(evidence_item, "summary", ""),
        explanation=(
            f"{ecosystem} dependency manifest detected without a corresponding "
            f"lockfile. This may reduce dependency reproducibility."
        ),
        metadata={"ecosystem": ecosystem, "signal": signal_type},
    )


# ── Finding adapters (match existing behavior) ───────────────────────


def dependency_unpinned_to_signal(
    evidence_items: list[object],
    *,
    ecosystem: str = "",
    count: int = 0,
) -> GovernedSignal:
    """Adapt unpinned dependency evidence into a GovernedSignal (FINDING).

    Unpinned dependencies are findings in existing behavior — they
    produce actionable TD-DEP entries. Disposition matches current
    _analyze_dependency_signals behavior exactly.
    """
    ev_ids = [getattr(e, "evidence_id", "unknown") for e in evidence_items]

    signal_id = make_signal_id("dependency", "unpinned_dependency", ev_ids)

    return GovernedSignal(
        signal_id=signal_id,
        family=SignalFamily.DEPENDENCY,
        kind="unpinned_dependency",
        disposition=SignalDisposition.FINDING,
        category="TD-DEP",
        severity="Medium",
        confidence="Medium",
        evidence_ids=ev_ids,
        source_signal_ids=[],
        title=(f"Unpinned {ecosystem} dependencies detected ({count} unpinned)"),
        summary=(
            f"{count} {ecosystem} dependencies use unpinned or broad "
            "version ranges. This reduces build reproducibility "
            "and makes dependency audits harder."
        ),
        explanation=(
            "Unpinned dependencies can change without warning, "
            "breaking builds or introducing vulnerabilities."
        ),
        metadata={"ecosystem": ecosystem, "count": count},
    )


def dependency_lockfile_conflict_to_signal(
    evidence_items: list[object],
    *,
    lockfiles: list[str] | None = None,
) -> GovernedSignal:
    """Adapt lockfile conflict evidence into a GovernedSignal (FINDING).

    Lockfile conflicts are findings in existing behavior. Disposition
    matches current _analyze_dependency_signals behavior exactly.
    """
    ev_ids = [getattr(e, "evidence_id", "unknown") for e in evidence_items]
    lf_names = lockfiles or []

    signal_id = make_signal_id("dependency", "lockfile_conflict", ev_ids)

    return GovernedSignal(
        signal_id=signal_id,
        family=SignalFamily.DEPENDENCY,
        kind="lockfile_conflict",
        disposition=SignalDisposition.FINDING,
        category="TD-DEP",
        severity="Medium",
        confidence="Medium",
        evidence_ids=ev_ids,
        source_signal_ids=[],
        title=f"Multiple Node.js lockfiles detected: {', '.join(lf_names)}",
        summary=(
            "Multiple lockfiles for the same ecosystem can cause "
            "inconsistent dependency resolution across environments."
        ),
        explanation=(
            "Different developers may get different dependency trees "
            "depending on which package manager they use."
        ),
        metadata={"lockfiles": lf_names},
    )


def dependency_orphan_lockfile_to_signal(
    evidence_item: object,
) -> GovernedSignal:
    """Adapt orphan lockfile (without manifest) into a GovernedSignal (ADVISORY).

    Lockfiles without manifests are advisory — suspicious but not
    necessarily actionable debt.
    """
    ev_id = getattr(evidence_item, "evidence_id", "unknown")
    meta = getattr(evidence_item, "metadata", {}) or {}
    ecosystem = meta.get("ecosystem", "") if isinstance(meta, dict) else ""
    signal_type = meta.get("signal", "orphan_lockfile") if isinstance(meta, dict) else ""

    signal_id = make_signal_id("dependency", signal_type, [ev_id])

    return GovernedSignal(
        signal_id=signal_id,
        family=SignalFamily.DEPENDENCY,
        kind=signal_type,
        disposition=SignalDisposition.ADVISORY,
        category="TD-DEP",
        severity="Low",
        confidence="High",
        evidence_ids=[ev_id],
        source_signal_ids=[],
        title=getattr(evidence_item, "summary", f"{ecosystem} lockfile without manifest"),
        summary=getattr(evidence_item, "summary", ""),
        explanation=(
            f"A {ecosystem} lockfile was detected without a corresponding "
            f"manifest. This may indicate incomplete repository contents."
        ),
        metadata={"ecosystem": ecosystem, "signal": signal_type},
    )


def dependency_parse_failure_to_signal(
    evidence_item: object,
) -> GovernedSignal:
    """Adapt a manifest parse failure into a GovernedSignal (ADVISORY).

    Parse failures limit coverage — they are advisory, not findings.
    """
    ev_id = getattr(evidence_item, "evidence_id", "unknown")
    meta = getattr(evidence_item, "metadata", {}) or {}
    ecosystem = meta.get("ecosystem", "") if isinstance(meta, dict) else ""
    manifest = meta.get("manifest", "") if isinstance(meta, dict) else ""

    signal_id = make_signal_id("dependency", "dependency_manifest_parse_failure", [ev_id])

    return GovernedSignal(
        signal_id=signal_id,
        family=SignalFamily.DEPENDENCY,
        kind="dependency_manifest_parse_failure",
        disposition=SignalDisposition.ADVISORY,
        category="TD-DEP",
        severity="Low",
        confidence="Low",
        evidence_ids=[ev_id],
        source_signal_ids=[],
        title=f"Could not parse {manifest or 'dependency manifest'}",
        summary=getattr(evidence_item, "summary", f"Could not parse {manifest}"),
        explanation=(
            f"Parse failure limits dependency analysis coverage for "
            f"{ecosystem} manifest {manifest}."
        ),
        metadata={"ecosystem": ecosystem, "manifest": manifest},
    )
