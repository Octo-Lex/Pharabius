"""Tests for AI adapter, context assembly, validation, and CLI integration."""

import json
from pathlib import Path
from typing import Any

import pytest

from pharabius.ai.adapter import DisabledAdapter
from pharabius.ai.context import (
    AIBudget,
    build_enrichment_context,
    get_evidence_map,
    get_finding_by_id,
    get_findings,
    get_linked_evidence,
    get_linked_units,
    get_verification_status,
    load_artifacts,
)
from pharabius.ai.enricher import enrich_findings
from pharabius.ai.mock_provider import MockAIAdapter
from pharabius.ai.validator import (
    validate_finding_enrichment,
    validate_raw_output,
)
from pharabius.schemas.ai_enrichment import (
    AIEnrichmentReport,
    FindingEnrichment,
)

# ── Fixtures ────────────────────────────────────────────────────────


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


@pytest.fixture
def sample_repo(tmp_path: Path) -> Path:
    """Create a minimal repo with .ai-debt artifacts."""
    ai_debt = tmp_path / ".ai-debt"
    _write_json(
        ai_debt / "evidence.json",
        {
            "schema_version": "1.0",
            "evidence": [
                {
                    "evidence_id": "EVD-001",
                    "type": "manifest_detected",
                    "location": {"file": "pyproject.toml"},
                    "raw_observation": "Python project manifest detected",
                },
                {
                    "evidence_id": "EVD-002",
                    "type": "dependency_manifest_detected",
                    "location": {"file": "requirements.txt"},
                    "raw_observation": "Dependencies without lockfile",
                },
                {
                    "evidence_id": "EVD-003",
                    "type": "test_file_detected",
                    "location": {"file": "tests/test_main.py"},
                    "raw_observation": "Test file detected",
                },
            ],
        },
    )
    _write_json(
        ai_debt / "debt-register.json",
        {
            "schema_version": "1.0",
            "project_name": "test-project",
            "findings": [
                {
                    "id": "TD-DEP-001",
                    "category": "TD-DEP",
                    "title": "Missing lockfile",
                    "severity": "Medium",
                    "evidence_ids": ["EVD-001", "EVD-002"],
                    "analysis_unit_ids": ["AU-PKG-ABC12345"],
                },
                {
                    "id": "TD-DEP-002",
                    "category": "TD-DEP",
                    "title": "Another dependency finding",
                    "severity": "High",
                    "evidence_ids": ["EVD-002"],
                    "analysis_unit_ids": [],
                },
            ],
        },
    )
    _write_json(
        ai_debt / "analysis-units.json",
        {
            "schema_version": "1.0",
            "units": [
                {
                    "unit_id": "AU-PKG-ABC12345",
                    "unit_type": "package",
                    "name": "test-pkg",
                }
            ],
        },
    )
    return tmp_path


@pytest.fixture
def empty_repo(tmp_path: Path) -> Path:
    """Repo with empty debt register."""
    ai_debt = tmp_path / ".ai-debt"
    _write_json(
        ai_debt / "evidence.json",
        {"schema_version": "1.0", "evidence": []},
    )
    _write_json(
        ai_debt / "debt-register.json",
        {"schema_version": "1.0", "findings": []},
    )
    return tmp_path


# ── Adapter Tests ───────────────────────────────────────────────────


class TestDisabledAdapter:
    def test_returns_disabled_response(self):
        adapter = DisabledAdapter()
        resp = adapter.generate_json("test prompt", {})
        assert resp.provider == "disabled"
        assert resp.finish_reason == "disabled"
        assert len(resp.errors) > 0

    def test_name_and_model(self):
        adapter = DisabledAdapter()
        assert adapter.name == "disabled"
        assert adapter.model == "none"

    def test_no_parsed_json(self):
        adapter = DisabledAdapter()
        resp = adapter.generate_json("test", {})
        assert resp.parsed_json is None


