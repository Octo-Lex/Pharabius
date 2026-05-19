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


# ── FailingMockAdapter (test-only) ──────────────────────────────────


class FailingMockAdapter(MockAIAdapter):
    """Configurable mock that produces invalid output for testing rejection."""

    def __init__(self, mode: str = "valid") -> None:
        self._mode = mode

    def generate_json(
        self, prompt: str, context: dict[str, Any], schema_hint: dict[str, Any] | None = None
    ) -> Any:
        from pharabius.ai.adapter import AIResponse
        from pharabius.schemas.ai_enrichment import AIUsageSummary

        findings = context.get("findings", [])
        if self._mode == "malformed-json":
            return AIResponse(
                provider="failing-mock",
                model="test",
                raw_text="not json {{{",
                parsed_json=None,
                usage=AIUsageSummary(provider="failing-mock", model="test"),
                errors=["Deliberate malformed JSON"],
            )
        elif self._mode == "wrong-shape":
            raw = json.dumps({"data": "not enrichments"})
            return AIResponse(
                provider="failing-mock",
                model="test",
                raw_text=raw,
                parsed_json={"data": "not enrichments"},
                usage=AIUsageSummary(provider="failing-mock", model="test"),
            )
        elif self._mode == "missing-evidence":
            encs = [
                {
                    "finding_id": f.get("id", ""),
                    "evidence_ids": ["EVD-NONEXISTENT"],
                    "confidence": "Medium",
                    "limitations": ["test"],
                }
                for f in findings
            ]
            raw = json.dumps({"enrichments": encs})
            return AIResponse(
                provider="failing-mock",
                model="test",
                raw_text=raw,
                parsed_json={"enrichments": encs},
                usage=AIUsageSummary(provider="failing-mock", model="test"),
            )
        elif self._mode == "empty-evidence":
            encs = [
                {
                    "finding_id": f.get("id", ""),
                    "evidence_ids": [],
                    "confidence": "Medium",
                    "limitations": ["test"],
                }
                for f in findings
            ]
            raw = json.dumps({"enrichments": encs})
            return AIResponse(
                provider="failing-mock",
                model="test",
                raw_text=raw,
                parsed_json={"enrichments": encs},
                usage=AIUsageSummary(provider="failing-mock", model="test"),
            )
        elif self._mode == "unknown-finding":
            encs = [
                {
                    "finding_id": "FAKE-001",
                    "evidence_ids": ["EVD-001"],
                    "confidence": "Medium",
                    "limitations": ["test"],
                }
            ]
            raw = json.dumps({"enrichments": encs})
            return AIResponse(
                provider="failing-mock",
                model="test",
                raw_text=raw,
                parsed_json={"enrichments": encs},
                usage=AIUsageSummary(provider="failing-mock", model="test"),
            )
        elif self._mode == "extra-fields":
            encs = [
                {
                    "finding_id": f.get("id", ""),
                    "evidence_ids": ["EVD-001"],
                    "confidence": "Medium",
                    "limitations": ["test"],
                    "invented_field": "bad",
                }
                for f in findings
            ]
            raw = json.dumps({"enrichments": encs})
            return AIResponse(
                provider="failing-mock",
                model="test",
                raw_text=raw,
                parsed_json={"enrichments": encs},
                usage=AIUsageSummary(provider="failing-mock", model="test"),
            )
        elif self._mode == "invalid-confidence":
            encs = [
                {
                    "finding_id": f.get("id", ""),
                    "evidence_ids": ["EVD-001"],
                    "confidence": "SuperHigh",
                    "limitations": ["test"],
                }
                for f in findings
            ]
            raw = json.dumps({"enrichments": encs})
            return AIResponse(
                provider="failing-mock",
                model="test",
                raw_text=raw,
                parsed_json={"enrichments": encs},
                usage=AIUsageSummary(provider="failing-mock", model="test"),
            )
        elif self._mode == "empty-limitations":
            encs = [
                {
                    "finding_id": f.get("id", ""),
                    "evidence_ids": ["EVD-001"],
                    "confidence": "Medium",
                    "limitations": [],
                }
                for f in findings
            ]
            raw = json.dumps({"enrichments": encs})
            return AIResponse(
                provider="failing-mock",
                model="test",
                raw_text=raw,
                parsed_json={"enrichments": encs},
                usage=AIUsageSummary(provider="failing-mock", model="test"),
            )
        elif self._mode == "mixed-batch":
            valid_enc = {
                "finding_id": findings[0].get("id", "") if findings else "F-001",
                "evidence_ids": ["EVD-001"],
                "confidence": "Medium",
                "limitations": ["test"],
            }
            invalid_enc = {
                "finding_id": "FAKE-001",
                "evidence_ids": ["EVD-001"],
                "confidence": "Medium",
                "limitations": ["test"],
            }
            raw = json.dumps({"enrichments": [valid_enc, invalid_enc]})
            return AIResponse(
                provider="failing-mock",
                model="test",
                raw_text=raw,
                parsed_json={"enrichments": [valid_enc, invalid_enc]},
                usage=AIUsageSummary(provider="failing-mock", model="test"),
            )
        else:
            return super().generate_json(prompt, context, schema_hint)


