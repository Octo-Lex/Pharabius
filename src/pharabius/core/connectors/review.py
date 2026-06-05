"""External evidence review and reporting.

Loads external evidence artifacts and combined-evidence manifests,
produces a deterministic summary for the review report.

Design rules:
- External evidence is reviewable but NOT confirmed findings.
- No new connectors, no scanner execution, no vulnerability confirmation.
- Summary is computed from existing artifacts only.
- Malformed artifacts produce warnings, not failures.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# S01 — Summary Model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ExternalEvidenceSummary:
    """Deterministic summary of external evidence state.

    All fields are computed from existing artifacts.
    No external scanner execution or network calls are made.
    """

    # External evidence directory state
    external_files_total: int = 0
    external_files_readable: int = 0
    external_files_malformed: int = 0
    external_items_total: int = 0

    # Combined evidence state
    combined_present: bool = False
    combined_readable: bool = False
    combined_native_count: int = 0
    combined_external_count: int = 0
    combined_total_count: int = 0
    combined_deduplicated: int = 0

    # Manifest state
    manifest_present: bool = False
    manifest_readable: bool = False
    manifest_sources: int = 0
    manifest_imported: int = 0
    manifest_duplicates: int = 0
    manifest_skipped: int = 0

    # Per-connector aggregation
    connector_counts: dict[str, int] = field(default_factory=dict)
    connector_evidence_counts: dict[str, int] = field(default_factory=dict)

    # Top rules and packages from structured metadata
    top_rules: list[tuple[str, int]] = field(default_factory=list)
    top_packages: list[tuple[str, int]] = field(default_factory=list)

    # Confidence distribution
    confidence_distribution: dict[str, int] = field(default_factory=dict)

    # Severity distribution (from depsec metadata, not mapped to confidence)
    severity_distribution: dict[str, int] = field(default_factory=list)  # type: ignore[assignment]

    # Warnings from malformed artifacts
    warnings: list[str] = field(default_factory=list)

    @property
    def has_external_evidence(self) -> bool:
        """Whether any external evidence files exist."""
        return self.external_files_total > 0

    @property
    def has_combined_evidence(self) -> bool:
        """Whether combined evidence has been generated."""
        return self.combined_present and self.combined_readable


# ---------------------------------------------------------------------------
# S02 — Artifact Loaders
# ---------------------------------------------------------------------------


def _load_json_safe(path: Path) -> dict[str, Any] | None:
    """Load JSON file, returning None on any error."""
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except (json.JSONDecodeError, UnicodeDecodeError, OSError):
        return None


def _load_external_stores(ext_dir: Path) -> tuple[list[dict[str, Any]], list[str]]:
    """Load all external evidence stores from the directory.

    Returns (stores, warnings). Each store is the raw JSON dict.
    Malformed files produce warnings, not errors.
    """
    stores: list[dict[str, Any]] = []
    warnings: list[str] = []

    if not ext_dir.exists():
        return stores, warnings

    for path in sorted(ext_dir.glob("*.json")):
        data = _load_json_safe(path)
        if data is None:
            warnings.append(f"Malformed external evidence: {path.name}")
            continue
        stores.append(data)

    return stores, warnings


def _extract_connector_name(item: dict[str, Any]) -> str:
    """Extract connector name from evidence item metadata."""
    metadata = item.get("metadata", {})
    if isinstance(metadata, dict):
        prov = metadata.get("connector_provenance", {})
        if isinstance(prov, dict):
            return prov.get("connector_name", "unknown")
    return "unknown"


def _extract_rule_id(item: dict[str, Any]) -> str | None:
    """Extract rule ID from evidence item metadata."""
    metadata = item.get("metadata", {})
    if isinstance(metadata, dict):
        prov = metadata.get("connector_provenance", {})
        if isinstance(prov, dict):
            rule = prov.get("source_rule_id", "")
            return rule if rule else None
    return None


def _extract_package_name(item: dict[str, Any]) -> str | None:
    """Extract package name from evidence item metadata coordinates."""
    metadata = item.get("metadata", {})
    if isinstance(metadata, dict):
        # depsec coordinates
        coords = metadata.get("depsec_coordinates", {})
        if isinstance(coords, dict) and coords.get("pkg_name"):
            return coords["pkg_name"]
        # sbom coordinates
        coords = metadata.get("sbom_coordinates", {})
        if isinstance(coords, dict) and coords.get("pkg_name"):
            return coords["pkg_name"]
    return None


def _extract_severity(item: dict[str, Any]) -> str | None:
    """Extract severity from evidence item metadata (not mapped to confidence)."""
    metadata = item.get("metadata", {})
    if isinstance(metadata, dict):
        # depsec coordinates carry severity
        coords = metadata.get("depsec_coordinates", {})
        if isinstance(coords, dict) and coords.get("severity"):
            return coords["severity"]
    return None


def _extract_confidence(item: dict[str, Any]) -> str:
    """Extract confidence from evidence item."""
    return item.get("confidence", "unknown")


# ---------------------------------------------------------------------------
# S03 — Build Summary
# ---------------------------------------------------------------------------


def build_external_evidence_summary(repository_root: Path) -> ExternalEvidenceSummary:
    """Build a deterministic summary of external evidence state.

    Reads from existing artifacts only. Does not execute scanners,
    create findings, or modify any files.

    Args:
        repository_root: Path to the repository root.

    Returns:
        ExternalEvidenceSummary with all computed fields.
    """
    root = repository_root.resolve()
    ai_debt = root / ".ai-debt"
    ext_dir = ai_debt / "external-evidence"

    warnings: list[str] = []

    # --- External evidence files ---
    ext_files = sorted(ext_dir.glob("*.json")) if ext_dir.exists() else []
    ext_stores_raw, load_warnings = _load_external_stores(ext_dir)
    warnings.extend(load_warnings)

    external_items_total = 0
    connector_counter: Counter[str] = Counter()
    connector_evidence_counter: Counter[str] = Counter()
    rule_counter: Counter[str] = Counter()
    package_counter: Counter[str] = Counter()
    confidence_counter: Counter[str] = Counter()
    severity_counter: Counter[str] = Counter()

    for store_data in ext_stores_raw:
        items = store_data.get("evidence", [])
        if not isinstance(items, list):
            continue
        external_items_total += len(items)

        for item in items:
            if not isinstance(item, dict):
                continue

            connector = _extract_connector_name(item)
            connector_counter[connector] += 1
            connector_evidence_counter[connector] += 1

            rule = _extract_rule_id(item)
            if rule:
                rule_counter[rule] += 1

            pkg = _extract_package_name(item)
            if pkg:
                package_counter[pkg] += 1

            conf = _extract_confidence(item)
            confidence_counter[conf] += 1

            sev = _extract_severity(item)
            if sev:
                severity_counter[sev] += 1

    # --- Combined evidence ---
    combined_path = ai_debt / "combined-evidence.json"
    combined_present = combined_path.exists()
    combined_data = _load_json_safe(combined_path)
    combined_readable = combined_data is not None
    combined_native_count = 0
    combined_external_count = 0
    combined_total_count = 0
    combined_deduplicated = 0

    if combined_data:
        combined_items = combined_data.get("evidence", [])
        if isinstance(combined_items, list):
            combined_total_count = len(combined_items)
            for item in combined_items:
                if isinstance(item, dict):
                    source = item.get("source", "")
                    if source == "external_connector":
                        combined_external_count += 1
                    else:
                        combined_native_count += 1

    # --- Manifest ---
    manifest_path = ai_debt / "combined-evidence-manifest.json"
    manifest_present = manifest_path.exists()
    manifest_data = _load_json_safe(manifest_path)
    manifest_readable = manifest_data is not None
    manifest_sources = 0
    manifest_imported = 0
    manifest_duplicates = 0
    manifest_skipped = 0

    if manifest_data:
        ext_sources = manifest_data.get("external_sources", [])
        if isinstance(ext_sources, list):
            manifest_sources = len(ext_sources)
            for src in ext_sources:
                if isinstance(src, dict):
                    manifest_imported += src.get("imported_count", 0)
                    manifest_duplicates += src.get("duplicate_count", 0)
                    manifest_skipped += src.get("skipped_count", 0)
        manifest_deduplicated = manifest_data.get("deduplicated", 0)
        if isinstance(manifest_deduplicated, int):
            combined_deduplicated = manifest_deduplicated

    # --- Top rules and packages (from structured metadata only) ---
    top_rules = rule_counter.most_common(20)
    top_packages = package_counter.most_common(20)

    # --- Sort connector counts deterministically ---
    sorted_connectors = dict(sorted(connector_counter.items()))
    sorted_connector_evidence = dict(sorted(connector_evidence_counter.items()))

    # --- Sort distributions deterministically ---
    sorted_confidence = dict(sorted(confidence_counter.items()))
    sorted_severity = dict(sorted(severity_counter.items()))

    return ExternalEvidenceSummary(
        external_files_total=len(ext_files),
        external_files_readable=len(ext_stores_raw),
        external_files_malformed=len(ext_files) - len(ext_stores_raw),
        external_items_total=external_items_total,
        combined_present=combined_present,
        combined_readable=combined_readable,
        combined_native_count=combined_native_count,
        combined_external_count=combined_external_count,
        combined_total_count=combined_total_count,
        combined_deduplicated=combined_deduplicated,
        manifest_present=manifest_present,
        manifest_readable=manifest_readable,
        manifest_sources=manifest_sources,
        manifest_imported=manifest_imported,
        manifest_duplicates=manifest_duplicates,
        manifest_skipped=manifest_skipped,
        connector_counts=sorted_connectors,
        connector_evidence_counts=sorted_connector_evidence,
        top_rules=top_rules,
        top_packages=top_packages,
        confidence_distribution=sorted_confidence,
        severity_distribution=sorted_severity,
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# S03 — Markdown Report Renderer
# ---------------------------------------------------------------------------


def render_external_evidence_report(summary: ExternalEvidenceSummary) -> str:
    """Render external evidence review as Markdown.

    The report is always generated — even with no external evidence — so
    operators can confirm the system checked and found nothing.

    The report explicitly states external evidence is NOT confirmed findings.
    """
    lines: list[str] = [
        "# External Evidence Review",
        "",
    ]

    # --- Scope notice ---
    lines.extend(
        [
            "## Scope",
            "",
            "This report reviews external evidence imported via connectors.",
            "External evidence is observational. It is **not** confirmed findings.",
            "No vulnerability confirmation, scanner execution, or finding creation",
            "is performed by this report.",
            "",
        ]
    )

    # --- External evidence files ---
    lines.extend(
        [
            "## External Evidence Files",
            "",
        ]
    )

    if not summary.has_external_evidence:
        lines.extend(
            [
                "No external evidence files found.",
                "",
                "To import external evidence, use:",
                "",
                "```",
                "ai-debt import-evidence --input <file> --format sarif",
                "ai-debt import-evidence --input <file> --format semgrep",
                "ai-debt import-evidence --input <file> --format trivy",
                "ai-debt import-evidence --input <file> --format grype",
                "ai-debt import-evidence --input <file> --format syft",
                "```",
                "",
            ]
        )
    else:
        lines.extend(
            [
                f"- Files found: **{summary.external_files_total}**",
                f"- Files readable: {summary.external_files_readable}",
                f"- Files malformed: {summary.external_files_malformed}",
                f"- Total evidence items: {summary.external_items_total}",
                "",
            ]
        )

        # Per-connector breakdown
        if summary.connector_counts:
            lines.extend(
                [
                    "### Evidence by Connector",
                    "",
                    "| Connector | Items |",
                    "|---|---:|",
                ]
            )
            for name, count in summary.connector_counts.items():
                lines.append(f"| {name} | {count} |")
            lines.append("")

    # --- Combined evidence ---
    lines.extend(
        [
            "## Combined Evidence",
            "",
        ]
    )

    if not summary.combined_present:
        lines.extend(
            [
                "No combined evidence store found.",
                "",
                "To combine native and external evidence, use:",
                "",
                "```",
                "ai-debt combine-evidence",
                "```",
                "",
            ]
        )
    else:
        lines.extend(
            [
                "- Combined store: **present**",
                f"- Total items: {summary.combined_total_count}",
                f"- Native items: {summary.combined_native_count}",
                f"- External items: {summary.combined_external_count}",
                f"- Deduplicated: {summary.combined_deduplicated}",
                "",
            ]
        )

    # --- Manifest details ---
    if summary.manifest_present and summary.manifest_readable:
        lines.extend(
            [
                "## Combination Manifest",
                "",
                f"- External sources: {summary.manifest_sources}",
                f"- Imported: {summary.manifest_imported}",
                f"- Duplicates skipped: {summary.manifest_duplicates}",
                f"- Skipped (unreadable): {summary.manifest_skipped}",
                "",
            ]
        )

    # --- Top rules ---
    if summary.top_rules:
        lines.extend(
            [
                "## Top Rules",
                "",
                "| Rule | Count |",
                "|---|---:|",
            ]
        )
        for rule, count in summary.top_rules[:20]:
            lines.append(f"| `{rule}` | {count} |")
        lines.append("")

    # --- Top packages ---
    if summary.top_packages:
        lines.extend(
            [
                "## Top Packages",
                "",
                "| Package | Count |",
                "|---|---:|",
            ]
        )
        for pkg, count in summary.top_packages[:20]:
            lines.append(f"| `{pkg}` | {count} |")
        lines.append("")

    # --- Confidence distribution ---
    if summary.confidence_distribution:
        lines.extend(
            [
                "## Confidence Distribution",
                "",
                "| Confidence | Count |",
                "|---|---:|",
            ]
        )
        for conf, count in summary.confidence_distribution.items():
            lines.append(f"| {conf} | {count} |")
        lines.append("")

    # --- Severity distribution ---
    if summary.severity_distribution:
        lines.extend(
            [
                "## Severity Distribution",
                "",
                "> Severity is stored as observational metadata. It is not mapped to",
                "> Pharabius confidence and does not create findings.",
                "",
                "| Severity | Count |",
                "|---|---:|",
            ]
        )
        for sev, count in summary.severity_distribution.items():
            lines.append(f"| {sev} | {count} |")
        lines.append("")

    # --- Warnings ---
    if summary.warnings:
        lines.extend(
            [
                "## Warnings",
                "",
            ]
        )
        for w in summary.warnings:
            lines.append(f"- {w}")
        lines.append("")

    # --- Interpretation ---
    lines.extend(
        [
            "## Interpretation",
            "",
        ]
    )

    if not summary.has_external_evidence:
        lines.append(
            "No external evidence was found. This report confirms the system "
            "checked for external evidence and found none."
        )
    elif summary.external_files_malformed > 0:
        lines.append(
            "Some external evidence files could not be parsed. Review the "
            "warnings above and re-import the affected files."
        )
    else:
        lines.append(
            "External evidence was successfully loaded. This evidence is "
            "reviewable but is **not** confirmed as findings. To incorporate "
            "it into analysis, use `ai-debt combine-evidence` followed by "
            "`ai-debt analyze --evidence`."
        )

    lines.append("")
    return "\n".join(lines)
