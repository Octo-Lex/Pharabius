"""Coverage artifact parsers.

Extracted from scanner.py in v3.4.0. Handles detection, parsing, and metric
extraction for Istanbul JSON, Python coverage.json, LCOV, Cobertura XML,
and JaCoCo XML coverage reports.
"""

from __future__ import annotations

from pathlib import Path

from pharabius.core.constants import (
    COMPLETENESS_COMPLETE,
    COMPLETENESS_PARTIAL,
    EVIDENCE_COVERAGE_GAP,
    EVIDENCE_COVERAGE_METRIC,
    EVIDENCE_COVERAGE_REPORT,
    OBSERVATION_STRENGTH_DERIVED,
    OBSERVATION_STRENGTH_DIRECT,
    OBSERVATION_STRENGTH_LIMITATION,
    PARSER_COVERAGE,
    READ_MODE_JSON,
    READ_MODE_TEXT,
)
from pharabius.core.io_helpers import read_json, read_text
from pharabius.schemas.evidence import EvidenceBuilder


def _parse_istanbul_coverage(
    file_path: Path, relative: str, builder: EvidenceBuilder,
) -> None:
    data = read_json(file_path)
    total = data.get("total", {})
    if not total:
        return
    for metric_name in ("lines", "statements", "functions", "branches"):
        metric_data = total.get(metric_name, {})
        pct = metric_data.get("pct", 0)
        if isinstance(pct, (int, float)):
            builder.add(
                type_=EVIDENCE_COVERAGE_METRIC,
                category="test_health",
                summary=f"{metric_name} coverage: {pct}%",
                location_file=relative,
                subject=metric_name,
                raw_observation=f"{metric_name}:{pct}%",
                confidence="High",
                metadata={
                    "metric": metric_name,
                    "percent": float(pct),
                    "format": "istanbul_json",
                    "observation_strength": OBSERVATION_STRENGTH_DIRECT,
                    "completeness": COMPLETENESS_COMPLETE,
                    "parser": PARSER_COVERAGE,
                    "read_mode": READ_MODE_JSON,
                },
            )


def _parse_python_coverage(
    file_path: Path, relative: str, builder: EvidenceBuilder,
) -> None:
    data = read_json(file_path)
    totals = data.get("totals", {})
    if not totals:
        return
    pct = totals.get("percent_covered")
    if pct is not None:
        builder.add(
            type_=EVIDENCE_COVERAGE_METRIC,
            category="test_health",
            summary=f"line coverage: {float(pct):.1f}%",
            location_file=relative,
            subject="lines",
            raw_observation=f"lines:{float(pct):.1f}%",
            confidence="High",
            metadata={
                "metric": "lines",
                "percent": float(pct),
                "format": "python_coverage_json",
                "observation_strength": OBSERVATION_STRENGTH_DIRECT,
                "completeness": COMPLETENESS_COMPLETE,
                "parser": PARSER_COVERAGE,
                "read_mode": READ_MODE_JSON,
            },
        )
    else:
        covered = totals.get("covered_lines", 0)
        total_statements = totals.get("num_statements", 0)
        if total_statements > 0:
            pct = round(covered / total_statements * 100, 1)
            builder.add(
                type_=EVIDENCE_COVERAGE_METRIC,
                category="test_health",
                summary=f"line coverage: {pct}% (derived)",
                location_file=relative,
                subject="lines",
                raw_observation=f"lines:{pct}%",
                confidence="High",
                metadata={
                    "metric": "lines",
                    "percent": float(pct),
                    "format": "python_coverage_json",
                    "derived": True,
                    "observation_strength": OBSERVATION_STRENGTH_DERIVED,
                    "completeness": COMPLETENESS_COMPLETE,
                    "parser": PARSER_COVERAGE,
                    "read_mode": READ_MODE_JSON,
                },
            )