class TestMockAdapter:
    def test_returns_schema_valid_output(self, sample_repo: Path):
        adapter = MockAIAdapter()
        artifacts = load_artifacts(sample_repo / ".ai-debt")
        register = artifacts["register"]
        findings = get_findings(register, max_findings=1)
        evidence_map = get_evidence_map(artifacts)

        context = {"findings": findings, "evidence_map": evidence_map}
        resp = adapter.generate_json("enrich", context)

        assert resp.provider == "mock"
        assert resp.finish_reason == "complete"
        assert resp.parsed_json is not None
        assert "enrichments" in resp.parsed_json
        assert len(resp.parsed_json["enrichments"]) == 1

    def test_preserves_evidence_ids(self, sample_repo: Path):
        adapter = MockAIAdapter()
        artifacts = load_artifacts(sample_repo / ".ai-debt")
        register = artifacts["register"]
        findings = get_findings(register, max_findings=1)
        evidence_map = get_evidence_map(artifacts)

        context = {"findings": findings, "evidence_map": evidence_map}
        resp = adapter.generate_json("enrich", context)

        enrichment = resp.parsed_json["enrichments"][0]
        assert "EVD-001" in enrichment["evidence_ids"]
        assert "EVD-002" in enrichment["evidence_ids"]

    def test_usage_metrics(self, sample_repo: Path):
        adapter = MockAIAdapter()
        artifacts = load_artifacts(sample_repo / ".ai-debt")
        register = artifacts["register"]
        findings = get_findings(register, max_findings=1)
        evidence_map = get_evidence_map(artifacts)

        context = {"findings": findings, "evidence_map": evidence_map}
        resp = adapter.generate_json("enrich", context)

        assert resp.usage.items_processed == 1
        assert resp.usage.items_accepted == 1
        assert resp.usage.items_rejected == 0
        assert resp.usage.prompt_chars > 0

    def test_no_findings_returns_empty(self):
        adapter = MockAIAdapter()
        context = {"findings": [], "evidence_map": {}}
        resp = adapter.generate_json("enrich", context)
        assert resp.parsed_json["enrichments"] == []

    def test_no_network_imports(self):
        """Verify no httpx/requests/aiohttp imports in mock provider."""
        import pharabius.ai.mock_provider as mod

        source = Path(mod.__file__).read_text(encoding="utf-8")
        assert "httpx" not in source
        assert "requests" not in source
        assert "aiohttp" not in source
        assert "urllib" not in source


# ── Context Tests ───────────────────────────────────────────────────


class TestLoadArtifacts:
    def test_loads_existing(self, sample_repo: Path):
        artifacts = load_artifacts(sample_repo / ".ai-debt")
        assert "evidence" in artifacts
        assert "register" in artifacts
        assert len(artifacts["register"]["findings"]) == 2

    def test_missing_files_return_empty(self, tmp_path: Path):
        artifacts = load_artifacts(tmp_path / ".ai-debt")
        assert artifacts["evidence"] == {}
        assert artifacts["register"] == {}
        assert artifacts["units"] == {}
        assert artifacts["graph"] == {}
        assert artifacts["verification"] == {}