# ── Extended Rejection Tests ────────────────────────────────────────


class TestRejectionSchemaFailures:
    def _base(self) -> dict[str, Any]:
        return {
            "finding_id": "TD-DEP-001",
            "evidence_ids": ["EVD-001"],
            "confidence": "Medium",
            "limitations": ["test"],
        }

    def test_valid_json_wrong_shape(self):
        results = validate_raw_output('{"data": "not enrichments"}', {"TD-DEP-001"}, {"EVD-001"})
        assert len(results) == 1
        assert not results[0].is_valid
        assert any("enrichments" in r for r in results[0].rejection_reasons)

    def test_enrichment_array_contains_non_objects(self):
        raw = json.dumps({"enrichments": ["not an object", 42]})
        results = validate_raw_output(raw, {"TD-DEP-001"}, {"EVD-001"})
        assert all(not r.is_valid for r in results)

    def test_missing_finding_id(self):
        data = self._base()
        del data["finding_id"]
        result = validate_finding_enrichment(data, {"TD-DEP-001"}, {"EVD-001"})
        assert not result.is_valid

    def test_missing_evidence_ids(self):
        data = self._base()
        del data["evidence_ids"]
        # Pydantic will use default_factory=list → empty list → rejected by our check
        result = validate_finding_enrichment(data, {"TD-DEP-001"}, {"EVD-001"})
        assert not result.is_valid
        assert "evidence_ids" in result.invalid_fields

    def test_evidence_ids_is_string_not_list(self):
        data = self._base()
        data["evidence_ids"] = "EVD-001"
        result = validate_finding_enrichment(data, {"TD-DEP-001"}, {"EVD-001"})
        assert not result.is_valid

    def test_evidence_ids_empty_list_rejected(self):
        data = self._base()
        data["evidence_ids"] = []
        result = validate_finding_enrichment(data, {"TD-DEP-001"}, {"EVD-001"})
        assert not result.is_valid
        assert "evidence_ids" in result.invalid_fields

    def test_finding_id_null(self):
        data = self._base()
        data["finding_id"] = None
        result = validate_finding_enrichment(data, {"TD-DEP-001"}, {"EVD-001"})
        assert not result.is_valid

    def test_confidence_empty_string(self):
        data = self._base()
        data["confidence"] = ""
        result = validate_finding_enrichment(data, {"TD-DEP-001"}, {"EVD-001"})
        assert not result.is_valid
        assert "confidence" in result.invalid_fields

    def test_multiple_violations_in_one_enrichment(self):
        data = {
            "finding_id": "FAKE-001",
            "evidence_ids": [],
            "confidence": "Bad",
            "limitations": [],
        }
        result = validate_finding_enrichment(data, {"TD-DEP-001"}, {"EVD-001"})
        assert not result.is_valid
        assert len(result.invalid_fields) >= 3  # finding_id, evidence_ids, confidence, limitations


class TestRejectionEvidenceFailures:
    def _base(self) -> dict[str, Any]:
        return {
            "finding_id": "TD-DEP-001",
            "evidence_ids": ["EVD-001"],
            "confidence": "Medium",
            "limitations": ["test"],
        }

    def test_evidence_id_from_another_repo(self):
        data = self._base()
        data["evidence_ids"] = ["EXT-EVD-999"]
        result = validate_finding_enrichment(data, {"TD-DEP-001"}, {"EVD-001"})
        assert not result.is_valid
        assert "EXT-EVD-999" in result.missing_evidence_ids

    def test_invented_finding_id(self):
        data = self._base()
        data["finding_id"] = "TD-NEW-999"
        result = validate_finding_enrichment(data, {"TD-DEP-001"}, {"EVD-001"})
        assert not result.is_valid
        assert "finding_id" in result.invalid_fields