def _parse_lcov_coverage(
    file_path: Path, relative: str, builder: EvidenceBuilder,
) -> None:
    text = read_text(file_path)
    if not text:
        return
    lf = 0
    lh = 0
    fnf = 0
    fnh = 0
    for line in text.split('\n'):
        line = line.strip()
        if line.startswith('LF:'):
            try:
                lf += int(line[3:])
            except ValueError:
                pass
        elif line.startswith('LH:'):
            try:
                lh += int(line[3:])
            except ValueError:
                pass
        elif line.startswith('FNF:'):
            try:
                fnf += int(line[4:])
            except ValueError:
                pass
        elif line.startswith('FNH:'):
            try:
                fnh += int(line[4:])
            except ValueError:
                pass
    if lf > 0:
        line_pct = round(lh / lf * 100, 1)
        builder.add(
            type_=EVIDENCE_COVERAGE_METRIC,
            category="test_health",
            summary=f"line coverage: {line_pct}% (LCOV)",
            location_file=relative,
            subject="lines",
            raw_observation=f"lines:{line_pct}%:LH={lh}/LF={lf}",
            confidence="High",
            metadata={
                "metric": "lines",
                "percent": float(line_pct),
                "format": "lcov",
                "lf": lf,
                "lh": lh,
                "observation_strength": OBSERVATION_STRENGTH_DIRECT,
                "completeness": COMPLETENESS_COMPLETE,
                "parser": PARSER_COVERAGE,
                "read_mode": READ_MODE_TEXT,
            },
        )
    if fnf > 0:
        func_pct = round(fnh / fnf * 100, 1)
        builder.add(
            type_=EVIDENCE_COVERAGE_METRIC,
            category="test_health",
            summary=f"function coverage: {func_pct}% (LCOV)",
            location_file=relative,
            subject="functions",
            raw_observation=f"functions:{func_pct}%:FNH={fnh}/FNF={fnf}",
            confidence="High",
            metadata={
                "metric": "functions",
                "percent": float(func_pct),
                "format": "lcov",
                "fnf": fnf,
                "fnh": fnh,
                "observation_strength": OBSERVATION_STRENGTH_DIRECT,
                "completeness": COMPLETENESS_COMPLETE,
                "parser": PARSER_COVERAGE,
                "read_mode": READ_MODE_TEXT,
            },
        )


def _parse_cobertura_coverage(
    file_path: Path, relative: str, builder: EvidenceBuilder,
) -> None:
    import xml.etree.ElementTree as ET

    text = read_text(file_path)
    if not text:
        return

    root_el = ET.fromstring(text)

    line_rate = root_el.get("line-rate")
    branch_rate = root_el.get("branch-rate")

    if line_rate is not None:
        try:
            pct = round(float(line_rate) * 100, 1)
            builder.add(
                type_=EVIDENCE_COVERAGE_METRIC,
                category="test_health",
                summary=f"line coverage: {pct}% (Cobertura)",
                location_file=relative,
                subject="lines",
                raw_observation=f"lines:{pct}%:line-rate={line_rate}",
                confidence="High",
                metadata={
                    "metric": "lines",
                    "percent": float(pct),
                    "format": "cobertura_xml",
                    "observation_strength": OBSERVATION_STRENGTH_DIRECT,
                    "completeness": COMPLETENESS_COMPLETE,
                    "parser": PARSER_COVERAGE,
                    "read_mode": READ_MODE_TEXT,
                },
            )
        except (ValueError, TypeError):
            pass

    if branch_rate is not None:
        try:
            pct = round(float(branch_rate) * 100, 1)
            builder.add(
                type_=EVIDENCE_COVERAGE_METRIC,
                category="test_health",
                summary=f"branch coverage: {pct}% (Cobertura)",
                location_file=relative,
                subject="branches",
                raw_observation=f"branches:{pct}%:branch-rate={branch_rate}",
                confidence="High",
                metadata={
                    "metric": "branches",
                    "percent": float(pct),
                    "format": "cobertura_xml",
                    "observation_strength": OBSERVATION_STRENGTH_DIRECT,
                    "completeness": COMPLETENESS_COMPLETE,
                    "parser": PARSER_COVERAGE,
                    "read_mode": READ_MODE_TEXT,
                },
            )
        except (ValueError, TypeError):
            pass


