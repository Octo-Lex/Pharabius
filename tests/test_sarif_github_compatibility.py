"""Tests for SARIF GitHub Code Scanning compatibility (W53-S04)."""

from __future__ import annotations

import json
from pathlib import Path

from pharabius.core.exporter import export_findings
from pharabius.schemas.finding import DebtFinding, DebtRegister


def _make_register(findings: list[DebtFinding]) -> DebtRegister:
    return DebtRegister(schema_version="1.0", findings=findings)


def _finding(
    fid: str = "TD-DEP-001",
    category: str = "TD-DEP",
    severity: str = "Medium",
    locations: list[str] | None = None,
) -> DebtFinding:
    return DebtFinding(
        id=fid,
        category=category,
        title="Test finding",
        description="Test description",
        severity=severity,
        confidence="High",
        risk_score=5,
        priority="Medium",
        technical_impact="Low",
        business_impact="Low",
        recommended_action="Fix it",
        evidence_ids=["EVD-001"],
        locations=locations or ["src/test.py"],
    )


def _export_sarif(tmp_path: Path, findings: list[DebtFinding]) -> dict:
    """Export SARIF and return parsed JSON."""
    reg = _make_register(findings)
    # Write debt register to expected location
    ai_debt = tmp_path / ".ai-debt"
    ai_debt.mkdir(exist_ok=True)
    dr_path = ai_debt / "debt-register.json"
    dr_path.write_text(
        json.dumps(json.loads(reg.model_dump_json()), indent=2),
        encoding="utf-8",
    )
    out = tmp_path / "out"
    result = export_findings(tmp_path, formats=["sarif"], output_dir=out)
    sarif_path = out / "findings.sarif"
    assert sarif_path.exists(), f"SARIF not found: {result}"
    return json.loads(sarif_path.read_text(encoding="utf-8"))


class TestSarifGitHubCompatibility:
    def test_schema_and_version(self, tmp_path: Path) -> None:
        sarif = _export_sarif(tmp_path, [_finding()])
        assert sarif["$schema"].endswith("sarif-schema-2.1.0.json")
        assert sarif["version"] == "2.1.0"

    def test_tool_driver(self, tmp_path: Path) -> None:
        sarif = _export_sarif(tmp_path, [_finding()])
        driver = sarif["runs"][0]["tool"]["driver"]
        assert driver["name"] == "Pharabius"
        assert "version" in driver
        assert len(driver["version"]) > 0

    def test_severity_mapping(self, tmp_path: Path) -> None:
        findings = [
            _finding(fid="TD-001", severity="Critical"),
            _finding(fid="TD-002", severity="High"),
            _finding(fid="TD-003", severity="Medium"),
            _finding(fid="TD-004", severity="Low"),
        ]
        sarif = _export_sarif(tmp_path, findings)
        results = sarif["runs"][0]["results"]
        levels = {r["properties"]["debtId"]: r["level"] for r in results}
        assert levels["TD-001"] == "error"
        assert levels["TD-002"] == "error"
        assert levels["TD-003"] == "warning"
        assert levels["TD-004"] == "note"

    def test_relative_file_uris(self, tmp_path: Path) -> None:
        sarif = _export_sarif(tmp_path, [_finding(locations=["src/test.py", "lib/mod.js"])])
        locs = sarif["runs"][0]["results"][0]["locations"]
        for loc in locs:
            uri = loc["physicalLocation"]["artifactLocation"]["uri"]
            assert not Path(uri).is_absolute(), f"URI should be relative: {uri}"
            assert "\\" not in uri, f"URI should use forward slashes: {uri}"

    def test_fingerprints_for_github_dedup(self, tmp_path: Path) -> None:
        sarif = _export_sarif(tmp_path, [_finding(fid="TD-DEP-001")])
        result = sarif["runs"][0]["results"][0]
        assert "fingerprints" in result
        assert result["fingerprints"]["debtId"] == "TD-DEP-001"

    def test_empty_findings_valid_sarif(self, tmp_path: Path) -> None:
        sarif = _export_sarif(tmp_path, [])
        assert sarif["runs"][0]["results"] == []

    def test_message_text_includes_title(self, tmp_path: Path) -> None:
        sarif = _export_sarif(tmp_path, [_finding()])
        result = sarif["runs"][0]["results"][0]
        assert "message" in result
        assert "text" in result["message"]
        assert result["message"]["text"] == "Test finding"