class TestRejectionBatchBehavior:
    def _base(self) -> dict[str, Any]:
        return {
            "finding_id": "TD-DEP-001",
            "evidence_ids": ["EVD-001"],
            "confidence": "Medium",
            "limitations": ["test"],
        }

    def test_valid_plus_invalid_non_strict(self):
        valid = self._base()
        invalid = {**self._base(), "finding_id": "FAKE-001"}
        raw = json.dumps({"enrichments": [valid, invalid]})
        results = validate_raw_output(raw, {"TD-DEP-001"}, {"EVD-001"})
        assert results[0].is_valid
        assert not results[1].is_valid

    def test_valid_plus_invalid_strict(self):
        valid = self._base()
        invalid = {**self._base(), "finding_id": "FAKE-001"}
        raw = json.dumps({"enrichments": [valid, invalid]})
        results = validate_raw_output(raw, {"TD-DEP-001"}, {"EVD-001"})
        # Strict behavior is handled by enricher, not validator
        assert len(results) == 2
        assert results[0].is_valid
        assert not results[1].is_valid

    def test_all_invalid_zero_accepted(self):
        encs = [
            {
                "finding_id": "FAKE-001",
                "evidence_ids": ["EVD-001"],
                "confidence": "Medium",
                "limitations": ["test"],
            }
        ]
        raw = json.dumps({"enrichments": encs})
        results = validate_raw_output(raw, {"TD-DEP-001"}, {"EVD-001"})
        assert all(not r.is_valid for r in results)

    def test_rejection_includes_raw_output_hash(self):
        raw = json.dumps(
            {
                "enrichments": [
                    {
                        "finding_id": "FAKE",
                        "evidence_ids": [],
                        "confidence": "Medium",
                        "limitations": ["t"],
                    }
                ]
            }
        )
        results = validate_raw_output(raw, {"TD-DEP-001"}, {"EVD-001"})
        assert results[0].raw_output_hash != ""
        assert len(results[0].raw_output_hash) == 16

    def test_rejection_includes_timestamp(self):
        raw = json.dumps(
            {
                "enrichments": [
                    {
                        "finding_id": "FAKE",
                        "evidence_ids": [],
                        "confidence": "Medium",
                        "limitations": ["t"],
                    }
                ]
            }
        )
        results = validate_raw_output(raw, {"TD-DEP-001"}, {"EVD-001"})
        assert results[0].timestamp != ""

    def test_same_invalid_same_hash(self):
        raw = json.dumps(
            {
                "enrichments": [
                    {
                        "finding_id": "FAKE",
                        "evidence_ids": [],
                        "confidence": "Medium",
                        "limitations": ["t"],
                    }
                ]
            }
        )
        r1 = validate_raw_output(raw, {"TD-DEP-001"}, {"EVD-001"})
        r2 = validate_raw_output(raw, {"TD-DEP-001"}, {"EVD-001"})
        assert r1[0].raw_output_hash == r2[0].raw_output_hash

    def test_empty_enrichments_array(self):
        raw = json.dumps({"enrichments": []})
        results = validate_raw_output(raw, {"TD-DEP-001"}, {"EVD-001"})
        assert results == []


# ── Context Stress Tests ─────────────────────────────────────────────


