"""Read-only status reader for .ai-debt workspace."""

from __future__ import annotations

import json
from pathlib import Path


def _load_json_safe(path: Path) -> dict[str, object] | None:
    """Load JSON file, returning None on any error."""
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, OSError):
        return None
    return data if isinstance(data, dict) else None


def _count_json_list(path: Path, key: str) -> tuple[str, int | None]:
    """Count items in a JSON list field. Returns (status, count)."""
    data = _load_json_safe(path)
    if data is None:
        if not path.exists():
            return ("absent", None)
        return ("unreadable", None)
    items = data.get(key)
    if not isinstance(items, list):
        return ("absent", None)
    return ("present", len(items))


def read_status(repository_root: Path) -> str:
    """Read workspace status and return formatted text. Does NOT modify files."""
    root = repository_root.resolve()
    ai_debt = root / ".ai-debt"

    warnings: list[str] = []
    lines: list[str] = []

    lines.append(f"Repository:   {root}")

    # Profile
    profile_path = ai_debt / "project-profile.json"
    profile = _load_json_safe(profile_path)
    if profile is None:
        if profile_path.exists():
            lines.append("Profile:      unreadable")
            warnings.append("project-profile.json is corrupted")
        else:
            lines.append("Profile:      absent")
    else:
        langs = ", ".join(profile.get("detected_languages", []))  # type: ignore[arg-type]
        lines.append(f"Profile:      present{f' ({langs})' if langs else ''}")

    # Evidence
    ev_status, ev_count = _count_json_list(ai_debt / "evidence.json", "evidence")
    if ev_status == "unreadable":
        lines.append("Evidence:     unreadable")
        warnings.append("evidence.json is corrupted")
    elif ev_status == "absent":
        lines.append("Evidence:     absent")
    else:
        lines.append(f"Evidence:     {ev_count} items")

    # Analysis units
    units_status, units_count = _count_json_list(ai_debt / "analysis-units.json", "units")
    if units_status == "unreadable":
        lines.append("Analysis units: unreadable")
        warnings.append("analysis-units.json is corrupted")
    elif units_status == "absent":
        lines.append("Analysis units: absent")
    else:
        lines.append(f"Analysis units: {units_count}")

    # Findings
    register_path = ai_debt / "debt-register.json"
    register = _load_json_safe(register_path)
    if register is None:
        if register_path.exists():
            lines.append("Findings:     unreadable")
            warnings.append("debt-register.json is corrupted")
        else:
            lines.append("Findings:     absent")
    else:
        summary = register.get("summary", {})
        if isinstance(summary, dict):
            total = summary.get("total_findings", 0)
            crit = summary.get("critical", 0)
            high = summary.get("high", 0)
            med = summary.get("medium", 0)
            low = summary.get("low", 0)
            lines.append(
                f"Findings:     {total} ({crit} critical, {high} high, {med} medium, {low} low)"
            )
        else:
            findings_list = register.get("findings", [])
            count = len(findings_list) if isinstance(findings_list, list) else "absent"
            lines.append(f"Findings:     {count}")

    # Work packages
    wp_dir = ai_debt / "work-packages"
    if wp_dir.exists():
        wp_count = len(list(wp_dir.glob("WP-*.md")))
        lines.append(f"Work packages: {wp_count}")
    else:
        lines.append("Work packages: absent")

    # Verification
    ver_path = ai_debt / "verification-report.json"
    ver = _load_json_safe(ver_path)
    if ver is None:
        if ver_path.exists():
            lines.append("Verification: unreadable")
            warnings.append("verification-report.json is corrupted")
        else:
            lines.append("Verification: absent")
    else:
        total = ver.get("total_findings_checked", 0)
        still = ver.get("still_detected_count", 0)
        remed = ver.get("likely_remediated_count", 0)
        gen: str = ver.get("generated_at", "")  # type: ignore[assignment]
        gen_short = gen[:10] if gen else "unknown"
        parts = [f"{still} still_detected"]
        if remed:
            parts.append(f"{remed} likely_remediated")
        lines.append(f"Verification: present — {', '.join(parts)} ({gen_short})")

    # Reports
    reports_dir = ai_debt / "reports"
    expected_reports = [
        "architecture-map.md",
        "dependency-health.md",
        "test-health.md",
        "security-exposure.md",
        "business-risk-proxy.md",
        "foundation-audit-report.md",
    ]
    if reports_dir.exists():
        found = sum(1 for r in expected_reports if (reports_dir / r).exists())
        lines.append(f"Reports:      {found}/{len(expected_reports)} present")
    else:
        lines.append("Reports:      absent")

    # Latest run
    runs_dir = ai_debt / "runs"
    if runs_dir.exists():
        runs = sorted(runs_dir.glob("RUN-*.json"))
        if runs:
            lines.append(f"Latest run:   {runs[-1].stem}")
        else:
            lines.append("Latest run:   absent")
    else:
        lines.append("Latest run:   absent")

    # Warnings
    if warnings:
        lines.append("")
        for w in warnings:
            lines.append(f"Warning: {w}")

    # External evidence (v3.4.0)
    ext_dir = ai_debt / "external-evidence"
    if ext_dir.exists():
        ext_files = list(ext_dir.glob("*.json"))
        readable = 0
        malformed = 0
        for ef in ext_files:
            try:
                data = json.loads(ef.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    readable += 1
                else:
                    malformed += 1
            except (json.JSONDecodeError, UnicodeDecodeError, OSError):
                malformed += 1
        if malformed:
            lines.append(f"Ext. evidence: {readable} files ({malformed} malformed)")
        else:
            lines.append(f"Ext. evidence: {readable} files")
    else:
        lines.append("Ext. evidence: absent")

    # Combined evidence (v3.4.0)
    combined_path = ai_debt / "combined-evidence.json"
    if combined_path.exists():
        combined = _load_json_safe(combined_path)
        if combined:
            ev = combined.get("evidence", [])
            if isinstance(ev, list):
                native = sum(
                    1 for e in ev if isinstance(e, dict) and e.get("source") != "external_connector"
                )
                external = sum(
                    1 for e in ev if isinstance(e, dict) and e.get("source") == "external_connector"
                )
                lines.append(
                    f"Combined:     {len(ev)} items ({native} native, {external} external)"
                )
            else:
                lines.append("Combined:     unreadable")
        else:
            lines.append("Combined:     unreadable")
    else:
        lines.append("Combined:     absent")

    # Candidate findings (v3.6.0)
    candidate_path = ai_debt / "candidate-findings.json"
    if candidate_path.exists():
        cand = _load_json_safe(candidate_path)
        if cand:
            total_cand = cand.get("summary", {}).get("total_candidates", 0)
            lines.append(f"Candidates:   {total_cand} (review required)")
        else:
            lines.append("Candidates:   unreadable")
    # No line if absent — candidates are optional

    return "\n".join(lines)
