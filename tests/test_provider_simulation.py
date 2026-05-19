"""Provider simulation tests for v0.8.0.

Tests provider failure modes using a SimulatedProvider test helper.
No real providers, no network calls, no credentials.
"""

import json
from typing import Any

from pharabius.ai.adapter import AIAdapter, AIResponse
from pharabius.ai.enricher import enrich_findings
from pharabius.schemas.ai_enrichment import AIUsageSummary

# ── Simulated provider ────────────────────────────────────────────────


class SimulatedProvider(AIAdapter):
    """Test-only provider that can be configured to simulate failure modes."""

    def __init__(
        self,
        *,
        raw_text: str = "",
        error_code: str = "",
        error_message: str = "",
        finish_reason: str = "complete",
        truncated: bool = False,
        latency_ms: int = 100,
    ) -> None:
        self._raw_text = raw_text
        self._error_code = error_code
        self._error_message = error_message
        self._finish_reason = finish_reason
        self._truncated = truncated
        self._latency_ms = latency_ms

    @property
    def name(self) -> str:
        return "simulated"

    @property
    def model(self) -> str:
        return "simulated-v0.8.0"

    def generate_json(
        self,
        prompt: str,
        context: dict[str, Any],
        schema_hint: dict[str, Any] | None = None,
        *,
        timeout_seconds: int = 30,
    ) -> AIResponse:
        errors: list[str] = []
        if self._error_message:
            errors.append(self._error_message)

        return AIResponse(
            provider=self.name,
            model=self.model,
            raw_text=self._raw_text,
            parsed_json=None,
            usage=AIUsageSummary(
                provider=self.name,
                model=self.model,
                prompt_chars=len(prompt),
                response_chars=len(self._raw_text),
            ),
            finish_reason=self._finish_reason,
            errors=errors,
            latency_ms=self._latency_ms,
            response_truncated=self._truncated,
            provider_error_code=self._error_code,
            provider_error_message=self._error_message,
        )


# ── Helpers ────────────────────────────────────────────────────────────


def _make_repo(
    tmp: Any,
    *,
    n_findings: int = 2,
    evidence_per_finding: int = 1,
) -> Any:
    """Create a minimal repo with evidence and findings."""
    import tempfile
    from pathlib import Path

    tmp_path = Path(tempfile.mkdtemp())
    ai = tmp_path / ".ai-debt"
    ai.mkdir()

    ev_list = []
    for i in range(n_findings):
        for j in range(evidence_per_finding):
            ev_list.append(
                {
                    "evidence_id": f"EVD-{i:03d}-{j:03d}",
                    "type": "test",
                    "location": {"file": f"a{i}.py"},
                    "raw_observation": f"obs {i}-{j}",
                }
            )

    (ai / "evidence.json").write_text(
        json.dumps({"schema_version": "1.0", "evidence": ev_list}), encoding="utf-8"
    )

    findings = [
        {
            "id": f"TD-DEP-{i:03d}",
            "category": "TD-DEP",
            "title": f"Test finding {i}",
            "severity": "Medium",
            "evidence_ids": [f"EVD-{i:03d}-{j:03d}" for j in range(evidence_per_finding)],
            "analysis_unit_ids": [],
        }
        for i in range(n_findings)
    ]

    (ai / "debt-register.json").write_text(
        json.dumps({"schema_version": "1.0", "findings": findings}), encoding="utf-8"
    )

    return tmp_path


def _valid_enrichment_json(n_findings: int = 2) -> str:
    """Return valid enrichment JSON for n findings."""
    enrichments = []
    for i in range(n_findings):
        enrichments.append(
            {
                "finding_id": f"TD-DEP-{i:03d}",
                "evidence_ids": [f"EVD-{i:03d}-000"],
                "confidence": "Medium",
                "limitations": ["AI-generated enrichment"],
                "explanation": f"Test enrichment for finding {i}",
            }
        )
    return json.dumps({"enrichments": enrichments})


# ── Provider simulation tests ──────────────────────────────────────────