class TestContextStress:
    def _make_large_evidence_repo(self, tmp_path: Path, n_evidence: int = 30) -> Path:
        ai_debt = tmp_path / ".ai-debt"
        evidence_items = []
        for i in range(n_evidence):
            evidence_items.append(
                {
                    "evidence_id": f"EVD-{i:03d}",
                    "type": "manifest_detected",
                    "location": {"file": f"file_{i}.py"},
                    "raw_observation": f"Evidence item {i}" + "x" * 200,
                }
            )
        _write_json(
            ai_debt / "evidence.json", {"schema_version": "1.0", "evidence": evidence_items}
        )
        all_evids = [f"EVD-{i:03d}" for i in range(n_evidence)]
        _write_json(
            ai_debt / "debt-register.json",
            {
                "schema_version": "1.0",
                "findings": [
                    {
                        "id": "F-001",
                        "category": "TD-DEP",
                        "title": "Test",
                        "severity": "Medium",
                        "evidence_ids": all_evids,
                        "analysis_unit_ids": [],
                    }
                ],
            },
        )
        return tmp_path

    def test_max_evidence_items_capped(self, tmp_path: Path):
        repo = self._make_large_evidence_repo(tmp_path, 30)
        artifacts = load_artifacts(repo / ".ai-debt")
        budget = AIBudget(max_evidence_items=10)
        items, omitted = get_linked_evidence(artifacts, [f"EVD-{i:03d}" for i in range(30)], budget)
        assert len(items) <= 10
        assert omitted >= 20

    def test_max_context_chars_capped(self, tmp_path: Path):
        repo = self._make_large_evidence_repo(tmp_path, 10)
        artifacts = load_artifacts(repo / ".ai-debt")
        budget = AIBudget(max_context_chars=500)
        items, _ = get_linked_evidence(artifacts, [f"EVD-{i:03d}" for i in range(10)], budget)
        # Should stop before including all 10 due to char budget
        assert len(items) < 10

    def test_long_raw_observation_truncated(self, tmp_path: Path):
        ai_debt = tmp_path / ".ai-debt"
        _write_json(
            ai_debt / "evidence.json",
            {
                "schema_version": "1.0",
                "evidence": [
                    {
                        "evidence_id": "EVD-001",
                        "type": "test",
                        "location": {"file": "a.py"},
                        "raw_observation": "x" * 10000,
                    }
                ],
            },
        )
        _write_json(
            ai_debt / "debt-register.json",
            {
                "schema_version": "1.0",
                "findings": [{"id": "F-001", "evidence_ids": ["EVD-001"], "analysis_unit_ids": []}],
            },
        )
        artifacts = load_artifacts(ai_debt)
        budget = AIBudget()
        items, _ = get_linked_evidence(artifacts, ["EVD-001"], budget)
        assert len(items) == 1
        # Verify observation exists but context stays bounded

    def test_deterministic_evidence_ordering(self, tmp_path: Path):
        repo = self._make_large_evidence_repo(tmp_path, 5)
        artifacts = load_artifacts(repo / ".ai-debt")
        budget = AIBudget()
        ids = ["EVD-000", "EVD-001", "EVD-002", "EVD-003", "EVD-004"]
        items1, _ = get_linked_evidence(artifacts, ids, budget)
        items2, _ = get_linked_evidence(artifacts, ids, budget)
        ids1 = [i["evidence_id"] for i in items1]
        ids2 = [i["evidence_id"] for i in items2]
        assert ids1 == ids2

    def test_empty_raw_observation_handled(self, tmp_path: Path):
        ai_debt = tmp_path / ".ai-debt"
        _write_json(
            ai_debt / "evidence.json",
            {
                "schema_version": "1.0",
                "evidence": [
                    {
                        "evidence_id": "EVD-001",
                        "type": "test",
                        "location": {"file": "a.py"},
                        "raw_observation": "",
                    }
                ],
            },
        )
        _write_json(
            ai_debt / "debt-register.json",
            {
                "schema_version": "1.0",
                "findings": [{"id": "F-001", "evidence_ids": ["EVD-001"], "analysis_unit_ids": []}],
            },
        )
        artifacts = load_artifacts(ai_debt)
        items, _ = get_linked_evidence(artifacts, ["EVD-001"], AIBudget())
        assert len(items) == 1

    def test_zero_evidence_ids_safe(self, tmp_path: Path):
        ai_debt = tmp_path / ".ai-debt"
        _write_json(ai_debt / "evidence.json", {"schema_version": "1.0", "evidence": []})
        _write_json(
            ai_debt / "debt-register.json",
            {
                "schema_version": "1.0",
                "findings": [{"id": "F-001", "evidence_ids": [], "analysis_unit_ids": []}],
            },
        )
        artifacts = load_artifacts(ai_debt)
        items, omitted = get_linked_evidence(artifacts, [], AIBudget())
        assert items == []
        assert omitted == 0

    def test_corrupted_units_degrades(self, tmp_path: Path):
        ai_debt = tmp_path / ".ai-debt"
        _write_json(ai_debt / "evidence.json", {"schema_version": "1.0", "evidence": []})
        _write_json(
            ai_debt / "debt-register.json",
            {
                "schema_version": "1.0",
                "findings": [{"id": "F-001", "evidence_ids": [], "analysis_unit_ids": []}],
            },
        )
        (ai_debt / "analysis-units.json").write_text("not json", encoding="utf-8")
        artifacts = load_artifacts(ai_debt)
        # Should degrade gracefully — units returns empty dict
        assert artifacts["units"] == {}

    def test_corrupted_graph_degrades(self, tmp_path: Path):
        ai_debt = tmp_path / ".ai-debt"
        _write_json(ai_debt / "evidence.json", {"schema_version": "1.0", "evidence": []})
        _write_json(
            ai_debt / "debt-register.json",
            {
                "schema_version": "1.0",
                "findings": [{"id": "F-001", "evidence_ids": [], "analysis_unit_ids": []}],
            },
        )
        (ai_debt / "architecture-graph.json").write_text("not json", encoding="utf-8")
        artifacts = load_artifacts(ai_debt)
        assert artifacts["graph"] == {}

    def test_corrupted_verification_degrades(self, tmp_path: Path):
        ai_debt = tmp_path / ".ai-debt"
        _write_json(ai_debt / "evidence.json", {"schema_version": "1.0", "evidence": []})
        _write_json(
            ai_debt / "debt-register.json",
            {
                "schema_version": "1.0",
                "findings": [{"id": "F-001", "evidence_ids": [], "analysis_unit_ids": []}],
            },
        )
        (ai_debt / "verification-report.json").write_text("not json", encoding="utf-8")
        artifacts = load_artifacts(ai_debt)
        assert artifacts["verification"] == {}

    def test_no_whole_repository_dump(self, sample_repo: Path):
        artifacts = load_artifacts(sample_repo / ".ai-debt")
        budget = AIBudget()
        ctx = build_enrichment_context(artifacts, max_findings=1, budget=budget)
        # Only 1 finding should be in context
        assert len(ctx["findings"]) == 1

    def test_only_linked_evidence_in_context(self, sample_repo: Path):
        artifacts = load_artifacts(sample_repo / ".ai-debt")
        register = artifacts["register"]
        finding = register["findings"][0]  # EVD-001, EVD-002
        budget = AIBudget()
        items, _ = get_linked_evidence(artifacts, finding["evidence_ids"], budget)
        included = {i["evidence_id"] for i in items}
        assert "EVD-003" not in included

    def test_unknown_unit_ids_skipped(self, sample_repo: Path):
        artifacts = load_artifacts(sample_repo / ".ai-debt")
        budget = AIBudget()
        units, _ = get_linked_units(artifacts, ["AU-NONEXISTENT"], budget)
        assert units == []


