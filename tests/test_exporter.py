"""Tests for the export module (SARIF, CSV, JSONL)."""

from __future__ import annotations

import csv
import hashlib
import json
from io import StringIO
from pathlib import Path

from pharabius.core.exporter import export_findings
from pharabius.core.init_workspace import initialize_workspace
from pharabius.schemas.finding import DebtFinding, DebtRegister, DebtRegisterSummary

# ── Helpers ──────────────────────────────────────────────────────────


def _setup_repo(
    tmp_path: Path,
    *,
    findings: list[DebtFinding] | None = None,
    with_verification: bool = False,
) -> Path:
    """Create a minimal .ai-debt workspace for export testing."""
    initialize_workspace(tmp_path)
    ai_debt = tmp_path / ".ai-debt"

    if findings is None:
        findings = [
            DebtFinding(
                id="TD-DEP-001",
                category="TD-DEP",
                title="Test dependency finding",
                description="Test",
                severity="Medium",
                technical_impact="Test",
                business_impact="Test",
                risk_score=50,
                priority="Medium",
                recommended_action="Fix the dependency",
                evidence_ids=["EVD-001"],
                locations=["pom.xml"],
                analysis_unit_ids=["AU-PKG-TEST"],
            )
        ]

    summary = DebtRegisterSummary(total_findings=len(findings), medium=len(findings))
    register = DebtRegister(project_name="test", summary=summary, findings=findings)
    (ai_debt / "debt-register.json").write_text(register.model_dump_json(), encoding="utf-8")

    if with_verification:
        report = {
            "total_findings_checked": len(findings),
            "still_detected_count": len(findings),
            "results": [],
        }
        for f in findings:
            report["results"].append(
                {
                    "finding_id": f.id,
                    "verification_status": "still_detected",
                }
            )
        (ai_debt / "verification-report.json").write_text(json.dumps(report), encoding="utf-8")

    return tmp_path


def _hash_files(paths: list[Path]) -> dict[str, str]:
    """Return SHA-256 hashes for given paths."""
    result = {}
    for p in paths:
        if p.exists():
            result[str(p)] = hashlib.sha256(p.read_bytes()).hexdigest()
    return result


# ── Missing register ─────────────────────────────────────────────────


class TestExportMissingRegister:
    def test_fails_without_register(self, tmp_path: Path) -> None:
        import pytest

        # Do NOT call initialize_workspace — it creates stub files
        with pytest.raises(FileNotFoundError, match=r"debt-register\.json not found"):
            export_findings(tmp_path)


# ── SARIF ────────────────────────────────────────────────────────────


