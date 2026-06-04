"""Bundle parser — extracts normalized records from .ai-debt artifacts."""

from __future__ import annotations

import json
import re
from pathlib import Path

from pharabius.schemas.claims import OperationalClaim
from pharabius.schemas.finding import DebtRegister
from pharabius.schemas.quality_gate import QualityGateResult
from pharabius.schemas.repository import RepositoryProfile
from pharabius.schemas.run_metadata import RunMetadata


class ParsedBundle:
    """Normalized records extracted from a bundle."""

    def __init__(self) -> None:
        self.profile: RepositoryProfile | None = None
        self.debt_register: DebtRegister | None = None
        self.runs: list[RunMetadata] = []
        self.quality_gates: list[QualityGateResult] = []
        self.claims: list[OperationalClaim] = []
        self.gaps: list[dict[str, object]] = []
        self.evidence_items: list[dict[str, object]] = []
        self.work_packages: list[dict[str, object]] = []
        self.parse_errors: list[str] = []
        self.evidence_warnings: list[dict[str, object]] = []
        self.work_package_warnings: list[dict[str, object]] = []


def parse_bundle(ai_debt_dir: Path) -> ParsedBundle:
    """Parse all known artifacts from an extracted .ai-debt directory."""
    result = ParsedBundle()

    # Profile
    result.profile = _parse_json_model(
        ai_debt_dir / "project-profile.json",
        RepositoryProfile,
        "project-profile.json",
        result.parse_errors,
    )

    # Debt register
    result.debt_register = _parse_json_model(
        ai_debt_dir / "debt-register.json",
        DebtRegister,
        "debt-register.json",
        result.parse_errors,
    )

    # Runs
    runs_dir = ai_debt_dir / "runs"
    if runs_dir.is_dir():
        for run_file in sorted(runs_dir.glob("RUN-*.json")):
            run_meta = _parse_json_model(run_file, RunMetadata, run_file.name, result.parse_errors)
            if run_meta is not None:
                result.runs.append(run_meta)

    # Claims
    claims_path = ai_debt_dir / "claims" / "operational-claims.json"
    if claims_path.exists():
        try:
            data = json.loads(claims_path.read_text(encoding="utf-8"))
            for claim_data in data.get("claims", []):
                try:
                    result.claims.append(OperationalClaim(**claim_data))
                except Exception as e:
                    result.parse_errors.append(f"claims/{claims_path.name}: {e}")
        except Exception as e:
            result.parse_errors.append(f"claims/operational-claims.json: {e}")

    # Gaps (from claims/gaps.md — parsed as structured text)
    gaps_path = ai_debt_dir / "claims" / "gaps.md"
    if gaps_path.exists():
        result.gaps = _parse_gaps_md(gaps_path)

    # Evidence store
    evidence_path = ai_debt_dir / "evidence.json"
    if evidence_path.exists():
        _parse_evidence(evidence_path, result)

    # Work packages
    wp_dir = ai_debt_dir / "work-packages"
    if wp_dir.is_dir():
        _parse_work_packages(wp_dir, result)

    return result


def _parse_json_model(
    path: Path,
    model_class: type,
    label: str,
    errors: list[str],
) -> object | None:
    """Parse a JSON file into a Pydantic model."""
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return model_class(**data)
    except Exception as e:
        errors.append(f"{label}: {e}")
        return None


def _parse_gaps_md(path: Path) -> list[dict[str, object]]:
    """Parse gaps.md into structured gap records."""
    gaps: list[dict[str, object]] = []
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return gaps

    # Simple heuristic: look for ### GAP-### headings
    lines = text.split("\n")
    current_gap: dict[str, object] | None = None
    for line in lines:
        if line.startswith("### GAP-") or line.startswith("## GAP-"):
            if current_gap is not None:
                gaps.append(current_gap)
            gap_id = line.lstrip("# ").strip().split()[0] if line.strip() else "GAP-UNKNOWN"
            current_gap = {"gap_id": gap_id, "description": "", "severity": "Medium"}
        elif current_gap is not None and line.strip():
            desc = str(current_gap.get("description", ""))
            if desc:
                desc += " "
            current_gap["description"] = desc + line.strip()

    if current_gap is not None:
        gaps.append(current_gap)

    return gaps