class TestProviderSimulation:
    """Tests simulating provider failure modes via SimulatedProvider."""

    def test_valid_output_accepted(self, tmp_path: Any) -> None:
        """Valid provider output should be accepted."""
        repo = _make_repo(tmp_path)
        provider = SimulatedProvider(raw_text=_valid_enrichment_json(2))

        # Monkey-patch _get_provider to return our simulated provider
        import pharabius.ai.enricher as enricher_mod

        original = enricher_mod._get_provider
        enricher_mod._get_provider = lambda name: provider
        try:
            report = enrich_findings(repo, provider_name="simulated")
        finally:
            enricher_mod._get_provider = original

        assert len(report.enrichments) == 2
        assert len(report.rejections) == 0

    def test_timeout_provider_error(self, tmp_path: Any) -> None:
        """Provider timeout should produce rejection record."""
        repo = _make_repo(tmp_path)
        provider = SimulatedProvider(
            raw_text="",
            error_code="timeout",
            error_message="Provider request timed out after 30 seconds",
            finish_reason="timeout",
        )

        import pharabius.ai.enricher as enricher_mod

        original = enricher_mod._get_provider
        enricher_mod._get_provider = lambda name: provider
        try:
            report = enrich_findings(repo, provider_name="simulated")
        finally:
            enricher_mod._get_provider = original

        assert len(report.enrichments) == 0
        assert len(report.rejections) >= 1
        assert "timed out" in report.rejections[0].reason.lower()

    def test_rate_limit_provider_error(self, tmp_path: Any) -> None:
        """Provider rate-limit should produce rejection record."""
        repo = _make_repo(tmp_path)
        provider = SimulatedProvider(
            raw_text="",
            error_code="rate_limit",
            error_message="Rate limit exceeded. Please retry later.",
            finish_reason="rate_limit",
        )

        import pharabius.ai.enricher as enricher_mod

        original = enricher_mod._get_provider
        enricher_mod._get_provider = lambda name: provider
        try:
            report = enrich_findings(repo, provider_name="simulated")
        finally:
            enricher_mod._get_provider = original

        assert len(report.enrichments) == 0
        assert any("rate" in r.reason.lower() for r in report.rejections)

    def test_auth_provider_error(self, tmp_path: Any) -> None:
        """Provider auth failure should produce rejection record."""
        repo = _make_repo(tmp_path)
        provider = SimulatedProvider(
            raw_text="",
            error_code="auth_failed",
            error_message="Authentication failed. Check API credentials.",
            finish_reason="auth_failed",
        )

        import pharabius.ai.enricher as enricher_mod

        original = enricher_mod._get_provider
        enricher_mod._get_provider = lambda name: provider
        try:
            report = enrich_findings(repo, provider_name="simulated")
        finally:
            enricher_mod._get_provider = original

        assert len(report.enrichments) == 0
        assert any("auth" in r.reason.lower() for r in report.rejections)

    def test_malformed_json_rejected(self, tmp_path: Any) -> None:
        """Malformed JSON from provider should be rejected."""
        repo = _make_repo(tmp_path)
        provider = SimulatedProvider(raw_text="not json {{{")

        import pharabius.ai.enricher as enricher_mod

        original = enricher_mod._get_provider
        enricher_mod._get_provider = lambda name: provider
        try:
            report = enrich_findings(repo, provider_name="simulated")
        finally:
            enricher_mod._get_provider = original

        assert len(report.enrichments) == 0
        assert len(report.rejections) >= 1

    def test_markdown_fenced_json_rejected(self, tmp_path: Any) -> None:
        """Markdown-wrapped JSON should be rejected."""
        valid = _valid_enrichment_json(1)
        fenced = f"```json\n{valid}\n```"
        repo = _make_repo(tmp_path)
        provider = SimulatedProvider(raw_text=fenced)

        import pharabius.ai.enricher as enricher_mod

        original = enricher_mod._get_provider
        enricher_mod._get_provider = lambda name: provider
        try:
            report = enrich_findings(repo, provider_name="simulated")
        finally:
            enricher_mod._get_provider = original

        assert len(report.enrichments) == 0
        assert len(report.rejections) >= 1

    def test_partial_json_rejected(self, tmp_path: Any) -> None:
        """Partial/truncated JSON should be rejected."""
        valid = _valid_enrichment_json(1)
        partial = valid[: len(valid) // 2]  # Cut in half
        repo = _make_repo(tmp_path)
        provider = SimulatedProvider(raw_text=partial, truncated=True)

        import pharabius.ai.enricher as enricher_mod

        original = enricher_mod._get_provider
        enricher_mod._get_provider = lambda name: provider
        try:
            report = enrich_findings(repo, provider_name="simulated")
        finally:
            enricher_mod._get_provider = original

        assert len(report.enrichments) == 0
        assert len(report.rejections) >= 1

    def test_json_with_comments_rejected(self, tmp_path: Any) -> None:
        """JSON with comments should be rejected."""
        valid = _valid_enrichment_json(1)
        commented = f"// this is a comment\n{valid}"
        repo = _make_repo(tmp_path)
        provider = SimulatedProvider(raw_text=commented)

        import pharabius.ai.enricher as enricher_mod

        original = enricher_mod._get_provider
        enricher_mod._get_provider = lambda name: provider
        try:
            report = enrich_findings(repo, provider_name="simulated")
        finally:
            enricher_mod._get_provider = original

        assert len(report.enrichments) == 0
        assert len(report.rejections) >= 1

    def test_content_filter_refusal(self, tmp_path: Any) -> None:
        """Content filter/safety refusal should produce rejection record."""
        repo = _make_repo(tmp_path)
        provider = SimulatedProvider(
            raw_text="",
            error_code="content_filter",
            error_message="Content filtered by provider safety system",
            finish_reason="content_filter",
        )

        import pharabius.ai.enricher as enricher_mod

        original = enricher_mod._get_provider
        enricher_mod._get_provider = lambda name: provider
        try:
            report = enrich_findings(repo, provider_name="simulated")
        finally:
            enricher_mod._get_provider = original

        assert len(report.enrichments) == 0
        assert any("content" in r.reason.lower() for r in report.rejections)

    def test_truncated_output_rejected(self, tmp_path: Any) -> None:
        """Truncated output should be rejected."""
        valid = _valid_enrichment_json(1)
        # Remove the closing bracket to simulate truncation
        truncated = valid[:-5]
        repo = _make_repo(tmp_path)
        provider = SimulatedProvider(raw_text=truncated, truncated=True)

        import pharabius.ai.enricher as enricher_mod

        original = enricher_mod._get_provider
        enricher_mod._get_provider = lambda name: provider
        try:
            report = enrich_findings(repo, provider_name="simulated")
        finally:
            enricher_mod._get_provider = original

        assert len(report.enrichments) == 0
        assert len(report.rejections) >= 1

    def test_empty_response_rejected(self, tmp_path: Any) -> None:
        """Empty response should produce rejection record."""
        repo = _make_repo(tmp_path)
        provider = SimulatedProvider(raw_text="")

        import pharabius.ai.enricher as enricher_mod

        original = enricher_mod._get_provider
        enricher_mod._get_provider = lambda name: provider
        try:
            report = enrich_findings(repo, provider_name="simulated")
        finally:
            enricher_mod._get_provider = original

        assert len(report.enrichments) == 0
        assert len(report.rejections) >= 1

    def test_mixed_valid_invalid_batch(self, tmp_path: Any) -> None:
        """Mixed valid/invalid enrichments should keep valid and reject invalid."""
        mixed = json.dumps(
            {
                "enrichments": [
                    {
                        "finding_id": "TD-DEP-000",
                        "evidence_ids": ["EVD-000-000"],
                        "confidence": "Medium",
                        "limitations": ["AI-generated enrichment"],
                    },
                    {
                        "finding_id": "FAKE-999",
                        "evidence_ids": ["EVD-NONEXISTENT"],
                        "confidence": "Medium",
                        "limitations": ["AI-generated enrichment"],
                    },
                ]
            }
        )
        repo = _make_repo(tmp_path, n_findings=1)
        provider = SimulatedProvider(raw_text=mixed)

        import pharabius.ai.enricher as enricher_mod

        original = enricher_mod._get_provider
        enricher_mod._get_provider = lambda name: provider
        try:
            report = enrich_findings(repo, provider_name="simulated")
        finally:
            enricher_mod._get_provider = original

        assert len(report.enrichments) == 1
        assert len(report.rejections) == 1
        assert report.enrichments[0].finding_id == "TD-DEP-000"

    def test_provider_error_does_not_crash(self, tmp_path: Any) -> None:
        """Provider errors should never crash the pipeline."""
        repo = _make_repo(tmp_path)
        provider = SimulatedProvider(
            raw_text="",
            error_code="internal_error",
            error_message="Internal provider error",
        )

        import pharabius.ai.enricher as enricher_mod

        original = enricher_mod._get_provider
        enricher_mod._get_provider = lambda name: provider
        try:
            report = enrich_findings(repo, provider_name="simulated")
        finally:
            enricher_mod._get_provider = original

        # Should return a report, not raise
        assert report is not None
        assert len(report.enrichments) == 0


# ── AIResponse new fields tests ───────────────────────────────────────


class TestAIResponseFields:
    """Tests for new AIResponse fields."""

    def test_new_fields_have_defaults(self) -> None:
        resp = AIResponse(provider="test", model="test")
        assert resp.request_id == ""
        assert resp.latency_ms == 0
        assert resp.response_truncated is False
        assert resp.provider_error_code == ""
        assert resp.provider_error_message == ""

    def test_new_fields_populated(self) -> None:
        resp = AIResponse(
            provider="test",
            model="test",
            request_id="req-123",
            latency_ms=250,
            response_truncated=True,
            provider_error_code="rate_limit",
            provider_error_message="Too many requests",
        )
        assert resp.request_id == "req-123"
        assert resp.latency_ms == 250
        assert resp.response_truncated is True
        assert resp.provider_error_code == "rate_limit"

    def test_usage_new_fields_have_defaults(self) -> None:
        usage = AIUsageSummary()
        assert usage.prompt_tokens == 0
        assert usage.completion_tokens == 0
        assert usage.total_tokens == 0
        assert usage.estimated_cost == 0.0

    def test_usage_new_fields_populated(self) -> None:
        usage = AIUsageSummary(
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            estimated_cost=0.003,
        )
        assert usage.total_tokens == 150
        assert usage.estimated_cost == 0.003


# ── Unknown provider message tests ────────────────────────────────────


class TestUnknownProviderMessage:
    """Tests for improved unknown provider error message."""

    def test_unknown_provider_message_v080(self, tmp_path: Any) -> None:
        """Unknown provider should mention v0.8.0 and available providers."""
        from typer.testing import CliRunner

        from pharabius.cli import app

        runner = CliRunner()
        runner.invoke(app, ["enrich", "--provider", "openai", "-r", str(tmp_path)])
        # Should fail because debt-register.json is missing, but the provider
        # check happens first only when prerequisites exist
        # Let's test the enricher directly
        from pharabius.ai.enricher import _get_provider

        try:
            _get_provider("openai")
            raise AssertionError("Should have raised ValueError")
        except ValueError as e:
            assert "v0.8.0" in str(e)
            assert "disabled, mock" in str(e)
            assert "Future releases" in str(e)

    def test_unknown_provider_message_no_credential_lookup(self, tmp_path: Any) -> None:
        """Error message should not contain credential hints."""
        from pharabius.ai.enricher import _get_provider

        try:
            _get_provider("openai")
        except ValueError as e:
            msg = str(e).lower()
            assert "api key" not in msg
            assert "credential" not in msg
            assert "token" not in msg
            assert "environment" not in msg