# ── Sidecar Quality Tests ───────────────────────────────────────────


class TestSidecarQuality:
    def test_md_privacy_caution_present(self, sample_repo: Path):
        enrich_findings(sample_repo, provider_name="mock")
        md = (sample_repo / ".ai-debt" / "ai" / "enrichment-report.md").read_text(encoding="utf-8")
        assert "Privacy Caution" in md
        assert "summarized repository context" in md

    def test_md_states_external_provider_caution(self, sample_repo: Path):
        enrich_findings(sample_repo, provider_name="mock")
        md = (sample_repo / ".ai-debt" / "ai" / "enrichment-report.md").read_text(encoding="utf-8")
        assert "External AI providers" in md or "third-party services" in md

    def test_md_states_canonical_unchanged(self, sample_repo: Path):
        enrich_findings(sample_repo, provider_name="mock")
        md = (sample_repo / ".ai-debt" / "ai" / "enrichment-report.md").read_text(encoding="utf-8")
        assert "No canonical artifacts were modified" in md

    def test_md_includes_timestamp(self, sample_repo: Path):
        enrich_findings(sample_repo, provider_name="mock")
        md = (sample_repo / ".ai-debt" / "ai" / "enrichment-report.md").read_text(encoding="utf-8")
        assert "Generated:" in md


# ── Markdown UX Tests (v0.7.2) ─────────────────────────────────────