class TestSarifExport:
    def test_basic_structure(self, tmp_path: Path) -> None:
        _setup_repo(tmp_path)
        result = export_findings(tmp_path, formats=["sarif"])
        sarif_path = result.files_written[0]
        sarif = json.loads(sarif_path.read_text(encoding="utf-8"))

        assert "$schema" in sarif
        assert sarif["version"] == "2.1.0"
        assert len(sarif["runs"]) == 1
        run = sarif["runs"][0]
        assert run["tool"]["driver"]["name"] == "Pharabius"
        assert isinstance(run["tool"]["driver"]["rules"], list)
        assert isinstance(run["results"], list)

    def test_sarif_version_2_1_0(self, tmp_path: Path) -> None:
        _setup_repo(tmp_path)
        result = export_findings(tmp_path, formats=["sarif"])
        sarif = json.loads(result.files_written[0].read_text(encoding="utf-8"))
        assert sarif["version"] == "2.1.0"

    def test_severity_mapping(self, tmp_path: Path) -> None:
        findings = [
            DebtFinding(
                id="TD-SEC-001",
                category="TD-SEC",
                title="High finding",
                description="Test",
                severity="High",
                technical_impact="Test",
                business_impact="Test",
                risk_score=80,
                priority="High",
                recommended_action="Fix",
            ),
            DebtFinding(
                id="TD-DEP-001",
                category="TD-DEP",
                title="Medium finding",
                description="Test",
                severity="Medium",
                technical_impact="Test",
                business_impact="Test",
                risk_score=50,
                priority="Medium",
                recommended_action="Fix",
            ),
            DebtFinding(
                id="TD-DOC-001",
                category="TD-DOC",
                title="Low finding",
                description="Test",
                severity="Low",
                technical_impact="Test",
                business_impact="Test",
                risk_score=10,
                priority="Low",
                recommended_action="Fix",
            ),
        ]
        _setup_repo(tmp_path, findings=findings)
        result = export_findings(tmp_path, formats=["sarif"])
        sarif = json.loads(result.files_written[0].read_text(encoding="utf-8"))
        levels = {r["message"]["text"]: r["level"] for r in sarif["runs"][0]["results"]}
        assert levels["High finding"] == "error"
        assert levels["Medium finding"] == "warning"
        assert levels["Low finding"] == "note"

    def test_locations_populated(self, tmp_path: Path) -> None:
        _setup_repo(tmp_path)
        result = export_findings(tmp_path, formats=["sarif"])
        sarif = json.loads(result.files_written[0].read_text(encoding="utf-8"))
        res = sarif["runs"][0]["results"][0]
        assert len(res["locations"]) == 1
        assert res["locations"][0]["physicalLocation"]["artifactLocation"]["uri"] == "pom.xml"
        assert res["locations"][0]["physicalLocation"]["region"]["startLine"] == 1

    def test_no_locations_empty(self, tmp_path: Path) -> None:
        findings = [
            DebtFinding(
                id="TD-DOC-001",
                category="TD-DOC",
                title="No locations",
                description="Test",
                severity="Low",
                technical_impact="Test",
                business_impact="Test",
                risk_score=10,
                priority="Low",
                recommended_action="Fix",
            )
        ]
        _setup_repo(tmp_path, findings=findings)
        result = export_findings(tmp_path, formats=["sarif"])
        sarif = json.loads(result.files_written[0].read_text(encoding="utf-8"))
        res = sarif["runs"][0]["results"][0]
        assert res["locations"] == []

    def test_properties(self, tmp_path: Path) -> None:
        _setup_repo(tmp_path)
        result = export_findings(tmp_path, formats=["sarif"])
        sarif = json.loads(result.files_written[0].read_text(encoding="utf-8"))
        props = sarif["runs"][0]["results"][0]["properties"]
        assert props["debtId"] == "TD-DEP-001"
        assert "evidenceIds" in props
        assert "analysisUnitIds" in props
        assert "verificationStatus" in props


# ── CSV ──────────────────────────────────────────────────────────────