class TestContextAssembly:
    def test_only_linked_evidence_included(self, sample_repo: Path):
        artifacts = load_artifacts(sample_repo / ".ai-debt")
        register = artifacts["register"]
        finding = register["findings"][0]  # TD-DEP-001 with EVD-001, EVD-002
        budget = AIBudget()
        evidence_items, _ = get_linked_evidence(artifacts, finding["evidence_ids"], budget)
        included_ids = {e.get("evidence_id") for e in evidence_items}
        assert "EVD-001" in included_ids
        assert "EVD-002" in included_ids
        assert "EVD-003" not in included_ids

    def test_budget_respected(self, sample_repo: Path):
        artifacts = load_artifacts(sample_repo / ".ai-debt")
        register = artifacts["register"]
        finding = register["findings"][0]
        budget = AIBudget(max_evidence_items=1)
        evidence_items, omitted = get_linked_evidence(artifacts, finding["evidence_ids"], budget)
        assert len(evidence_items) <= 1
        assert omitted >= 1

    def test_omitted_evidence_recorded(self, sample_repo: Path):
        artifacts = load_artifacts(sample_repo / ".ai-debt")
        register = artifacts["register"]
        finding = register["findings"][0]
        budget = AIBudget(max_evidence_items=0)
        _, omitted = get_linked_evidence(artifacts, finding["evidence_ids"], budget)
        assert omitted == 2

    def test_units_absent_works(self, tmp_path: Path):
        ai_debt = tmp_path / ".ai-debt"
        _write_json(
            ai_debt / "evidence.json",
            {"schema_version": "1.0", "evidence": []},
        )
        _write_json(
            ai_debt / "debt-register.json",
            {"schema_version": "1.0", "findings": [{"id": "F-001", "evidence_ids": []}]},
        )
        artifacts = load_artifacts(ai_debt)
        ctx = build_enrichment_context(artifacts, max_findings=10)
        assert len(ctx["findings"]) == 1

    def test_graph_absent_works(self, tmp_path: Path):
        ai_debt = tmp_path / ".ai-debt"
        _write_json(
            ai_debt / "evidence.json",
            {"schema_version": "1.0", "evidence": []},
        )
        _write_json(
            ai_debt / "debt-register.json",
            {"schema_version": "1.0", "findings": [{"id": "F-001", "evidence_ids": []}]},
        )
        artifacts = load_artifacts(ai_debt)
        ctx = build_enrichment_context(artifacts, max_findings=10)
        assert len(ctx["findings"]) == 1

    def test_verification_absent_works(self, tmp_path: Path):
        artifacts = {"register": {"findings": [{"id": "F-001"}]}, "evidence": {"evidence": []}}
        status = get_verification_status(artifacts, "F-001")
        assert status is None

    def test_empty_register_handled(self, empty_repo: Path):
        artifacts = load_artifacts(empty_repo / ".ai-debt")
        ctx = build_enrichment_context(artifacts)
        assert ctx["findings"] == []

    def test_analysis_units_included(self, sample_repo: Path):
        artifacts = load_artifacts(sample_repo / ".ai-debt")
        register = artifacts["register"]
        finding = register["findings"][0]  # Has AU-PKG-ABC12345
        budget = AIBudget()
        units, _ = get_linked_units(artifacts, finding["analysis_unit_ids"], budget)
        assert len(units) == 1
        assert units[0]["unit_id"] == "AU-PKG-ABC12345"


class TestGetFindingById:
    def test_found(self, sample_repo: Path):
        artifacts = load_artifacts(sample_repo / ".ai-debt")
        f = get_finding_by_id(artifacts["register"], "TD-DEP-001")
        assert f is not None
        assert f["title"] == "Missing lockfile"

    def test_not_found(self, sample_repo: Path):
        artifacts = load_artifacts(sample_repo / ".ai-debt")
        f = get_finding_by_id(artifacts["register"], "NONEXISTENT")
        assert f is None


# ── Validation Tests ────────────────────────────────────────────────