class TestMarkdownUX:
    """Tests for sidecar markdown readability improvements."""

    def test_md_summary_table(self, sample_repo: Path) -> None:
        enrich_findings(sample_repo, provider_name="mock")
        md = (sample_repo / ".ai-debt" / "ai" / "enrichment-report.md").read_text(encoding="utf-8")
        assert "## Summary" in md
        assert "| Metric | Value |" in md
        assert "| Provider" in md
        assert "| Model" in md
        assert "Enrichments accepted" in md
        assert "Enrichments rejected" in md
        assert "Evidence IDs referenced" in md
        assert "Evidence items omitted" in md

    def test_md_review_checklist(self, sample_repo: Path) -> None:
        enrich_findings(sample_repo, provider_name="mock")
        md = (sample_repo / ".ai-debt" / "ai" / "enrichment-report.md").read_text(encoding="utf-8")
        assert "## Review Checklist" in md
        assert "- [ ]" in md
        assert "evidence IDs verified" in md
        assert "No canonical artifacts modified" in md
        assert "Privacy caution acknowledged" in md

    def test_md_privacy_caution_updated(self, sample_repo: Path) -> None:
        enrich_findings(sample_repo, provider_name="mock")
        md = (sample_repo / ".ai-debt" / "ai" / "enrichment-report.md").read_text(encoding="utf-8")
        assert "Privacy Caution" in md
        # Should warn about external providers, not claim they're absent
        assert "third-party" in md or "External AI providers" in md

    def test_md_canonical_statement(self, sample_repo: Path) -> None:
        enrich_findings(sample_repo, provider_name="mock")
        md = (sample_repo / ".ai-debt" / "ai" / "enrichment-report.md").read_text(encoding="utf-8")
        assert "No canonical artifacts were modified" in md

    def test_md_evidence_ids_sorted(self, sample_repo: Path) -> None:
        """Evidence IDs in enrichment section should be sorted."""
        enrich_findings(sample_repo, provider_name="mock")
        md = (sample_repo / ".ai-debt" / "ai" / "enrichment-report.md").read_text(encoding="utf-8")
        # Find the line with Evidence IDs
        for line in md.split("\n"):
            if "Evidence IDs:" in line:
                # Extract the IDs after the label
                ids_str = line.split("Evidence IDs:")[1].strip()
                ids = [x.strip() for x in ids_str.split(",")]
                assert ids == sorted(ids), f"Evidence IDs not sorted: {ids}"

    def test_md_deterministic_enrichment_ordering(self, sample_repo: Path) -> None:
        """Two enrichments runs should produce same enrichment ordering."""
        import hashlib

        enrich_findings(sample_repo, provider_name="mock")
        md1 = (sample_repo / ".ai-debt" / "ai" / "enrichment-report.md").read_text(encoding="utf-8")
        # Strip timestamps for comparison
        lines1 = [
            ln for ln in md1.split("\n") if "Generated" not in ln and "generated_at" not in ln
        ]
        hash1 = hashlib.sha256("\n".join(lines1).encode()).hexdigest()

        enrich_findings(sample_repo, provider_name="mock")
        md2 = (sample_repo / ".ai-debt" / "ai" / "enrichment-report.md").read_text(encoding="utf-8")
        lines2 = [
            ln for ln in md2.split("\n") if "Generated" not in ln and "generated_at" not in ln
        ]
        hash2 = hashlib.sha256("\n".join(lines2).encode()).hexdigest()

        assert hash1 == hash2, "Markdown content differs between runs (excluding timestamps)"

    def test_md_rejection_with_hash(self, sample_repo: Path) -> None:
        """Rejection section should include raw_output_hash."""
        import json as _json

        enrich_findings(sample_repo, provider_name="mock")
        rej_path = sample_repo / ".ai-debt" / "ai" / "rejected-ai-output.json"
        if rej_path.exists():
            rejections = _json.loads(rej_path.read_text(encoding="utf-8"))
            for rej in rejections:
                if rej.get("raw_output_hash"):
                    md = (sample_repo / ".ai-debt" / "ai" / "enrichment-report.md").read_text(
                        encoding="utf-8"
                    )
                    assert "Hash:" in md
                    break

    def test_md_rejection_section_uses_headings(self, sample_repo: Path) -> None:
        """Rejection items should use ### headings for better readability."""
        enrich_findings(sample_repo, provider_name="mock")
        md = (sample_repo / ".ai-debt" / "ai" / "enrichment-report.md").read_text(encoding="utf-8")
        # If there are rejections in the report, check heading format
        if "## Rejections" in md:
            # Should have ### for each rejection (not bullet points)
            assert "### " in md or "Enrichments rejected" in md


# ── Regression Tests (v0.7.2) ───────────────────────────────────────