class TestCsvExport:
    def test_headers(self, tmp_path: Path) -> None:
        _setup_repo(tmp_path)
        result = export_findings(tmp_path, formats=["csv"])
        content = result.files_written[0].read_text(encoding="utf-8-sig")
        reader = csv.reader(StringIO(content))
        headers = next(reader)
        assert headers == [
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

    def test_row_count(self, tmp_path: Path) -> None:
        _setup_repo(tmp_path)
        result = export_findings(tmp_path, formats=["csv"])
        content = result.files_written[0].read_text(encoding="utf-8-sig")
        reader = csv.reader(StringIO(content))
        rows = list(reader)
        # 1 header + 1 finding
        assert len(rows) == 2

    def test_quoting(self, tmp_path: Path) -> None:
        findings = [
            DebtFinding(
                id="TD-DEP-001",
                category="TD-DEP",
                title="Has, commas",
                description="Test",
                severity="Medium",
                technical_impact="Test",
                business_impact="Test",
                risk_score=50,
                priority="Medium",
                recommended_action="Fix deps, run tests",
            )
        ]
        _setup_repo(tmp_path, findings=findings)
        result = export_findings(tmp_path, formats=["csv"])
        # Should not crash; re-read to verify quoting
        content = result.files_written[0].read_text(encoding="utf-8-sig")
        reader = csv.reader(StringIO(content))
        rows = list(reader)
        assert rows[1][1] == "Has, commas"
        assert rows[1][11] == "Fix deps, run tests"

    def test_utf8_bom(self, tmp_path: Path) -> None:
        _setup_repo(tmp_path)
        result = export_findings(tmp_path, formats=["csv"])
        raw = result.files_written[0].read_bytes()
        assert raw[:3] == b"\xef\xbb\xbf"


# ── JSONL ────────────────────────────────────────────────────────────


class TestJsonlExport:
    def test_line_count(self, tmp_path: Path) -> None:
        _setup_repo(tmp_path)
        result = export_findings(tmp_path, formats=["jsonl"])
        content = result.files_written[0].read_text(encoding="utf-8")
        lines = [line for line in content.strip().split("\n") if line]
        assert len(lines) == 1

    def test_parseable(self, tmp_path: Path) -> None:
        _setup_repo(tmp_path)
        result = export_findings(tmp_path, formats=["jsonl"])
        content = result.files_written[0].read_text(encoding="utf-8")
        for line in content.strip().split("\n"):
            if line:
                obj = json.loads(line)
                assert isinstance(obj, dict)

    def test_fields(self, tmp_path: Path) -> None:
        _setup_repo(tmp_path)
        result = export_findings(tmp_path, formats=["jsonl"])
        content = result.files_written[0].read_text(encoding="utf-8")
        obj = json.loads(content.strip())
        expected_fields = {
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
        }
        assert set(obj.keys()) == expected_fields


# ── Enrichment ───────────────────────────────────────────────────────


class TestExportEnrichment:
    def test_includes_verification_status(self, tmp_path: Path) -> None:
        _setup_repo(tmp_path, with_verification=True)
        result = export_findings(tmp_path, formats=["jsonl"])
        content = result.files_written[0].read_text(encoding="utf-8")
        obj = json.loads(content.strip())
        assert obj["verification_status"] == "still_detected"

    def test_without_verification(self, tmp_path: Path) -> None:
        _setup_repo(tmp_path, with_verification=False)
        result = export_findings(tmp_path, formats=["jsonl"])
        content = result.files_written[0].read_text(encoding="utf-8")
        obj = json.loads(content.strip())
        assert obj["verification_status"] == ""

    def test_without_units_file(self, tmp_path: Path) -> None:
        _setup_repo(tmp_path)
        # No analysis-units.json — but finding has analysis_unit_ids
        result = export_findings(tmp_path, formats=["jsonl"])
        content = result.files_written[0].read_text(encoding="utf-8")
        obj = json.loads(content.strip())
        assert obj["analysis_unit_ids"] == ["AU-PKG-TEST"]


# ── Immutability ─────────────────────────────────────────────────────


class TestExportImmutability:
    def test_does_not_modify_source(self, tmp_path: Path) -> None:
        _setup_repo(tmp_path, with_verification=True)
        ai_debt = tmp_path / ".ai-debt"
        source_files = [
            ai_debt / "debt-register.json",
            ai_debt / "verification-report.json",
        ]
        before = _hash_files(source_files)

        export_findings(tmp_path)

        after = _hash_files(source_files)
        for path_str, hash_val in before.items():
            assert after[path_str] == hash_val, f"Modified: {path_str}"


# ── CLI options ──────────────────────────────────────────────────────


class TestExportCliOptions:
    def test_format_sarif_only(self, tmp_path: Path) -> None:
        _setup_repo(tmp_path)
        result = export_findings(tmp_path, formats=["sarif"])
        written = [p.suffix for p in result.files_written]
        assert written == [".sarif"]

    def test_format_all(self, tmp_path: Path) -> None:
        _setup_repo(tmp_path)
        result = export_findings(tmp_path, formats=["sarif", "csv", "jsonl"])
        written = sorted([p.suffix for p in result.files_written])
        assert written == [".csv", ".jsonl", ".sarif"]

    def test_custom_output_dir(self, tmp_path: Path) -> None:
        _setup_repo(tmp_path)
        custom = tmp_path / "custom-output"
        result = export_findings(tmp_path, output_dir=custom)
        assert all(str(custom) in str(p) for p in result.files_written)


# ── Zero findings ────────────────────────────────────────────────────


class TestExportZeroFindings:
    def test_zero_finding_sarif(self, tmp_path: Path) -> None:
        _setup_repo(tmp_path, findings=[])
        result = export_findings(tmp_path, formats=["sarif"])
        sarif = json.loads(result.files_written[0].read_text(encoding="utf-8"))
        assert sarif["runs"][0]["results"] == []
        assert sarif["runs"][0]["tool"]["driver"]["rules"] == []

    def test_zero_finding_csv(self, tmp_path: Path) -> None:
        _setup_repo(tmp_path, findings=[])
        result = export_findings(tmp_path, formats=["csv"])
        content = result.files_written[0].read_text(encoding="utf-8-sig")
        reader = csv.reader(StringIO(content))
        rows = list(reader)
        # Only header
        assert len(rows) == 1
        assert rows[0][0] == "debt_id"

    def test_zero_finding_jsonl(self, tmp_path: Path) -> None:
        _setup_repo(tmp_path, findings=[])
        result = export_findings(tmp_path, formats=["jsonl"])
        content = result.files_written[0].read_text(encoding="utf-8")
        # Empty file
        assert content.strip() == ""