def _parse_jacoco_coverage(
    file_path: Path, relative: str, builder: EvidenceBuilder,
) -> None:
    import xml.etree.ElementTree as ET

    text = read_text(file_path)
    if not text:
        return

    root_el = ET.fromstring(text)

    report_counters = list(root_el.findall("counter"))

    if report_counters:
        counters_to_use = report_counters
    else:
        counters_to_use = []
        for package in root_el.findall("package"):
            counters_to_use.extend(package.findall("counter"))

    TYPE_TO_METRIC = {
        "LINE": "lines",
        "BRANCH": "branches",
        "METHOD": "methods",
        "INSTRUCTION": "instructions",
        "COMPLEXITY": "complexity",
    }

    aggregated: dict[str, dict[str, int]] = {}
    for counter in counters_to_use:
        ctype = counter.get("type")
        if ctype is None:
            continue
        missed = int(counter.get("missed", 0))
        covered = int(counter.get("covered", 0))
        if ctype not in aggregated:
            aggregated[ctype] = {"missed": 0, "covered": 0}
        aggregated[ctype]["missed"] += missed
        aggregated[ctype]["covered"] += covered

    for ctype, data in aggregated.items():
        metric = TYPE_TO_METRIC.get(ctype)
        if metric is None:
            continue
        total = data["covered"] + data["missed"]
        if total == 0:
            continue
        pct = round(data["covered"] / total * 100, 1)
        builder.add(
            type_=EVIDENCE_COVERAGE_METRIC,
            category="test_health",
            summary=f"{metric} coverage: {pct}% (JaCoCo)",
            location_file=relative,
            subject=metric,
            raw_observation=f"{metric}:{pct}%:covered={data['covered']}/total={total}",
            confidence="High",
            metadata={
                "metric": metric,
                "percent": float(pct),
                "format": "jacoco_xml",
                "covered": data["covered"],
                "missed": data["missed"],
                "source": "report_level" if report_counters else "package_level",
                "observation_strength": OBSERVATION_STRENGTH_DIRECT,
                "completeness": COMPLETENESS_COMPLETE,
                "parser": PARSER_COVERAGE,
                "read_mode": READ_MODE_TEXT,
            },
        )


def scan_coverage_artifact(
    file_path: Path,
    relative: str,
    format_type: str,
    builder: EvidenceBuilder,
) -> bool:
    """Scan a coverage report file.

    Returns True if the artifact format was recognized and handled.
    Returns False if the format type is unknown.
    """
    _TEXT_FORMATS = ("lcov", "cobertura_xml", "jacoco_xml")

    builder.add(
        type_=EVIDENCE_COVERAGE_REPORT,
        category="test_health",
        summary=f"Coverage report detected: {relative}",
        location_file=relative,
        subject=relative,
        raw_observation=format_type,
        confidence="High",
        metadata={
            "format": format_type,
            "observation_strength": OBSERVATION_STRENGTH_DIRECT,
            "completeness": COMPLETENESS_COMPLETE,
            "parser": PARSER_COVERAGE,
            "read_mode": READ_MODE_TEXT if format_type in _TEXT_FORMATS else READ_MODE_JSON,
        },
    )
    try:
        if format_type == "istanbul_json":
            _parse_istanbul_coverage(file_path, relative, builder)
        elif format_type == "python_coverage_json":
            _parse_python_coverage(file_path, relative, builder)
        elif format_type == "lcov":
            _parse_lcov_coverage(file_path, relative, builder)
        elif format_type == "cobertura_xml":
            _parse_cobertura_coverage(file_path, relative, builder)
        elif format_type == "jacoco_xml":
            _parse_jacoco_coverage(file_path, relative, builder)
        else:
            return False
    except Exception:
        builder.add(
            type_=EVIDENCE_COVERAGE_GAP,
            category="test_health",
            summary=f"Coverage report {relative} could not be fully parsed",
            location_file=relative,
            subject=relative,
            raw_observation=f"parse_failure:{format_type}",
            confidence="Medium",
            metadata={
                "format": format_type,
                "reason": "malformed_report",
                "observation_strength": OBSERVATION_STRENGTH_LIMITATION,
                "completeness": COMPLETENESS_PARTIAL,
                "parser": PARSER_COVERAGE,
                "read_mode": READ_MODE_TEXT if format_type in _TEXT_FORMATS else READ_MODE_JSON,
            },
        )
    return True
