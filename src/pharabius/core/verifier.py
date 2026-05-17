"""Deterministic verification of debt-register findings against current evidence."""

from __future__ import annotations

import json
import re
from pathlib import Path

from pharabius.core.analyzer import analyze_evidence
from pharabius.schemas.analysis_unit import AnalysisUnitStore
from pharabius.schemas.evidence import EvidenceStore
from pharabius.schemas.finding import DebtFinding, DebtRegister
from pharabius.schemas.verification import (
    VerificationReport,
    VerificationResult,
    WorkPackageVerificationResult,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

STATUS_STILL_DETECTED = "still_detected"
STATUS_LIKELY_REMEDIATED = "likely_remediated"
STATUS_EVIDENCE_MISSING = "evidence_missing"
STATUS_PARTIALLY_SUPPORTED = "partially_supported"
STATUS_STALE = "stale"
STATUS_UNCERTAIN = "uncertain"

EVIDENCE_OVERLAP_THRESHOLD = 0.5

# ---------------------------------------------------------------------------
# Input loading
# ---------------------------------------------------------------------------


def _load_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _load_debt_register(root: Path) -> DebtRegister:
    path = root / ".ai-debt" / "debt-register.json"
    data = _load_json(path)
    if not data:
        raise FileNotFoundError(
            "debt-register.json not found. Run 'ai-debt analyze --no-ai' first."
        )
    return DebtRegister.model_validate(data)


def _load_evidence_store(root: Path) -> EvidenceStore:
    path = root / ".ai-debt" / "evidence.json"
    data = _load_json(path)
    if not data:
        raise FileNotFoundError("evidence.json not found. Run 'ai-debt scan' first.")
    return EvidenceStore.model_validate(data)


def _load_analysis_units(root: Path) -> AnalysisUnitStore | None:
    path = root / ".ai-debt" / "analysis-units.json"
    data = _load_json(path)
    if not data:
        return None
    return AnalysisUnitStore.model_validate(data)


# ---------------------------------------------------------------------------
# Matching logic
# ---------------------------------------------------------------------------


def _normalize_title(title: str) -> str:
    return re.sub(r"\s+", " ", title.strip().lower())


def _normalized_locations(finding: DebtFinding) -> frozenset[str]:
    return frozenset(loc.replace("\\", "/").strip().lower() for loc in finding.locations)


def _evidence_overlap(original: DebtFinding, candidate: DebtFinding) -> float:
    if not original.evidence_ids:
        return 0.0
    orig_set = set(original.evidence_ids)
    cand_set = set(candidate.evidence_ids)
    return len(orig_set & cand_set) / len(orig_set)


def _match_findings(original: DebtFinding, current_findings: list[DebtFinding]) -> list[str]:
    """Match an original finding to current findings using priority rules.

    Returns list of matching current finding IDs (may be empty).
    """
    # Priority 1: same category + evidence overlap >= 50%
    evidence_matches = []
    for cf in current_findings:
        if cf.category != original.category:
            continue
        if _evidence_overlap(original, cf) >= EVIDENCE_OVERLAP_THRESHOLD:
            evidence_matches.append(cf)
    if evidence_matches:
        best = max(evidence_matches, key=lambda cf: _evidence_overlap(original, cf))
        return [best.id]

    # Priority 2: same category + same normalized locations
    orig_locs = _normalized_locations(original)
    if orig_locs:
        for cf in current_findings:
            if cf.category != original.category:
                continue
            if _normalized_locations(cf) == orig_locs:
                return [cf.id]

    # Priority 3: same category + same normalized title
    orig_title = _normalize_title(original.title)
    if orig_title:
        for cf in current_findings:
            if cf.category != original.category:
                continue
            if _normalize_title(cf.title) == orig_title:
                return [cf.id]

    # Priority 4: same finding ID (weak fallback)
    for cf in current_findings:
        if cf.id == original.id and cf.category == original.category:
            return [cf.id]

    return []


# ---------------------------------------------------------------------------
# Location verification
# ---------------------------------------------------------------------------


def _check_locations(finding: DebtFinding, root: Path) -> tuple[list[str], list[str]]:
    present: list[str] = []
    missing: list[str] = []
    for loc in finding.locations:
        if (root / loc).exists():
            present.append(loc)
        else:
            missing.append(loc)
    return present, missing


# ---------------------------------------------------------------------------
# Status assignment
# ---------------------------------------------------------------------------


def _assign_status(
    has_match: bool,
    evidence_present: list[str],
    evidence_missing: list[str],
    locations_missing: list[str],
    all_units_missing: bool,
    units_available: bool,
) -> str:
    """Assign verification status using priority rules.

    Priority order (first matching rule wins):
    1. uncertain — required inputs unavailable
    2. likely_remediated — all gone (locations, evidence, analyzer)
    3. stale — structural mismatch (locations gone + evidence remains, or units gone)
    4. still_detected — match + evidence present
    5. partially_supported — match + evidence partial, or partial evidence no match
    6. evidence_missing — no match + all evidence gone
    """
    some_evidence = len(evidence_present) > 0
    all_evidence_gone = len(evidence_present) == 0 and len(evidence_missing) > 0
    no_evidence_data = len(evidence_present) == 0 and len(evidence_missing) == 0
    ((len(locations_missing) > 0 and len(locations_missing) == len(evidence_missing)) or False)

    # 1. Uncertain — only if we truly can't verify
    # (We don't use this for individual findings in normal flow,
    #  but keep it as a safety net)
    # Not assigning uncertain for normal operation — handled by input checks

    # 2. likely_remediated: no match + all evidence gone + locations gone
    if not has_match and all_evidence_gone and len(locations_missing) > 0:
        return STATUS_LIKELY_REMEDIATED

    # 2b. likely_remediated: no match + no evidence data (old finding had no evidence)
    if not has_match and no_evidence_data and len(locations_missing) > 0:
        return STATUS_LIKELY_REMEDIATED

    # 3. stale: all locations missing but evidence still exists (structural drift)
    if locations_missing and some_evidence and not has_match:
        return STATUS_STALE

    # 3b. stale: all units missing (file exists, finding had units, all gone)
    if all_units_missing and not has_match:
        return STATUS_STALE

    # 4. still_detected: match + at least some evidence
    if has_match and some_evidence:
        return STATUS_STILL_DETECTED

    # 4b. still_detected: match + no evidence data (finding had no evidence_ids)
    if has_match and no_evidence_data:
        return STATUS_STILL_DETECTED

    # 5. partially_supported: match but evidence incomplete
    if has_match and all_evidence_gone:
        return STATUS_PARTIALLY_SUPPORTED

    # 6. evidence_missing: no match + all evidence gone (but no locations missing)
    if not has_match and all_evidence_gone:
        return STATUS_EVIDENCE_MISSING

    # 5b. partially_supported: no match but some evidence
    if not has_match and some_evidence:
        return STATUS_PARTIALLY_SUPPORTED

    # 6b. evidence_missing: no match, no evidence, no locations info
    if not has_match and no_evidence_data:
        return STATUS_EVIDENCE_MISSING

    # Fallback
    return STATUS_UNCERTAIN


# ---------------------------------------------------------------------------
# Work package verification
# ---------------------------------------------------------------------------


def _parse_wp_debt_ids(wp_path: Path) -> list[str]:
    """Extract debt IDs from a work package markdown file."""
    try:
        content = wp_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []

    # Find ## Linked Debt Items section
    ids: list[str] = []
    in_section = False
    for line in content.splitlines():
        if line.strip().lower() == "## linked debt items":
            in_section = True
            continue
        if in_section and line.startswith("## "):
            break
        if in_section:
            for match in re.finditer(r"`([A-Z]+-[A-Z]+-\d+)`", line):
                ids.append(match.group(1))
    return ids


def _verify_work_packages(
    root: Path,
    finding_statuses: dict[str, str],
    source_findings_by_id: dict[str, DebtFinding],
) -> list[WorkPackageVerificationResult]:
    wp_dir = root / ".ai-debt" / "work-packages"
    if not wp_dir.exists():
        return []

    results: list[WorkPackageVerificationResult] = []
    for wp_path in sorted(wp_dir.glob("WP-*.md")):
        wp_rel = wp_path.relative_to(root / ".ai-debt").as_posix()
        debt_ids = _parse_wp_debt_ids(wp_path)

        if not debt_ids:
            results.append(
                WorkPackageVerificationResult(
                    work_package_path=wp_rel,
                    linked_debt_ids=[],
                    status="needs_review",
                    notes=["No linked debt IDs found in work package."],
                )
            )
            continue

        # Check each linked debt ID
        has_orphaned = False
        has_stale = False
        all_valid = True

        for did in debt_ids:
            if did not in source_findings_by_id:
                has_orphaned = True
                all_valid = False
                continue
            status = finding_statuses.get(did, STATUS_UNCERTAIN)
            if status in (STATUS_LIKELY_REMEDIATED, STATUS_STALE):
                has_stale = True
                all_valid = False
            elif status not in (STATUS_STILL_DETECTED, STATUS_PARTIALLY_SUPPORTED):
                all_valid = False

        if has_orphaned:
            wp_status = "orphaned"
            notes = [
                f"Linked finding {did} not in debt register."
                for did in debt_ids
                if did not in source_findings_by_id
            ]
        elif has_stale:
            wp_status = "stale"
            notes = ["Linked finding is likely remediated or stale."]
        elif all_valid:
            wp_status = "valid"
            notes = []
        else:
            wp_status = "needs_review"
            notes = ["Linked findings have mixed or uncertain statuses."]

        results.append(
            WorkPackageVerificationResult(
                work_package_path=wp_rel,
                linked_debt_ids=debt_ids,
                status=wp_status,
                notes=notes,
            )
        )

    return results


# ---------------------------------------------------------------------------
# Main verification
# ---------------------------------------------------------------------------


def verify_repository(repository_root: Path) -> VerificationReport:
    """Run verification and return report. Does NOT modify any files."""
    root = repository_root.resolve()
    ai_debt = root / ".ai-debt"

    # Load inputs
    try:
        source_register = _load_debt_register(root)
    except FileNotFoundError:
        raise
    except Exception as exc:
        raise FileNotFoundError(f"Could not read verification inputs: {exc}") from exc

    try:
        evidence_store = _load_evidence_store(root)
    except FileNotFoundError:
        raise
    except Exception as exc:
        raise FileNotFoundError(f"Could not read verification inputs: {exc}") from exc

    unit_store = _load_analysis_units(root)
    current_evidence_ids = {item.evidence_id for item in evidence_store.evidence}

    # Run current analyzer in memory
    try:
        current_register = analyze_evidence(root)
    except Exception:
        current_register = DebtRegister()

    current_findings = current_register.findings

    # Build source findings lookup
    source_findings_by_id: dict[str, DebtFinding] = {f.id: f for f in source_register.findings}

    # Verify each finding
    results: list[VerificationResult] = []
    finding_statuses: dict[str, str] = {}

    for finding in source_register.findings:
        # Evidence check
        ev_present = [eid for eid in finding.evidence_ids if eid in current_evidence_ids]
        ev_missing = [eid for eid in finding.evidence_ids if eid not in current_evidence_ids]

        # Unit check
        unit_ids_checked = finding.analysis_unit_ids
        units_available = unit_store is not None
        if unit_store is not None:
            current_unit_ids = {u.analysis_unit_id for u in unit_store.units}
            unit_present = [uid for uid in unit_ids_checked if uid in current_unit_ids]
            unit_missing = [uid for uid in unit_ids_checked if uid not in current_unit_ids]
        else:
            unit_present = []
            unit_missing = []

        # Location check
        loc_present, loc_missing = _check_locations(finding, root)

        # Matching
        matched_ids = _match_findings(finding, current_findings)
        has_match = len(matched_ids) > 0

        # All units missing check (only if units file exists and finding had units)
        all_units_missing = units_available and len(unit_ids_checked) > 0 and len(unit_present) == 0

        # Status assignment
        status = _assign_status(
            has_match=has_match,
            evidence_present=ev_present,
            evidence_missing=ev_missing,
            locations_missing=loc_missing,
            all_units_missing=all_units_missing,
            units_available=units_available,
        )

        # Notes
        notes: list[str] = []
        if not units_available and unit_ids_checked:
            notes.append("Analysis units unavailable; unit verification skipped")

        # Recommended action
        rec_action = _recommended_action(status)

        # Work package paths (populated later)
        result = VerificationResult(
            finding_id=finding.id,
            verification_status=status,
            confidence=finding.confidence,
            evidence_ids_checked=finding.evidence_ids,
            evidence_ids_present=ev_present,
            evidence_ids_missing=ev_missing,
            analysis_unit_ids_checked=unit_ids_checked,
            analysis_unit_ids_present=unit_present,
            analysis_unit_ids_missing=unit_missing,
            analysis_units_available=units_available,
            locations_checked=finding.locations,
            locations_present=loc_present,
            locations_missing=loc_missing,
            still_detected_by_current_analyzer=has_match,
            current_matching_finding_ids=matched_ids,
            recommended_action=rec_action,
            notes=notes,
        )
        results.append(result)
        finding_statuses[finding.id] = status

    # Work package verification
    wp_results = _verify_work_packages(root, finding_statuses, source_findings_by_id)

    # Populate work_package_paths on results
    wp_by_debt_id: dict[str, list[str]] = {}
    for wp in wp_results:
        for did in wp.linked_debt_ids:
            wp_by_debt_id.setdefault(did, []).append(wp.work_package_path)
    for result in results:
        result.work_package_paths = wp_by_debt_id.get(result.finding_id, [])

    # Build report
    report = VerificationReport(
        repository=str(root),
        source_debt_register_path=str(ai_debt / "debt-register.json"),
        current_evidence_path=str(ai_debt / "evidence.json"),
        current_analysis_units_path=(
            str(ai_debt / "analysis-units.json") if unit_store is not None else ""
        ),
        current_analyzer_mode="deterministic-no-ai",
        current_evidence_count=len(evidence_store.evidence),
        current_analysis_unit_count=(len(unit_store.units) if unit_store is not None else 0),
        total_findings_checked=len(results),
        still_detected_count=sum(
            1 for r in results if r.verification_status == STATUS_STILL_DETECTED
        ),
        evidence_missing_count=sum(
            1 for r in results if r.verification_status == STATUS_EVIDENCE_MISSING
        ),
        partially_supported_count=sum(
            1 for r in results if r.verification_status == STATUS_PARTIALLY_SUPPORTED
        ),
        likely_remediated_count=sum(
            1 for r in results if r.verification_status == STATUS_LIKELY_REMEDIATED
        ),
        stale_count=sum(1 for r in results if r.verification_status == STATUS_STALE),
        uncertain_count=sum(1 for r in results if r.verification_status == STATUS_UNCERTAIN),
        results=results,
        work_packages_valid=sum(1 for wp in wp_results if wp.status == "valid"),
        work_packages_stale=sum(1 for wp in wp_results if wp.status == "stale"),
        work_packages_orphaned=sum(1 for wp in wp_results if wp.status == "orphaned"),
        work_packages_needs_review=sum(1 for wp in wp_results if wp.status == "needs_review"),
        work_package_results=wp_results,
    )

    return report


def _recommended_action(status: str) -> str:
    actions = {
        STATUS_STILL_DETECTED: (
            "Finding confirmed by current evidence. Follow existing remediation plan."
        ),
        STATUS_LIKELY_REMEDIATED: ("Finding likely resolved. Verify manually before closing."),
        STATUS_EVIDENCE_MISSING: (
            "Supporting evidence is missing. Re-run scan and analyze to refresh."
        ),
        STATUS_PARTIALLY_SUPPORTED: (
            "Finding partially supported. Review remaining evidence and scope."
        ),
        STATUS_STALE: ("Structural changes detected. Re-assess finding scope and validity."),
        STATUS_UNCERTAIN: ("Verification inconclusive. Re-run full pipeline for fresh results."),
    }
    return actions.get(status, "Review finding.")


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------


def render_verification_report_markdown(report: VerificationReport) -> str:
    """Render verification report as human-readable Markdown."""
    # Collect statuses that appear in results
    active_statuses = {r.verification_status for r in report.results}

    status_defs = {
        STATUS_STILL_DETECTED: "Current analyzer confirms with supporting evidence.",
        STATUS_LIKELY_REMEDIATED: (
            "No match, evidence gone, locations gone. Review before closing."
        ),
        STATUS_EVIDENCE_MISSING: "Supporting evidence missing. Cannot confirm remediation.",
        STATUS_PARTIALLY_SUPPORTED: "Some evidence remains. Support incomplete. Review required.",
        STATUS_STALE: "Structural mismatch: units, locations, or links no longer align.",
        STATUS_UNCERTAIN: "Insufficient inputs for a defensible verification result.",
    }

    lines: list[str] = [
        "# Verification Report",
        "",
        "> **Note:** Verification checks evidence support. It does not prove risk is gone.",
        "",
        f"**Repository:** {report.repository}",
        f"**Generated:** {report.generated_at}",
        f"**Analyzer mode:** {report.current_analyzer_mode}",
        "",
        "## Summary",
        "",
        "| Metric | Count |",
        "|---|---:|",
        f"| Findings checked | {report.total_findings_checked} |",
        f"| Still detected | {report.still_detected_count} |",
        f"| Likely remediated | {report.likely_remediated_count} |",
        f"| Evidence missing | {report.evidence_missing_count} |",
        f"| Partially supported | {report.partially_supported_count} |",
        f"| Stale | {report.stale_count} |",
        f"| Uncertain | {report.uncertain_count} |",
        "",
    ]

    # Status definitions (only for statuses that appear)
    if active_statuses:
        lines.extend(["## Status Definitions", ""])
        for sv, defn in status_defs.items():
            if sv in active_statuses:
                lines.append(f"- **{sv}:** {defn}")
        lines.append("")

    # Sections by status
    status_sections = [
        ("Still Detected", STATUS_STILL_DETECTED),
        ("Likely Remediated", STATUS_LIKELY_REMEDIATED),
        ("Partially Supported", STATUS_PARTIALLY_SUPPORTED),
        ("Evidence Missing", STATUS_EVIDENCE_MISSING),
        ("Stale", STATUS_STALE),
        ("Uncertain", STATUS_UNCERTAIN),
    ]

    for section_title, status_val in status_sections:
        matching = [r for r in report.results if r.verification_status == status_val]
        if not matching:
            continue
        lines.extend([f"## {section_title}", ""])
        lines.extend(["| Finding | Evidence | Locations Missing |"])
        lines.extend(["|---|---:|---:|"])
        for r in matching:
            ev_total = len(r.evidence_ids_checked)
            ev_present = len(r.evidence_ids_present)
            ev_str = f"{ev_present}/{ev_total}" if ev_total > 0 else "\u2014"
            lines.append(f"| {r.finding_id} | {ev_str} | {len(r.locations_missing)} |")
        lines.append("")

    # Work package review
    if report.work_package_results:
        lines.extend(["## Work Package Review", ""])
        lines.extend(["| Work Package | Status | Linked Findings | Notes |"])
        lines.extend(["|---|---|---|---|"])
        for wp in report.work_package_results:
            wp_name = Path(wp.work_package_path).name
            notes_str = "; ".join(wp.notes) if wp.notes else "\u2014"
            linked = ", ".join(wp.linked_debt_ids) if wp.linked_debt_ids else "\u2014"
            lines.append(f"| {wp_name} | {wp.status} | {linked} | {notes_str} |")
        lines.append("")

    # Recommended actions grouped by status
    lines.extend(["## Recommended Actions", ""])
    for status_val in [
        STATUS_STILL_DETECTED,
        STATUS_LIKELY_REMEDIATED,
        STATUS_PARTIALLY_SUPPORTED,
        STATUS_EVIDENCE_MISSING,
        STATUS_STALE,
        STATUS_UNCERTAIN,
    ]:
        matching = [r for r in report.results if r.verification_status == status_val]
        if not matching:
            continue
        lines.append(f"**{status_val}:**")
        for r in matching:
            lines.append(f"- {r.finding_id}: {r.recommended_action}")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Write helpers
# ---------------------------------------------------------------------------


def write_verification_report(repository_root: Path) -> VerificationReport:
    """Run verification and write JSON + Markdown reports."""
    root = repository_root.resolve()
    ai_debt = root / ".ai-debt"

    report = verify_repository(root)

    # Write JSON
    json_path = ai_debt / "verification-report.json"
    json_path.write_text(report.model_dump_json(indent=2) + "\n", encoding="utf-8")

    # Write Markdown
    md_path = ai_debt / "verification-report.md"
    md_path.write_text(render_verification_report_markdown(report), encoding="utf-8")

    return report