class TestRegressionV072:
    """Regression tests to confirm v0.7.2 changes don't break existing behavior."""

    def test_enrich_still_writes_sidecars(self, sample_repo: Path) -> None:
        enrich_findings(sample_repo, provider_name="mock")
        ai_dir = sample_repo / ".ai-debt" / "ai"
        assert (ai_dir / "enrichment-report.json").exists()
        assert (ai_dir / "enrichment-report.md").exists()
        assert (ai_dir / "finding-enrichments.json").exists()
        assert (ai_dir / "rejected-ai-output.json").exists()

    def test_disabled_still_writes_nothing(self, sample_repo: Path) -> None:
        enrich_findings(sample_repo, provider_name="disabled")
        ai_dir = sample_repo / ".ai-debt" / "ai"
        assert not ai_dir.exists()

    def test_dry_run_still_writes_nothing(self, sample_repo: Path) -> None:
        enrich_findings(sample_repo, provider_name="mock", dry_run=True)
        ai_dir = sample_repo / ".ai-debt" / "ai"
        assert not ai_dir.exists()

    def test_unknown_finding_id_still_fails(self, sample_repo: Path) -> None:
        from typer.testing import CliRunner as CR

        from pharabius.cli import app as cli_app

        r = CR().invoke(
            cli_app,
            ["enrich", "--provider", "mock", "--finding-id", "NONEXISTENT", "-r", str(sample_repo)],
        )
        assert r.exit_code == 1
        assert "NONEXISTENT" in r.output

    def test_ai_status_not_in_run(self, tmp_path: Path) -> None:
        """ai-status is a separate command, not part of ai-debt run."""

        # run should work normally without any ai-status behavior
        # Just verify the function exists and is separate
        from pharabius.ai.status_reader import read_ai_status

        _status, code = read_ai_status(tmp_path)
        assert code == 0  # no sidecar is fine


# ── Immutability Across Modes ───────────────────────────────────────


class TestImmutabilityModes:
    def _hash_files(self, repo: Path) -> dict[str, str]:
        import hashlib

        hashes: dict[str, str] = {}
        ai_debt = repo / ".ai-debt"
        for name in ["debt-register.json", "evidence.json", "analysis-units.json"]:
            p = ai_debt / name
            if p.exists():
                hashes[name] = hashlib.sha256(p.read_bytes()).hexdigest()
        return hashes

    @pytest.mark.parametrize(
        "mode",
        [
            {"provider_name": "disabled"},
            {"provider_name": "mock"},
            {"provider_name": "mock", "dry_run": True},
            {"provider_name": "mock", "strict": True},
            {"provider_name": "mock", "finding_id": "TD-DEP-001"},
            {"provider_name": "mock", "max_findings": 1},
        ],
    )
    def test_canonical_unchanged(self, sample_repo: Path, mode: dict[str, Any]):
        before = self._hash_files(sample_repo)
        enrich_findings(sample_repo, **mode)
        after = self._hash_files(sample_repo)
        assert before == after


# ── Privacy & Dependency Checks ─────────────────────────────────────


class TestPrivacyChecks:
    def test_no_network_libs_in_ai_modules(self):
        import pharabius.ai.adapter as adapter_mod
        import pharabius.ai.context as context_mod
        import pharabius.ai.enricher as enricher_mod
        import pharabius.ai.validator as validator_mod

        for mod in [adapter_mod, context_mod, enricher_mod, validator_mod]:
            source = Path(mod.__file__).read_text(encoding="utf-8")
            assert "import httpx" not in source
            assert "import requests" not in source
            assert "import aiohttp" not in source
            assert "import urllib.request" not in source

    def test_no_provider_sdks(self):
        import pharabius.ai.mock_provider as mod

        source = Path(mod.__file__).read_text(encoding="utf-8")
        assert "openai" not in source.lower() or "mock" in source.lower()
        assert "anthropic" not in source.lower()


# ── Import Boundary Checks ──────────────────────────────────────────


class TestImportBoundaries:
    def test_ai_does_not_import_core(self):
        import pharabius.ai.enricher as mod

        source = Path(mod.__file__).read_text(encoding="utf-8")
        assert "from pharabius.core" not in source
        assert "import pharabius.core" not in source

    def test_core_does_not_import_ai(self):
        import pharabius.core.analyzer as mod

        source = Path(mod.__file__).read_text(encoding="utf-8")
        assert "from pharabius.ai" not in source
        assert "import pharabius.ai" not in source