def _parse_evidence(path: Path, result: ParsedBundle) -> None:
    """Parse evidence.json into structured evidence items.

    Malformed records are skipped with a warning, not fatal.
    """
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        result.parse_errors.append(f"evidence.json: {e}")
        return

    evidence_list = data.get("evidence", [])
    if not isinstance(evidence_list, list):
        result.parse_errors.append("evidence.json: 'evidence' is not a list")
        return

    for idx, item in enumerate(evidence_list):
        if not isinstance(item, dict):
            result.evidence_warnings.append(
                {
                    "code": "malformed_evidence_record_skipped",
                    "message": "Skipped non-object evidence record.",
                    "path": "evidence.json",
                    "index": idx,
                }
            )
            continue

        evidence_id = item.get("evidence_id") or item.get("id") or ""
        if not evidence_id or not isinstance(evidence_id, str):
            result.evidence_warnings.append(
                {
                    "code": "malformed_evidence_record_skipped",
                    "message": "Skipped evidence record with missing/invalid ID.",
                    "path": "evidence.json",
                    "index": idx,
                }
            )
            continue

        location = item.get("location") or {}
        if not isinstance(location, dict):
            location = {}

        result.evidence_items.append(
            {
                "evidence_id": evidence_id,
                "source": str(item.get("source", "unknown")),
                "type": str(item.get("type", "unknown")),
                "category": str(item.get("category", "unknown")),
                "file_path": str(location.get("file", "")),
                "line_start": location.get("line_start") or location.get("line"),
                "line_end": location.get("line_end"),
                "subject": str(item.get("subject", "")),
                "object": str(item.get("object", "")),
                "summary": str(item.get("summary", "")),
                "raw_observation": str(item.get("raw_observation", "")),
                "confidence": str(item.get("confidence", "Medium")),
                "collected_at": str(item.get("collected_at", "")),
                "metadata": item.get("metadata")
                if isinstance(item.get("metadata"), dict)
                else None,
            }
        )


def _parse_work_packages(wp_dir: Path, result: ParsedBundle) -> None:
    """Parse work-packages/*.md into structured records.

    Malformed packages are skipped with a warning, not fatal.
    """
    seen_ids: set[str] = set()

    for wp_file in sorted(wp_dir.glob("WP-*.md")):
        try:
            content = wp_file.read_text(encoding="utf-8")
        except Exception as e:
            result.work_package_warnings.append(
                {
                    "code": "work_package_read_error",
                    "message": f"Could not read {wp_file.name}: {e}",
                    "path": f"work-packages/{wp_file.name}",
                }
            )
            continue

        # Extract package ID from filename: WP-001-slug.md → WP-001
        stem = wp_file.stem
        wp_id_match = re.match(r"^(WP-\d+)", stem)
        wp_id = wp_id_match.group(1) if wp_id_match else ""

        if not wp_id:
            result.work_package_warnings.append(
                {
                    "code": "malformed_work_package_skipped",
                    "message": "Skipped work package with no valid ID in filename.",
                    "path": f"work-packages/{wp_file.name}",
                }
            )
            continue

        if wp_id in seen_ids:
            result.work_package_warnings.append(
                {
                    "code": "duplicate_work_package_id",
                    "message": f"Duplicate work package ID {wp_id} skipped.",
                    "path": f"work-packages/{wp_file.name}",
                    "package_id": wp_id,
                }
            )
            continue

        seen_ids.add(wp_id)

        # Title from first heading
        title_match = re.search(r"^# Work Package: (.+)$", content, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else stem

        # Parse sections
        linked_raw = _extract_md_section(content, "Linked Debt Items")
        linked = _extract_md_list_items(linked_raw)

        objective = _extract_md_section(content, "Objective") or ""
        current_risk = _extract_md_section(content, "Current Risk") or ""

        approach_raw = _extract_md_section(content, "Recommended Engineering Approach")
        approach = _extract_md_list_items(approach_raw)

        areas_raw = _extract_md_section(content, "Expected Affected Areas")
        areas = _extract_md_list_items(areas_raw)

        preconditions_raw = _extract_md_section(content, "Preconditions")
        preconditions = _extract_md_list_items(preconditions_raw)

        verification_raw = _extract_md_section(content, "Verification Recommendations")
        verification = _extract_md_list_items(verification_raw)

        risks_raw = _extract_md_section(content, "Risks and Cautions")
        risks = _extract_md_list_items(risks_raw)

        dod_raw = _extract_md_section(content, "Definition of Done")
        dod = _extract_md_list_items(dod_raw)

        evidence_raw = _extract_md_section(content, "Evidence")
        evidence = _extract_md_list_items(evidence_raw)

        effort_raw = _extract_md_section(content, "Estimated Effort")
        effort = effort_raw.strip() if effort_raw else ""

        status_raw = _extract_md_section(content, "Status")
        status = status_raw.strip() if status_raw else ""

        result.work_packages.append(
            {
                "package_id": wp_id,
                "title": title,
                "linked_debt_items": linked,
                "objective": objective,
                "current_risk": current_risk,
                "recommended_engineering_approach": approach,
                "expected_affected_areas": areas,
                "preconditions": preconditions,
                "verification_recommendations": verification,
                "risks_and_cautions": risks,
                "definition_of_done": dod,
                "estimated_effort": effort,
                "declared_evidence_ids": evidence,
                "status": status,
            }
        )


def _extract_md_section(content: str, heading: str) -> str:
    """Extract text between a ## heading and the next ## heading."""
    pattern = rf"^## {re.escape(heading)}\s*\n(.*?)(?=^## |\Z)"
    match = re.search(pattern, content, re.MULTILINE | re.DOTALL)
    return match.group(1).strip() if match else ""


def _extract_md_list_items(section_text: str) -> list[str]:
    """Extract bullet-point or numbered list items from section text."""
    items: list[str] = []
    for line in section_text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("- "):
            items.append(stripped[2:].strip().strip("`"))
        elif re.match(r"^\d+\.\s", stripped):
            items.append(re.sub(r"^\d+\.\s+", "", stripped))
    return items