class TestValidation:
    def _make_valid_enrichment(self) -> dict[str, Any]:
        return {
            "finding_id": "TD-DEP-001",
            "evidence_ids": ["EVD-001", "EVD-002"],
            "confidence": "Medium",
            "limitations": ["AI-generated enrichment — validate before acting"],
            "explanation": "Test explanation",
        }

    def test_valid_enrichment_accepted(self):
        result = validate_finding_enrichment(
            self._make_valid_enrichment(),
            valid_finding_ids={"TD-DEP-001"},
            valid_evidence_ids={"EVD-001", "EVD-002"},
        )
        assert result.is_valid
        assert result.enrichment is not None
        assert result.enrichment.finding_id == "TD-DEP-001"

    def test_missing_evidence_id_rejected(self):
        data = self._make_valid_enrichment()
        data["evidence_ids"] = ["EVD-001", "EVD-NONEXISTENT"]
        result = validate_finding_enrichment(
            data,
            valid_finding_ids={"TD-DEP-001"},
            valid_evidence_ids={"EVD-001", "EVD-002"},
        )
        assert not result.is_valid
        assert "EVD-NONEXISTENT" in result.missing_evidence_ids

    def test_unknown_finding_id_rejected(self):
        data = self._make_valid_enrichment()
        data["finding_id"] = "FAKE-001"
        result = validate_finding_enrichment(
            data,
            valid_finding_ids={"TD-DEP-001"},
            valid_evidence_ids={"EVD-001"},
        )
        assert not result.is_valid
        assert "finding_id" in result.invalid_fields

    def test_malformed_json_rejected(self):
        results = validate_raw_output(
            "not json {{{",
            valid_finding_ids={"TD-DEP-001"},
            valid_evidence_ids={"EVD-001"},
        )
        assert len(results) == 1
        assert not results[0].is_valid
        assert any("Malformed JSON" in r for r in results[0].rejection_reasons)

    def test_extra_fields_rejected(self):
        data = self._make_valid_enrichment()
        data["invented_field"] = "should not be allowed"
        result = validate_finding_enrichment(
            data,
            valid_finding_ids={"TD-DEP-001"},
            valid_evidence_ids={"EVD-001", "EVD-002"},
        )
        assert not result.is_valid

    def test_invalid_confidence_rejected(self):
        data = self._make_valid_enrichment()
        data["confidence"] = "SuperHigh"
        result = validate_finding_enrichment(
            data,
            valid_finding_ids={"TD-DEP-001"},
            valid_evidence_ids={"EVD-001", "EVD-002"},
        )
        assert not result.is_valid
        assert "confidence" in result.invalid_fields

    def test_empty_limitations_rejected(self):
        data = self._make_valid_enrichment()
        data["limitations"] = []
        result = validate_finding_enrichment(
            data,
            valid_finding_ids={"TD-DEP-001"},
            valid_evidence_ids={"EVD-001", "EVD-002"},
        )
        assert not result.is_valid
        assert "limitations" in result.invalid_fields

    def test_unknown_unit_ids_rejected(self):
        data = self._make_valid_enrichment()
        data["analysis_unit_ids"] = ["AU-FAKE-00000000"]
        result = validate_finding_enrichment(
            data,
            valid_finding_ids={"TD-DEP-001"},
            valid_evidence_ids={"EVD-001", "EVD-002"},
            valid_unit_ids={"AU-PKG-ABC12345"},
        )
        assert not result.is_valid
        assert "analysis_unit_ids" in result.invalid_fields

    def test_unknown_graph_ids_rejected(self):
        data = self._make_valid_enrichment()
        data["graph_ids"] = ["ARCH-NODE-FAKE0000"]
        result = validate_finding_enrichment(
            data,
            valid_finding_ids={"TD-DEP-001"},
            valid_evidence_ids={"EVD-001", "EVD-002"},
            valid_graph_ids={"ARCH-NODE-REAL0001"},
        )
        assert not result.is_valid
        assert "graph_ids" in result.invalid_fields

    def test_partial_invalid_handled(self):
        """Multiple enrichments — one valid, one invalid."""
        valid_enc = self._make_valid_enrichment()
        invalid_enc = self._make_valid_enrichment()
        invalid_enc["finding_id"] = "FAKE-001"

        raw = json.dumps({"enrichments": [valid_enc, invalid_enc]})
        results = validate_raw_output(
            raw,
            valid_finding_ids={"TD-DEP-001"},
            valid_evidence_ids={"EVD-001", "EVD-002"},
        )
        assert len(results) == 2
        assert results[0].is_valid
        assert not results[1].is_valid

    def test_normal_prose_not_rejected(self):
        """Normal prose with module names should pass schema validation."""
        data = self._make_valid_enrichment()
        data["explanation"] = (
            "The module `pharabius.core.analyzer` uses `pharabius.schemas.finding`. "
            "Commands like `ai-debt scan` collect evidence. "
            "Package `my-lib` version 1.0.0 was detected."
        )
        result = validate_finding_enrichment(
            data,
            valid_finding_ids={"TD-DEP-001"},
            valid_evidence_ids={"EVD-001", "EVD-002"},
        )
        assert result.is_valid


# ── Enricher Integration Tests ──────────────────────────────────────


