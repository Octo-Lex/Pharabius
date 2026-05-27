"""Tests for sample .ai-debt bundle validation (W50-S03)."""

from __future__ import annotations

import json
from pathlib import Path

SAMPLE = Path("docs/examples/sample-ai-debt")


class TestSampleBundleExists:
    def test_readme_exists(self) -> None:
        assert (SAMPLE / "README.md").exists()

    def test_required_json_exists(self) -> None:
        for name in [
            "project-profile.json",
            "evidence.json",
            "debt-register.json",
        ]:
            assert (SAMPLE / name).exists(), f"Missing: {name}"


class TestSampleJsonParses:
    def test_all_json_parses(self) -> None:
        for p in SAMPLE.rglob("*.json"):
            json.loads(p.read_text())


class TestCrossReferences:
    def test_evidence_ids_in_findings(self) -> None:
        reg = json.loads((SAMPLE / "debt-register.json").read_text())
        evd = json.loads((SAMPLE / "evidence.json").read_text())
        evd_ids = {e["id"] for e in evd["evidence"]}
        for f in reg["findings"]:
            for eid in f["evidence_ids"]:
                assert eid in evd_ids, f"Finding {f['id']} refs unknown evidence {eid}"

    def test_finding_ids_stable(self) -> None:
        reg = json.loads((SAMPLE / "debt-register.json").read_text())
        assert reg["findings"][0]["id"] == "TD-DEP-001"


class TestSampleSafety:
    def test_no_secrets(self) -> None:
        dangerous = ["password", "secret", "api_key", "token", "credential"]
        for p in SAMPLE.rglob("*"):
            if p.is_file() and p.suffix in (".json", ".md", ".yaml"):
                text = p.read_text().lower()
                for word in dangerous:
                    assert word not in text, f"'{word}' found in {p}"

    def test_no_real_paths(self) -> None:
        reg = json.loads((SAMPLE / "debt-register.json").read_text())
        for f in reg["findings"]:
            for loc in f["locations"]:
                assert not loc["file"].startswith(("/", "C:", "Users")), \
                    f"Absolute path in sample: {loc['file']}"


class TestSampleMarkdown:
    def test_debt_register_md_has_heading(self) -> None:
        text = (SAMPLE / "debt-register.md").read_text()
        assert "TD-DEP-001" in text

    def test_report_has_findings(self) -> None:
        text = (SAMPLE / "reports" / "foundation-audit-report.md").read_text()
        assert "TD-DEP-001" in text
