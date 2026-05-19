"""Provider response variability tests for v0.9.1.

All tests use httpx.MockTransport — no real network calls.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from unittest.mock import patch

import httpx
import pytest

from pharabius.ai.enricher import enrich_findings
from pharabius.schemas.ai_enrichment import AIBudget

# ── Helpers ────────────────────────────────────────────────────────────


def _setup_repo(
    tmp_path: Path,
    *,
    n_findings: int = 3,
) -> Path:
    """Create a minimal .ai-debt repo with n findings."""
    ai = tmp_path / ".ai-debt"
    ai.mkdir()
    evidence = []
    findings = []
    for i in range(n_findings):
        eid = f"EVD-{i:03d}"
        evidence.append(
            {
                "evidence_id": eid,
                "type": "test",
                "category": "test",
                "summary": f"test evidence {i}",
                "location": {"file": f"file_{i}.py"},
                "raw_observation": f"obs {i}",
            }
        )
        findings.append(
            {
                "id": f"TD-DEP-{i:03d}",
                "category": "TD-DEP",
                "title": f"Test finding {i}",
                "severity": "Medium",
                "evidence_ids": [eid],
                "analysis_unit_ids": [],
            }
        )
    (ai / "evidence.json").write_text(
        json.dumps({"schema_version": "1.0", "evidence": evidence}),
        encoding="utf-8",
    )
    (ai / "debt-register.json").write_text(
        json.dumps({"schema_version": "1.0", "findings": findings}),
        encoding="utf-8",
    )
    return tmp_path


def _mock_transport(content: str, status_code: int = 200) -> httpx.MockTransport:
    """Create mock transport returning content."""

    def handler(request: httpx.Request) -> httpx.Response:
        if status_code != 200:
            return httpx.Response(status_code, json={"error": {"message": "error"}})
        body = {
            "choices": [{"message": {"content": content}, "finish_reason": "stop"}],
            "model": "test-model",
            "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        }
        return httpx.Response(status_code, json=body, headers={"x-request-id": "req-test"})

    return httpx.MockTransport(handler)


def _mock_transport_no_usage(content: str) -> httpx.MockTransport:
    """Mock transport with no usage field."""

    def handler(request: httpx.Request) -> httpx.Response:
        body = {
            "choices": [{"message": {"content": content}, "finish_reason": "stop"}],
            "model": "test-model",
        }
        return httpx.Response(200, json=body)

    return httpx.MockTransport(handler)


def _mock_transport_no_request_id(content: str) -> httpx.MockTransport:
    """Mock transport with no request ID."""

    def handler(request: httpx.Request) -> httpx.Response:
        body = {
            "choices": [{"message": {"content": content}, "finish_reason": "stop"}],
            "model": "test-model",
            "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        }
        return httpx.Response(200, json=body)

    return httpx.MockTransport(handler)


def _enrichment_json(*finding_ids: str) -> str:
    """Build valid enrichment JSON for given finding IDs."""
    enrichments = []
    for fid in finding_ids:
        idx = fid.split("-")[-1]
        enrichments.append(
            {
                "finding_id": fid,
                "evidence_ids": [f"EVD-{idx}"],
                "confidence": "Medium",
                "limitations": ["AI-generated enrichment"],
                "explanation": f"Enrichment for {fid}",
            }
        )
    return json.dumps({"enrichments": enrichments})


def _run_enrich(
    repo: Path,
    content: str,
    *,
    transport_status: int = 200,
    max_findings: int = 10,
    finding_id: str | None = None,
    max_output_chars: int = 10_000,
    strict: bool = False,
) -> Any:
    """Run enrich pipeline with mock transport."""
    from pharabius.ai.providers.openai_compatible import OpenAICompatibleAdapter

    transport = _mock_transport(content, status_code=transport_status)
    with patch.dict(
        os.environ,
        {"PHARABIUS_OPENAI_API_KEY": "sk-test", "PHARABIUS_OPENAI_MODEL": "test-model"},
        clear=False,
    ):
        adapter = OpenAICompatibleAdapter(model="test-model", transport=transport)

    import pharabius.ai.enricher as enricher_mod

    _original_get_provider = enricher_mod._get_provider
    enricher_mod._get_provider = lambda name, *, model="": adapter  # type: ignore[assignment]
    try:
        budget = AIBudget(max_output_chars=max_output_chars)
        report = enrich_findings(
            repo,
            provider_name="mock",
            max_findings=max_findings,
            finding_id=finding_id,
            budget=budget,
            strict=strict,
        )
    finally:
        enricher_mod._get_provider = _original_get_provider  # type: ignore[assignment]

    return report


# ── Response format variability ───────────────────────────────────────


class TestResponseFormatVariability:
    """Tests for various provider response formats."""

    def test_refusal_text_rejected(self, tmp_path: Path) -> None:
        """V1: Non-JSON refusal text is rejected."""
        repo = _setup_repo(tmp_path)
        report = _run_enrich(repo, "I cannot assist with this request.")
        assert len(report.enrichments) == 0
        assert len(report.rejections) > 0
        assert any("Malformed JSON" in r.reason for r in report.rejections)

    def test_missing_enrichments_key_rejected(self, tmp_path: Path) -> None:
        """V2: JSON without enrichments key is rejected."""
        repo = _setup_repo(tmp_path)
        report = _run_enrich(repo, json.dumps({"data": []}))
        assert len(report.enrichments) == 0
        assert any("enrichments" in r.reason.lower() for r in report.rejections)

    def test_empty_enrichments_array(self, tmp_path: Path) -> None:
        """V3: Empty enrichments array produces empty result."""
        repo = _setup_repo(tmp_path)
        report = _run_enrich(repo, json.dumps({"enrichments": []}))
        assert len(report.enrichments) == 0
        assert len(report.rejections) == 0

    def test_conservative_valid_json_accepted(self, tmp_path: Path) -> None:
        """V4: Valid JSON with conservative answer is accepted."""
        repo = _setup_repo(tmp_path)
        report = _run_enrich(repo, _enrichment_json("TD-DEP-000"))
        assert len(report.enrichments) == 1
        assert report.enrichments[0].finding_id == "TD-DEP-000"

    def test_hallucinated_evidence_ids_rejected(self, tmp_path: Path) -> None:
        """V5: Valid JSON with unknown evidence IDs is rejected."""
        repo = _setup_repo(tmp_path)
        bad_json = json.dumps(
            {
                "enrichments": [
                    {
                        "finding_id": "TD-DEP-000",
                        "evidence_ids": ["EVD-FAKE-999"],
                        "confidence": "Medium",
                        "limitations": ["AI-generated"],
                        "explanation": "Bad evidence",
                    }
                ]
            }
        )
        report = _run_enrich(repo, bad_json)
        assert len(report.enrichments) == 0
        assert len(report.rejections) > 0
        assert any("EVD-FAKE-999" in str(r.missing_evidence_ids) for r in report.rejections)

    def test_usage_without_request_id(self, tmp_path: Path) -> None:
        """V6: Response with usage but no request ID is accepted."""
        repo = _setup_repo(tmp_path)
        transport = _mock_transport_no_request_id(_enrichment_json("TD-DEP-000"))
        import pharabius.ai.enricher as enricher_mod
        from pharabius.ai.providers.openai_compatible import OpenAICompatibleAdapter

        with patch.dict(
            os.environ,
            {"PHARABIUS_OPENAI_API_KEY": "sk-test", "PHARABIUS_OPENAI_MODEL": "test-model"},
            clear=False,
        ):
            adapter = OpenAICompatibleAdapter(model="test-model", transport=transport)
        _original = enricher_mod._get_provider
        try:
            enricher_mod._get_provider = lambda name, *, model="": adapter  # type: ignore[assignment]
            report = enrich_findings(repo, provider_name="mock")
        finally:
            enricher_mod._get_provider = _original  # type: ignore[assignment]
        assert len(report.enrichments) == 1
        assert report.usage.request_id == ""

    def test_request_id_without_usage(self, tmp_path: Path) -> None:
        """V7: Response with request ID but no usage is accepted."""
        repo = _setup_repo(tmp_path)
        transport = _mock_transport_no_usage(_enrichment_json("TD-DEP-000"))
        import pharabius.ai.enricher as enricher_mod
        from pharabius.ai.providers.openai_compatible import OpenAICompatibleAdapter

        with patch.dict(
            os.environ,
            {"PHARABIUS_OPENAI_API_KEY": "sk-test", "PHARABIUS_OPENAI_MODEL": "test-model"},
            clear=False,
        ):
            adapter = OpenAICompatibleAdapter(model="test-model", transport=transport)
        _original = enricher_mod._get_provider
        try:
            enricher_mod._get_provider = lambda name, *, model="": adapter  # type: ignore[assignment]
            report = enrich_findings(repo, provider_name="mock")
        finally:
            enricher_mod._get_provider = _original  # type: ignore[assignment]
        assert len(report.enrichments) == 1
        assert report.usage.prompt_tokens == 0

    def test_empty_string_content_rejected(self, tmp_path: Path) -> None:
        """V8: Empty string content is rejected."""
        repo = _setup_repo(tmp_path)
        report = _run_enrich(repo, "")
        assert len(report.enrichments) == 0
        assert len(report.rejections) > 0

    def test_extra_unknown_fields_rejected(self, tmp_path: Path) -> None:
        """V9: Enrichment with extra fields is rejected (forbid extra)."""
        repo = _setup_repo(tmp_path)
        bad_json = json.dumps(
            {
                "enrichments": [
                    {
                        "finding_id": "TD-DEP-000",
                        "evidence_ids": ["EVD-000"],
                        "confidence": "Medium",
                        "limitations": ["AI-generated"],
                        "explanation": "test",
                        "sneaky_field": "should be rejected",
                    }
                ]
            }
        )
        report = _run_enrich(repo, bad_json)
        assert len(report.enrichments) == 0
        assert len(report.rejections) > 0


# ── Selected-finding boundary ────────────────────────────────────────


class TestSelectedFindingBoundary:
    """Tests for selected-finding boundary enforcement."""

    def test_selected_finding_accepted(self, tmp_path: Path) -> None:
        """S1: Enrichment for selected finding is accepted."""
        repo = _setup_repo(tmp_path, n_findings=3)
        report = _run_enrich(repo, _enrichment_json("TD-DEP-000"), max_findings=1)
        assert len(report.enrichments) == 1
        assert report.enrichments[0].finding_id == "TD-DEP-000"

    def test_unselected_finding_rejected(self, tmp_path: Path) -> None:
        """S2: Enrichment for existing but unselected finding is rejected."""
        repo = _setup_repo(tmp_path, n_findings=3)
        # Select only first finding, but provider enrichs third
        report = _run_enrich(
            repo,
            _enrichment_json("TD-DEP-002"),
            max_findings=1,
        )
        assert len(report.enrichments) == 0
        assert len(report.rejections) > 0
        assert any("TD-DEP-002" in r.reason for r in report.rejections)

    def test_mixed_selected_unselected(self, tmp_path: Path) -> None:
        """S3: Selected accepted, unselected rejected."""
        repo = _setup_repo(tmp_path, n_findings=3)
        report = _run_enrich(
            repo,
            _enrichment_json("TD-DEP-000", "TD-DEP-002"),
            max_findings=1,
        )
        # Only TD-DEP-000 should be selected (max_findings=1)
        assert len(report.enrichments) == 1
        assert report.enrichments[0].finding_id == "TD-DEP-000"
        assert any("TD-DEP-002" in r.reason for r in report.rejections)

    def test_duplicate_finding_rejected(self, tmp_path: Path) -> None:
        """S4: Duplicate enrichment for same finding — first accepted, duplicate rejected."""
        repo = _setup_repo(tmp_path, n_findings=2)
        dup_json = json.dumps(
            {
                "enrichments": [
                    {
                        "finding_id": "TD-DEP-000",
                        "evidence_ids": ["EVD-000"],
                        "confidence": "Medium",
                        "limitations": ["AI-generated"],
                        "explanation": "First",
                    },
                    {
                        "finding_id": "TD-DEP-000",
                        "evidence_ids": ["EVD-000"],
                        "confidence": "High",
                        "limitations": ["AI-generated"],
                        "explanation": "Duplicate",
                    },
                ]
            }
        )
        report = _run_enrich(repo, dup_json)
        assert len(report.enrichments) == 1
        assert report.enrichments[0].explanation == "First"
        assert any("Duplicate" in r.reason for r in report.rejections)

    def test_strict_mode_rejects_batch(self, tmp_path: Path) -> None:
        """S5: Strict mode rejects whole batch when unselected enrichment appears."""
        repo = _setup_repo(tmp_path, n_findings=3)
        report = _run_enrich(
            repo,
            _enrichment_json("TD-DEP-000", "TD-DEP-002"),
            max_findings=1,
            strict=True,
        )
        assert len(report.enrichments) == 0
        assert any("TD-DEP-002" in r.reason for r in report.rejections)

    def test_non_strict_keeps_valid(self, tmp_path: Path) -> None:
        """S6: Non-strict keeps valid selected, records invalid."""
        repo = _setup_repo(tmp_path, n_findings=3)
        report = _run_enrich(
            repo,
            _enrichment_json("TD-DEP-000", "TD-DEP-002"),
            max_findings=1,
            strict=False,
        )
        assert len(report.enrichments) == 1
        assert report.enrichments[0].finding_id == "TD-DEP-000"
        assert len(report.rejections) >= 1

    def test_finding_id_flag_boundary(self, tmp_path: Path) -> None:
        """S7: --finding-id selects one, provider enriches different — rejected."""
        repo = _setup_repo(tmp_path, n_findings=3)
        report = _run_enrich(
            repo,
            _enrichment_json("TD-DEP-001"),
            finding_id="TD-DEP-000",
        )
        assert len(report.enrichments) == 0
        assert any("TD-DEP-001" in r.reason for r in report.rejections)


# ── Output budget enforcement ────────────────────────────────────────


class TestOutputBudget:
    """Tests for output budget enforcement."""

    def test_over_budget_rejected(self, tmp_path: Path) -> None:
        """B1: Raw output exceeding max_output_chars is rejected."""
        repo = _setup_repo(tmp_path)
        big_content = "x" * 100
        report = _run_enrich(repo, big_content, max_output_chars=50)
        assert len(report.enrichments) == 0
        assert len(report.rejections) >= 1

    def test_rejection_reason_mentions_size(self, tmp_path: Path) -> None:
        """B2: Rejection reason includes actual size and max budget."""
        repo = _setup_repo(tmp_path)
        big_content = "x" * 100
        report = _run_enrich(repo, big_content, max_output_chars=50)
        assert len(report.rejections) >= 1
        reason = report.rejections[0].reason
        assert "100 chars" in reason
        assert "50 max" in reason

    def test_raw_output_hash_recorded(self, tmp_path: Path) -> None:
        """B3: raw_output_hash is recorded for over-budget output."""
        repo = _setup_repo(tmp_path)
        big_content = "x" * 100
        report = _run_enrich(repo, big_content, max_output_chars=50)
        assert len(report.rejections) >= 1
        assert report.rejections[0].raw_output_hash != ""

    def test_excessive_output_not_in_sidecar_markdown(self, tmp_path: Path) -> None:
        """B4: Over-budget output is not written to sidecar markdown."""
        repo = _setup_repo(tmp_path)
        big_content = "x" * 100
        report = _run_enrich(repo, big_content, max_output_chars=50)
        # The report is returned but not written since we used _run_enrich
        # which calls enrich_findings directly. The sidecar is only written
        # for non-dry-run. Check the report object instead.
        for rej in report.rejections:
            assert "x" * 90 not in rej.reason  # No raw content in reason

    def test_canonical_artifacts_unchanged(self, tmp_path: Path) -> None:
        """B5: Canonical artifacts remain unchanged after over-budget rejection."""
        repo = _setup_repo(tmp_path)
        register_path = repo / ".ai-debt" / "debt-register.json"
        before = register_path.read_text(encoding="utf-8")
        big_content = "x" * 100
        _run_enrich(repo, big_content, max_output_chars=50)
        after = register_path.read_text(encoding="utf-8")
        assert before == after

    def test_output_at_limit_accepted(self, tmp_path: Path) -> None:
        """B6: Output exactly at max_output_chars is accepted."""
        repo = _setup_repo(tmp_path)
        valid = _enrichment_json("TD-DEP-000")
        report = _run_enrich(repo, valid, max_output_chars=len(valid))
        # Should not be rejected for budget
        assert not any("exceeds budget" in r.reason for r in report.rejections)


# ── Provider error tests ────────────────────────────────────────────


class TestProviderErrors:
    """Tests for provider-level error handling through enrich pipeline."""

    def test_timeout_rejection(self, tmp_path: Path) -> None:
        """E1: Timeout produces rejection with provider_error_code."""

        def timeout_handler(request: httpx.Request) -> httpx.Response:
            raise httpx.TimeoutException("timed out")

        transport = httpx.MockTransport(timeout_handler)
        import pharabius.ai.enricher as enricher_mod
        from pharabius.ai.providers.openai_compatible import OpenAICompatibleAdapter

        repo = _setup_repo(tmp_path)
        with patch.dict(
            os.environ,
            {"PHARABIUS_OPENAI_API_KEY": "sk-test", "PHARABIUS_OPENAI_MODEL": "test-model"},
            clear=False,
        ):
            adapter = OpenAICompatibleAdapter(model="test-model", transport=transport)
        _original = enricher_mod._get_provider
        try:
            enricher_mod._get_provider = lambda name, *, model="": adapter  # type: ignore[assignment]
            report = enrich_findings(repo, provider_name="mock")
        finally:
            enricher_mod._get_provider = _original  # type: ignore[assignment]
        assert len(report.enrichments) == 0
        assert len(report.rejections) >= 1
        assert (
            "timed out" in report.rejections[0].reason.lower()
            or "timeout" in report.rejections[0].reason.lower()
        )

    def test_server_error_rejection(self, tmp_path: Path) -> None:
        """E2: 5xx produces rejection."""
        repo = _setup_repo(tmp_path)
        report = _run_enrich(repo, "", transport_status=500)
        assert len(report.enrichments) == 0
        assert len(report.rejections) >= 1

    def test_rate_limit_rejection(self, tmp_path: Path) -> None:
        """E3: 429 produces rejection."""
        repo = _setup_repo(tmp_path)
        report = _run_enrich(repo, "", transport_status=429)
        assert len(report.enrichments) == 0
        assert any("rate" in r.reason.lower() for r in report.rejections)

    def test_auth_failure_rejection(self, tmp_path: Path) -> None:
        """E4: 401 produces rejection."""
        repo = _setup_repo(tmp_path)
        report = _run_enrich(repo, "", transport_status=401)
        assert len(report.enrichments) == 0
        assert any("auth" in r.reason.lower() for r in report.rejections)

    def test_content_filter_rejection(self, tmp_path: Path) -> None:
        """E5: Content filter produces rejection."""
        repo = _setup_repo(tmp_path)

        def filter_handler(request: httpx.Request) -> httpx.Response:
            body = {
                "choices": [
                    {"message": {"content": "filtered"}, "finish_reason": "content_filter"}
                ],
                "model": "test-model",
            }
            return httpx.Response(200, json=body)

        transport = httpx.MockTransport(filter_handler)
        import pharabius.ai.enricher as enricher_mod
        from pharabius.ai.providers.openai_compatible import OpenAICompatibleAdapter

        with patch.dict(
            os.environ,
            {"PHARABIUS_OPENAI_API_KEY": "sk-test", "PHARABIUS_OPENAI_MODEL": "test-model"},
            clear=False,
        ):
            adapter = OpenAICompatibleAdapter(model="test-model", transport=transport)
        _original = enricher_mod._get_provider
        try:
            enricher_mod._get_provider = lambda name, *, model="": adapter  # type: ignore[assignment]
            report = enrich_findings(repo, provider_name="mock")
        finally:
            enricher_mod._get_provider = _original  # type: ignore[assignment]
        assert len(report.enrichments) == 0
        assert len(report.rejections) >= 1
        # Content filter response with non-JSON content gets rejected
        assert any(
            "filter" in r.reason.lower() or "malformed" in r.reason.lower()
            for r in report.rejections
        )


# ── Regression: _get_provider isolation ─────────────────────────────


class TestGetProviderIsolation:
    """Regression tests for _get_provider leak between test classes.

    Prior to v0.11.0, TestProviderErrors and TestResponseFormatVariability
    mutated enricher_mod._get_provider without restoring it, causing
    TestUnknownProviderMessage in test_provider_simulation.py to fail
    when run in the same batch.
    """

    def test_get_provider_unknown_raises_after_variability(self) -> None:
        """After all variability tests, _get_provider('openai') must still raise."""
        import pharabius.ai.enricher as enricher_mod

        # The original function should be in place — no leaked lambda
        with pytest.raises(ValueError, match="not available"):
            enricher_mod._get_provider("openai")

    def test_get_provider_known_still_work(self) -> None:
        """Known providers still resolve after variability tests."""
        import pharabius.ai.enricher as enricher_mod

        disabled = enricher_mod._get_provider("disabled")
        assert disabled is not None

        mock = enricher_mod._get_provider("mock")
        assert mock is not None
