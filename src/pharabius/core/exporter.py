"""Export findings to SARIF, CSV, and JSONL formats.

Reads existing .ai-debt/ artifacts and converts them to standard interchange
formats for CI integration, spreadsheet triage, and downstream tooling.

This module is purely additive — it does not modify source artifacts.
"""

from __future__ import annotations

import csv
import json
import logging
from dataclasses import dataclass, field
from io import StringIO
from pathlib import Path

from pharabius.schemas.finding import DebtRegister

logger = logging.getLogger(__name__)

# SARIF severity mapping
_SEVERITY_TO_SARIF_LEVEL: dict[str, str] = {
    "Critical": "error",
    "High": "error",
    "Medium": "warning",
    "Low": "note",
}

# Category display names for SARIF rules
CATEGORY_NAMES: dict[str, str] = {
    "TD-DEP": "Dependency Debt",
    "TD-SEC": "Security Risk",
    "TD-TEST": "Test Gap",
    "TD-BUILD": "Build/CI Gap",
    "TD-DOC": "Documentation Debt",
    "TD-ARCH": "Architecture Debt",
    "TD-CONFIG": "Configuration Debt",
    "TD-COMP": "Complexity Debt",
}

# CSV column headers (in order)
CSV_COLUMNS = [
    "debt_id",
    "title",
    "category",
    "severity",
    "score",
    "confidence",
    "status",
    "verification_status",
    "evidence_ids",
    "analysis_unit_ids",
    "locations",
    "recommended_action",
    "work_packages",
]

# JSONL field names
JSONL_FIELDS = [
    "debt_id",
    "title",
    "category",
    "severity",
    "risk_score",
    "confidence",
    "status",
    "verification_status",
    "evidence_ids",
    "analysis_unit_ids",
    "locations",
    "recommended_action",
    "work_packages",
]


@dataclass
class ExportResult:
    """Result of an export operation."""

    files_written: list[Path] = field(default_factory=list)
    finding_count: int = 0
    warnings: list[str] = field(default_factory=list)


def _load_json_safe(path: Path) -> dict[str, object] | None:
    """Load a JSON file, returning None on missing or malformed."""
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))  # type: ignore[no-any-return]
    except (json.JSONDecodeError, OSError):
        return None


def _get_tool_version() -> str:
    """Get Pharabius package version."""
    try:
        from importlib.metadata import version

        return version("pharabius")
    except Exception:
        return "unknown"


def _build_verification_lookup(
    repo_root: Path,
) -> dict[str, str]:
    """Build finding_id -> verification_status lookup from verification report."""
    path = repo_root / ".ai-debt" / "verification-report.json"
    data = _load_json_safe(path)
    if data is None:
        return {}

    results = data.get("results")
    if not isinstance(results, list):
        return {}

    lookup: dict[str, str] = {}
    for item in results:
        if isinstance(item, dict):
            fid = item.get("finding_id")
            status = item.get("verification_status")
            if isinstance(fid, str) and isinstance(status, str):
                lookup[fid] = status
    return lookup


def _build_work_package_lookup(
    repo_root: Path,
    register: DebtRegister,
) -> dict[str, list[str]]:
    """Build finding_id -> [wp_filenames] lookup."""
    # First try verification report (most reliable)
    path = repo_root / ".ai-debt" / "verification-report.json"
    data = _load_json_safe(path)
    if data is not None:
        results = data.get("results")
        if isinstance(results, list):
            lookup: dict[str, list[str]] = {}
            for item in results:
                if isinstance(item, dict):
                    fid = item.get("finding_id")
                    wps = item.get("work_package_paths")
                    if isinstance(fid, str) and isinstance(wps, list):
                        lookup[fid] = [str(w) for w in wps if isinstance(w, (str, Path))]
            if lookup:
                return lookup

    # Fallback: scan work-packages directory for filenames containing debt IDs
    wp_dir = repo_root / ".ai-debt" / "work-packages"
    if not wp_dir.is_dir():
        return {}

    wp_files = list(wp_dir.glob("*.md"))
    if not wp_files:
        return {}

    lookup = {}
    for finding in register.findings:
        linked: list[str] = []
        for wp_file in wp_files:
            # Read file content and look for debt ID references
            try:
                content = wp_file.read_text(encoding="utf-8", errors="ignore")
                if finding.id in content:
                    linked.append(wp_file.name)
            except OSError:
                pass
        if linked:
            lookup[finding.id] = linked

    return lookup


def _severity_to_sarif_level(severity: str) -> str:
    """Map Pharabius severity to SARIF level."""
    return _SEVERITY_TO_SARIF_LEVEL.get(severity, "note")


