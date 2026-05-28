"""Tests for SARIF fixture validation (v2.0.1 S04)."""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "sarif"


def _load_fixture(name: str) -> dict:
    path = FIXTURE_DIR / name
    return json.loads(path.read_text(encoding="utf-8"))


class TestSARIFFixtureParsing:
    def test_sample_findings_parses(self) -> None:
        data = _load_fixture("sample-findings.sarif")
        assert isinstance(data, dict)

    def test_empty_findings_parses(self) -> None:
        data = _load_fixture("empty-findings.sarif")
        assert isinstance(data, dict)


class TestSARIFFixtureRequiredFields:
    def test_sample_has_schema(self) -> None:
        data = _load_fixture("sample-findings.sarif")
        assert "$schema" in data
        assert "sarif-schema-2.1.0" in data["$schema"]

    def test_sample_has_version(self) -> None:
        data = _load_fixture("sample-findings.sarif")
        assert data["version"] == "2.1.0"

    def test_sample_has_runs(self) -> None:
        data = _load_fixture("sample-findings.sarif")
        assert len(data["runs"]) >= 1

    def test_sample_has_tool_driver(self) -> None:
        data = _load_fixture("sample-findings.sarif")
        driver = data["runs"][0]["tool"]["driver"]
        assert driver["name"] == "Pharabius"
        assert "version" in driver

    def test_empty_has_empty_results(self) -> None:
        data = _load_fixture("empty-findings.sarif")
        assert data["runs"][0]["results"] == []


class TestSARIFFixtureResults:
    def test_sample_has_results(self) -> None:
        data = _load_fixture("sample-findings.sarif")
        assert len(data["runs"][0]["results"]) >= 1

    def test_sample_result_has_rule_id(self) -> None:
        data = _load_fixture("sample-findings.sarif")
        result = data["runs"][0]["results"][0]
        assert "ruleId" in result
        assert result["ruleId"] == "TD-DEP"

    def test_sample_result_has_level(self) -> None:
        data = _load_fixture("sample-findings.sarif")
        result = data["runs"][0]["results"][0]
        assert "level" in result
        assert result["level"] in ("error", "warning", "note")

    def test_sample_result_has_message(self) -> None:
        data = _load_fixture("sample-findings.sarif")
        result = data["runs"][0]["results"][0]
        assert "message" in result
        assert "text" in result["message"]

    def test_sample_result_has_fingerprints(self) -> None:
        data = _load_fixture("sample-findings.sarif")
        result = data["runs"][0]["results"][0]
        assert "fingerprints" in result
        assert "debtId" in result["fingerprints"]


class TestSARIFFixtureLocations:
    def test_sample_locations_are_relative(self) -> None:
        data = _load_fixture("sample-findings.sarif")
        for result in data["runs"][0]["results"]:
            for loc in result.get("locations", []):
                uri = loc["physicalLocation"]["artifactLocation"]["uri"]
                assert not Path(uri).is_absolute(), f"URI must be relative: {uri}"
                assert "\\" not in uri, f"URI must use forward slashes: {uri}"


class TestSARIFDocs:
    def test_sarif_doc_exists(self) -> None:
        assert (REPO_ROOT / "docs" / "SARIF.md").exists()

    def test_sarif_doc_local_only(self) -> None:
        content = (REPO_ROOT / "docs" / "SARIF.md").read_text(encoding="utf-8")
        assert "local" in content.lower()
        assert "not done by default" in content or "not upload" in content.lower()

    def test_sarif_doc_no_default_upload(self) -> None:
        content = (REPO_ROOT / "docs" / "SARIF.md").read_text(encoding="utf-8")
        lines = content.splitlines()
        for line in lines:
            if "upload-sarif" in line and "codeql" in line:
                assert line.strip().startswith("-") or line.strip().startswith("#"), (
                    f"Upload step must be clearly optional: {line}"
                )

    def test_action_yml_no_upload_sarif(self) -> None:
        content = (REPO_ROOT / "action.yml").read_text(encoding="utf-8")
        assert "upload-sarif" not in content