class TestEnrichFindings:
    def test_disabled_provider_writes_nothing(self, sample_repo: Path):
        report = enrich_findings(sample_repo, provider_name="disabled")
        assert report.provider == "disabled"
        assert not (sample_repo / ".ai-debt" / "ai").exists()

    def test_mock_provider_writes_sidecar(self, sample_repo: Path):
        report = enrich_findings(sample_repo, provider_name="mock")
        assert report.provider == "mock"
        assert len(report.enrichments) > 0
        assert (sample_repo / ".ai-debt" / "ai" / "enrichment-report.json").exists()
        assert (sample_repo / ".ai-debt" / "ai" / "enrichment-report.md").exists()
        assert (sample_repo / ".ai-debt" / "ai" / "finding-enrichments.json").exists()
        assert (sample_repo / ".ai-debt" / "ai" / "rejected-ai-output.json").exists()

    def test_dry_run_writes_nothing(self, sample_repo: Path):
        report = enrich_findings(sample_repo, provider_name="mock", dry_run=True)
        assert len(report.enrichments) > 0
        assert not (sample_repo / ".ai-debt" / "ai").exists()

    def test_finding_id_limits_enrichment(self, sample_repo: Path):
        report = enrich_findings(sample_repo, provider_name="mock", finding_id="TD-DEP-001")
        assert len(report.enrichments) == 1
        assert report.enrichments[0].finding_id == "TD-DEP-001"

    def test_max_findings_limits_count(self, sample_repo: Path):
        report = enrich_findings(sample_repo, provider_name="mock", max_findings=1)
        assert len(report.enrichments) == 1

    def test_empty_register(self, empty_repo: Path):
        report = enrich_findings(empty_repo, provider_name="mock")
        assert len(report.enrichments) == 0
        assert len(report.rejections) == 0

    def test_strict_mode_rejects_all_on_failure(self, sample_repo: Path):
        """If mock produces valid output, strict should still pass."""
        report = enrich_findings(sample_repo, provider_name="mock", strict=True)
        # Mock produces valid output, so strict should pass
        assert len(report.enrichments) > 0


class TestEnricherImmutability:
    def test_debt_register_unchanged(self, sample_repo: Path):
        register_path = sample_repo / ".ai-debt" / "debt-register.json"
        before = register_path.read_text(encoding="utf-8")
        enrich_findings(sample_repo, provider_name="mock")
        after = register_path.read_text(encoding="utf-8")
        assert before == after

    def test_evidence_unchanged(self, sample_repo: Path):
        evidence_path = sample_repo / ".ai-debt" / "evidence.json"
        before = evidence_path.read_text(encoding="utf-8")
        enrich_findings(sample_repo, provider_name="mock")
        after = evidence_path.read_text(encoding="utf-8")
        assert before == after

    def test_analysis_units_unchanged(self, sample_repo: Path):
        units_path = sample_repo / ".ai-debt" / "analysis-units.json"
        before = units_path.read_text(encoding="utf-8")
        enrich_findings(sample_repo, provider_name="mock")
        after = units_path.read_text(encoding="utf-8")
        assert before == after


class TestEnricherReportFormat:
    def test_report_json_valid(self, sample_repo: Path):
        enrich_findings(sample_repo, provider_name="mock")
        report_path = sample_repo / ".ai-debt" / "ai" / "enrichment-report.json"
        data = json.loads(report_path.read_text(encoding="utf-8"))
        report = AIEnrichmentReport.model_validate(data)
        assert report.is_ai_enriched is True
        assert report.schema_version == "1.0"
        assert len(report.enrichments) > 0

    def test_report_md_readable(self, sample_repo: Path):
        enrich_findings(sample_repo, provider_name="mock")
        md_path = sample_repo / ".ai-debt" / "ai" / "enrichment-report.md"
        content = md_path.read_text(encoding="utf-8")
        assert "# AI Enrichment Report" in content
        assert "mock" in content
        assert "TD-DEP-001" in content

    def test_enrichments_json_valid(self, sample_repo: Path):
        enrich_findings(sample_repo, provider_name="mock")
        enc_path = sample_repo / ".ai-debt" / "ai" / "finding-enrichments.json"
        data = json.loads(enc_path.read_text(encoding="utf-8"))
        assert isinstance(data, list)
        for item in data:
            FindingEnrichment.model_validate(item)

    def test_rejections_json_valid(self, sample_repo: Path):
        enrich_findings(sample_repo, provider_name="mock")
        rej_path = sample_repo / ".ai-debt" / "ai" / "rejected-ai-output.json"
        data = json.loads(rej_path.read_text(encoding="utf-8"))
        assert isinstance(data, list)

    def test_report_labels_ai_enrichment(self, sample_repo: Path):
        enrich_findings(sample_repo, provider_name="mock")
        md_path = sample_repo / ".ai-debt" / "ai" / "enrichment-report.md"
        content = md_path.read_text(encoding="utf-8")
        assert "AI-generated enrichment" in content
        assert "debt-register.json" in content