def _build_sarif(
    register: DebtRegister,
    verification_lookup: dict[str, str],
    wp_lookup: dict[str, list[str]],
) -> dict[str, object]:
    # Build rules from unique categories
    categories = sorted({f.category for f in register.findings})
    rules = []
    category_to_index: dict[str, int] = {}
    for i, cat in enumerate(categories):
        rules.append(
            {
                "id": cat,
                "name": CATEGORY_NAMES.get(cat, cat),
                "shortDescription": {"text": CATEGORY_NAMES.get(cat, cat)},
                "properties": {"category": cat},
            }
        )
        category_to_index[cat] = i

    # Build results
    results = []
    for finding in register.findings:
        result: dict[str, object] = {
            "ruleId": finding.category,
            "ruleIndex": category_to_index.get(finding.category, 0),
            "level": _severity_to_sarif_level(finding.severity),
            "message": {"text": finding.title},
        }

        # Locations
        if finding.locations:
            result["locations"] = [
                {
                    "physicalLocation": {
                        "artifactLocation": {"uri": loc.replace("\\", "/")},
                        "region": {"startLine": 1},
                    }
                }
                for loc in finding.locations
            ]
        else:
            result["locations"] = []

        # Properties
        result["properties"] = {
            "debtId": finding.id,
            "category": finding.category,
            "severity": finding.severity,
            "score": finding.risk_score,
            "confidence": finding.confidence,
            "status": finding.status,
            "verificationStatus": verification_lookup.get(finding.id, ""),
            "evidenceIds": finding.evidence_ids,
            "analysisUnitIds": finding.analysis_unit_ids,
            "workPackages": wp_lookup.get(finding.id, []),
        }

        # GitHub Code Scanning fingerprint for dedup
        result["fingerprints"] = {"debtId": finding.id}

        results.append(result)

    version = _get_tool_version()
    return {
        "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/main/sarif-2.1/schema/sarif-schema-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "Pharabius",
                        "semanticVersion": version,
                        "version": version,
                        "rules": rules,
                    }
                },
                "results": results,
            }
        ],
    }


def _write_sarif(
    register: DebtRegister,
    verification_lookup: dict[str, str],
    wp_lookup: dict[str, list[str]],
    output_path: Path,
) -> None:
    """Write SARIF v2.1.0 file."""
    sarif = _build_sarif(register, verification_lookup, wp_lookup)
    output_path.write_text(
        json.dumps(sarif, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _write_csv(
    register: DebtRegister,
    verification_lookup: dict[str, str],
    wp_lookup: dict[str, list[str]],
    output_path: Path,
) -> None:
    """Write CSV file with UTF-8 BOM."""
    buf = StringIO()
    writer = csv.writer(buf, quoting=csv.QUOTE_MINIMAL)

    # Header
    writer.writerow(CSV_COLUMNS)

    # Rows
    for finding in register.findings:
        writer.writerow(
            [
                finding.id,
                finding.title,
                finding.category,
                finding.severity,
                finding.risk_score,
                finding.confidence,
                finding.status,
                verification_lookup.get(finding.id, ""),
                ";".join(finding.evidence_ids),
                ";".join(finding.analysis_unit_ids),
                ";".join(finding.locations),
                finding.recommended_action,
                ";".join(wp_lookup.get(finding.id, [])),
            ]
        )

    output_path.write_bytes(b"\xef\xbb\xbf" + buf.getvalue().encode("utf-8"))


def _write_jsonl(
    register: DebtRegister,
    verification_lookup: dict[str, str],
    wp_lookup: dict[str, list[str]],
    output_path: Path,
) -> None:
    """Write JSONL file."""
    lines: list[str] = []
    for finding in register.findings:
        record = {
            "debt_id": finding.id,
            "title": finding.title,
            "category": finding.category,
            "severity": finding.severity,
            "risk_score": finding.risk_score,
            "confidence": finding.confidence,
            "status": finding.status,
            "verification_status": verification_lookup.get(finding.id, ""),
            "evidence_ids": finding.evidence_ids,
            "analysis_unit_ids": finding.analysis_unit_ids,
            "locations": finding.locations,
            "recommended_action": finding.recommended_action,
            "work_packages": wp_lookup.get(finding.id, []),
        }
        lines.append(json.dumps(record, ensure_ascii=False))

    output_path.write_text(
        "\n".join(lines) + ("\n" if lines else ""),
        encoding="utf-8",
    )


def export_findings(
    repository_root: Path,
    *,
    formats: list[str] | None = None,
    output_dir: Path | None = None,
) -> ExportResult:
    """Export findings to standard interchange formats.

    Args:
        repository_root: Repository root containing .ai-debt/.
        formats: List of formats to export ("sarif", "csv", "jsonl").
        output_dir: Override output directory.

    Returns:
        ExportResult with files written, count, and warnings.

    Raises:
        FileNotFoundError: If debt-register.json is missing.
    """
    if formats is None:
        formats = ["sarif", "csv", "jsonl"]

    root = repository_root.resolve()
    ai_debt = root / ".ai-debt"
    register_path = ai_debt / "debt-register.json"

    if not register_path.exists():
        raise FileNotFoundError(
            "debt-register.json not found. Run 'ai-debt analyze --no-ai' first."
        )

    # Load debt register
    register = DebtRegister.model_validate_json(register_path.read_text(encoding="utf-8"))

    # Build enrichment lookups
    verification_lookup = _build_verification_lookup(root)
    wp_lookup = _build_work_package_lookup(root, register)

    result = ExportResult(finding_count=len(register.findings))

    # Resolve output directory
    out = Path(output_dir).resolve() if output_dir is not None else ai_debt / "exports"

    out.mkdir(parents=True, exist_ok=True)

    # Write formats
    for fmt in formats:
        if fmt == "sarif":
            path = out / "findings.sarif"
            _write_sarif(register, verification_lookup, wp_lookup, path)
            result.files_written.append(path)
        elif fmt == "csv":
            path = out / "findings.csv"
            _write_csv(register, verification_lookup, wp_lookup, path)
            result.files_written.append(path)
        elif fmt == "jsonl":
            path = out / "findings.jsonl"
            _write_jsonl(register, verification_lookup, wp_lookup, path)
            result.files_written.append(path)

    return result
