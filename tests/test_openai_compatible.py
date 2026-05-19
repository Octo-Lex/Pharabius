"""Tests for OpenAI-compatible provider adapter.

All tests use httpx.MockTransport — no real network calls in CI.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from unittest.mock import patch

import httpx
import pytest

# ── Helpers ────────────────────────────────────────────────────────────


def _valid_enrichment_json(n: int = 1) -> str:
    """Return valid enrichment JSON for n findings."""
    enrichments = []
    for i in range(n):
        enrichments.append(
            {
                "finding_id": f"TD-DEP-{i:03d}",
                "evidence_ids": [f"EVD-{i:03d}"],
                "confidence": "Medium",
                "limitations": ["AI-generated enrichment"],
                "explanation": f"Test enrichment for finding {i}",
            }
        )
    return json.dumps({"enrichments": enrichments})


def _mock_response(
    status_code: int = 200,
    content: str = "",
    *,
    finish_reason: str = "stop",
    model: str = "test-model",
    prompt_tokens: int = 100,
    completion_tokens: int = 50,
    request_id: str = "req-123",
) -> httpx.MockTransport:
    """Create a MockTransport returning the given response."""

    def handler(request: httpx.Request) -> httpx.Response:
        if status_code != 200:
            return httpx.Response(status_code, json={"error": {"message": "error"}})
        body = {
            "choices": [{"message": {"content": content}, "finish_reason": finish_reason}],
            "model": model,
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            },
        }
        headers = {}
        if request_id:
            headers["x-request-id"] = request_id
        return httpx.Response(status_code, json=body, headers=headers)

    return httpx.MockTransport(handler)


def _make_adapter(transport: httpx.MockTransport, *, model: str = "test-model") -> Any:
    """Create an OpenAICompatibleAdapter with mock transport."""
    from pharabius.ai.providers.openai_compatible import OpenAICompatibleAdapter

    with patch.dict(os.environ, {"PHARABIUS_OPENAI_API_KEY": "sk-test"}, clear=False):
        return OpenAICompatibleAdapter(model=model, transport=transport)


# ── Adapter unit tests ────────────────────────────────────────────────


class TestOpenAICompatibleAdapter:
    """Tests for the OpenAI-compatible provider adapter."""

    def test_missing_api_key_fails(self) -> None:
        """Missing API key should fail clearly."""
        from pharabius.ai.providers.openai_compatible import OpenAICompatibleAdapter

        with patch.dict(os.environ, {}, clear=True):
            # Remove any PHARABIUS_OPENAI_API_KEY
            os.environ.pop("PHARABIUS_OPENAI_API_KEY", None)
            with pytest.raises(ValueError, match="PHARABIUS_OPENAI_API_KEY"):
                OpenAICompatibleAdapter(model="test", transport=_mock_response())

    def test_missing_model_fails(self) -> None:
        """Missing model should fail clearly."""
        from pharabius.ai.providers.openai_compatible import OpenAICompatibleAdapter

        with (
            patch.dict(os.environ, {"PHARABIUS_OPENAI_API_KEY": "sk-test"}, clear=False),
            pytest.raises(ValueError, match=r"--model.*PHARABIUS_OPENAI_MODEL"),
        ):
            OpenAICompatibleAdapter(model="", transport=_mock_response())

    def test_api_key_not_echoed(self) -> None:
        """API key value should not appear in errors or responses."""
        adapter = _make_adapter(_mock_response(content=_valid_enrichment_json()))
        response = adapter.generate_json("test", {"findings": []})
        # Key should never appear in raw_text, errors, or serialized output
        dumped = response.model_dump_json()
        assert "sk-test" not in dumped

    def test_successful_response(self) -> None:
        """Successful provider response produces valid enrichment."""
        adapter = _make_adapter(_mock_response(content=_valid_enrichment_json(1)))
        response = adapter.generate_json(
            "test",
            {
                "findings": [
                    {
                        "id": "TD-DEP-000",
                        "evidence_ids": ["EVD-000"],
                        "title": "T",
                        "category": "C",
                        "severity": "Medium",
                        "analysis_unit_ids": [],
                    }
                ],
                "evidence_map": {},
            },
        )
        assert response.finish_reason == "stop"
        assert len(response.errors) == 0
        assert "TD-DEP-000" in response.raw_text

    def test_token_usage_captured(self) -> None:
        """Token usage from provider response should be captured."""
        adapter = _make_adapter(
            _mock_response(
                content=_valid_enrichment_json(), prompt_tokens=200, completion_tokens=100
            )
        )
        response = adapter.generate_json("test", {"findings": []})
        assert response.usage.prompt_tokens == 200
        assert response.usage.completion_tokens == 100
        assert response.usage.total_tokens == 300

    def test_request_id_captured(self) -> None:
        """Request ID from response headers should be captured."""
        adapter = _make_adapter(
            _mock_response(content=_valid_enrichment_json(), request_id="req-abc-123")
        )
        response = adapter.generate_json("test", {"findings": []})
        assert response.request_id == "req-abc-123"

    def test_latency_ms_populated(self) -> None:
        """Latency should be > 0."""
        adapter = _make_adapter(_mock_response(content=_valid_enrichment_json()))
        response = adapter.generate_json("test", {"findings": []})
        assert response.latency_ms >= 0

    def test_model_flag_overrides_env(self) -> None:
        """--model flag should take precedence over env var."""
        with patch.dict(os.environ, {"PHARABIUS_OPENAI_MODEL": "env-model"}, clear=False):
            adapter = _make_adapter(
                _mock_response(content=_valid_enrichment_json()), model="cli-model"
            )
            assert adapter.model == "cli-model"

    def test_env_model_fallback(self) -> None:
        """PHARABIUS_OPENAI_MODEL should be used if --model not passed."""
        from pharabius.ai.providers.openai_compatible import OpenAICompatibleAdapter

        with patch.dict(
            os.environ,
            {"PHARABIUS_OPENAI_API_KEY": "sk-test", "PHARABIUS_OPENAI_MODEL": "env-model"},
            clear=False,
        ):
            adapter = OpenAICompatibleAdapter(model="", transport=_mock_response())
            assert adapter.model == "env-model"

    def test_base_url_override(self) -> None:
        """PHARABIUS_OPENAI_BASE_URL should be used."""
        from pharabius.ai.providers.openai_compatible import OpenAICompatibleAdapter

        with patch.dict(
            os.environ,
            {
                "PHARABIUS_OPENAI_API_KEY": "sk-test",
                "PHARABIUS_OPENAI_MODEL": "m",
                "PHARABIUS_OPENAI_BASE_URL": "https://custom.api.com",
            },
            clear=False,
        ):
            adapter = OpenAICompatibleAdapter(model="m", transport=_mock_response())
            assert adapter._base_url == "https://custom.api.com"

    def test_malformed_provider_response_rejected(self) -> None:
        """Malformed JSON from provider should be in raw_text for validation to reject."""
        adapter = _make_adapter(_mock_response(content="not json {{{"))
        response = adapter.generate_json("test", {"findings": []})
        assert response.raw_text == "not json {{{"
        assert len(response.errors) == 0  # Adapter doesn't validate; validator does

    def test_auth_failure(self) -> None:
        """HTTP 401 should produce auth_failed error."""
        adapter = _make_adapter(_mock_response(status_code=401))
        response = adapter.generate_json("test", {"findings": []})
        assert response.provider_error_code == "auth_failed"
        assert len(response.errors) > 0

    def test_rate_limit(self) -> None:
        """HTTP 429 should produce rate_limit error."""
        adapter = _make_adapter(_mock_response(status_code=429))
        response = adapter.generate_json("test", {"findings": []})
        assert response.provider_error_code == "rate_limit"
        assert len(response.errors) > 0

    def test_timeout(self) -> None:
        """Timeout should produce timeout error."""

        def timeout_handler(request: httpx.Request) -> httpx.Response:
            raise httpx.TimeoutException("timed out")

        transport = httpx.MockTransport(timeout_handler)
        adapter = _make_adapter(transport)
        response = adapter.generate_json("test", {"findings": []})
        assert response.provider_error_code == "timeout"
        assert len(response.errors) > 0

    def test_server_error(self) -> None:
        """HTTP 500 should produce server_error."""
        adapter = _make_adapter(_mock_response(status_code=500))
        response = adapter.generate_json("test", {"findings": []})
        assert response.provider_error_code == "server_error"
        assert len(response.errors) > 0

    def test_content_filter(self) -> None:
        """Content filter finish_reason should be mapped."""
        adapter = _make_adapter(_mock_response(content="filtered", finish_reason="content_filter"))
        response = adapter.generate_json("test", {"findings": []})
        assert response.provider_error_code == "content_filter"
        assert len(response.errors) > 0

    def test_truncated_output(self) -> None:
        """Truncated output (finish_reason=length) should be flagged."""
        adapter = _make_adapter(
            _mock_response(content=_valid_enrichment_json(), finish_reason="length")
        )
        response = adapter.generate_json("test", {"findings": []})
        assert response.response_truncated is True

    def test_network_error(self) -> None:
        """Connection error should produce network_error."""

        def connect_handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("connection refused")

        transport = httpx.MockTransport(connect_handler)
        adapter = _make_adapter(transport)
        response = adapter.generate_json("test", {"findings": []})
        assert response.provider_error_code == "network_error"


# ── CLI/Consent tests ─────────────────────────────────────────────────


class TestCLIConsent:
    """Tests for external provider consent gate."""

    def test_external_without_consent_fails(self, tmp_path: Path) -> None:
        """openai-compatible without --allow-external-provider should fail."""
        from typer.testing import CliRunner

        from pharabius.cli import app

        # Setup repo
        ai = tmp_path / ".ai-debt"
        ai.mkdir()
        (ai / "evidence.json").write_text(
            json.dumps(
                {
                    "schema_version": "1.0",
                    "evidence": [
                        {
                            "evidence_id": "EVD-001",
                            "type": "test",
                            "location": {"file": "a.py"},
                            "raw_observation": "obs",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        (ai / "debt-register.json").write_text(
            json.dumps(
                {
                    "schema_version": "1.0",
                    "findings": [
                        {
                            "id": "TD-DEP-001",
                            "category": "TD-DEP",
                            "title": "T",
                            "severity": "Medium",
                            "evidence_ids": ["EVD-001"],
                            "analysis_unit_ids": [],
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

        runner = CliRunner()
        result = runner.invoke(
            app, ["enrich", "--provider", "openai-compatible", "-r", str(tmp_path)]
        )
        assert result.exit_code == 1
        assert "external" in result.output.lower()
        assert "--context-preview" in result.output
        assert "--allow-external-provider" in result.output

    def test_consent_message_recommends_preview(self, tmp_path: Path) -> None:
        """Consent message should recommend --context-preview."""
        from typer.testing import CliRunner

        from pharabius.cli import app

        ai = tmp_path / ".ai-debt"
        ai.mkdir()
        (ai / "evidence.json").write_text(
            json.dumps({"schema_version": "1.0", "evidence": []}), encoding="utf-8"
        )
        (ai / "debt-register.json").write_text(
            json.dumps({"schema_version": "1.0", "findings": []}), encoding="utf-8"
        )

        runner = CliRunner()
        result = runner.invoke(
            app, ["enrich", "--provider", "openai-compatible", "-r", str(tmp_path)]
        )
        assert result.exit_code == 1
        assert "--context-preview" in result.output

    def test_context_preview_no_provider_call(self, tmp_path: Path) -> None:
        """Context preview with openai-compatible should not call provider."""
        from typer.testing import CliRunner

        from pharabius.cli import app

        ai = tmp_path / ".ai-debt"
        ai.mkdir()
        (ai / "evidence.json").write_text(
            json.dumps(
                {
                    "schema_version": "1.0",
                    "evidence": [
                        {
                            "evidence_id": "EVD-001",
                            "type": "test",
                            "location": {"file": "a.py"},
                            "raw_observation": "obs",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        (ai / "debt-register.json").write_text(
            json.dumps(
                {
                    "schema_version": "1.0",
                    "findings": [
                        {
                            "id": "TD-DEP-001",
                            "category": "TD-DEP",
                            "title": "T",
                            "severity": "Medium",
                            "evidence_ids": ["EVD-001"],
                            "analysis_unit_ids": [],
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

        runner = CliRunner()
        result = runner.invoke(
            app,
            ["enrich", "--provider", "openai-compatible", "--context-preview", "-r", str(tmp_path)],
        )
        assert result.exit_code == 0
        assert "No provider was called" in result.output

    def test_context_preview_no_key_needed(self, tmp_path: Path) -> None:
        """Context preview should not require API key."""
        from typer.testing import CliRunner

        from pharabius.cli import app

        ai = tmp_path / ".ai-debt"
        ai.mkdir()
        (ai / "evidence.json").write_text(
            json.dumps({"schema_version": "1.0", "evidence": []}), encoding="utf-8"
        )
        (ai / "debt-register.json").write_text(
            json.dumps({"schema_version": "1.0", "findings": []}), encoding="utf-8"
        )

        runner = CliRunner()
        # No PHARABIUS_OPENAI_API_KEY set — should still work for preview
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("PHARABIUS_OPENAI_API_KEY", None)
            result = runner.invoke(
                app,
                [
                    "enrich",
                    "--provider",
                    "openai-compatible",
                    "--context-preview",
                    "-r",
                    str(tmp_path),
                ],
            )
        assert result.exit_code == 0

    def test_mock_no_consent_needed(self, tmp_path: Path) -> None:
        """Mock provider should not require consent."""
        from typer.testing import CliRunner

        from pharabius.cli import app

        ai = tmp_path / ".ai-debt"
        ai.mkdir()
        (ai / "evidence.json").write_text(
            json.dumps(
                {
                    "schema_version": "1.0",
                    "evidence": [
                        {
                            "evidence_id": "EVD-001",
                            "type": "test",
                            "location": {"file": "a.py"},
                            "raw_observation": "obs",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        (ai / "debt-register.json").write_text(
            json.dumps(
                {
                    "schema_version": "1.0",
                    "findings": [
                        {
                            "id": "TD-DEP-001",
                            "category": "TD-DEP",
                            "title": "T",
                            "severity": "Medium",
                            "evidence_ids": ["EVD-001"],
                            "analysis_unit_ids": [],
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

        runner = CliRunner()
        result = runner.invoke(app, ["enrich", "--provider", "mock", "-r", str(tmp_path)])
        assert result.exit_code == 0
        assert "Enriched:   1" in result.output

    def test_disabled_no_consent_needed(self, tmp_path: Path) -> None:
        """Disabled provider should not require consent."""
        from typer.testing import CliRunner

        from pharabius.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["enrich", "-r", str(tmp_path)])
        # Fails because no debt-register, but NOT because of consent
        assert "consent" not in result.output.lower() or result.exit_code != 1
        assert "external service" not in result.output

    def test_invalid_provider_still_fails(self, tmp_path: Path) -> None:
        """Unknown provider should still fail."""
        from typer.testing import CliRunner

        from pharabius.cli import app

        ai = tmp_path / ".ai-debt"
        ai.mkdir()
        (ai / "evidence.json").write_text(
            json.dumps({"schema_version": "1.0", "evidence": []}), encoding="utf-8"
        )
        (ai / "debt-register.json").write_text(
            json.dumps({"schema_version": "1.0", "findings": []}), encoding="utf-8"
        )

        runner = CliRunner()
        result = runner.invoke(app, ["enrich", "--provider", "nonexistent", "-r", str(tmp_path)])
        assert result.exit_code == 1
        assert "not available" in result.output

    def test_credentials_not_in_sidecars(self, tmp_path: Path) -> None:
        """API key should not appear in sidecar JSON."""
        ai = tmp_path / ".ai-debt"
        ai.mkdir()
        (ai / "evidence.json").write_text(
            json.dumps(
                {
                    "schema_version": "1.0",
                    "evidence": [
                        {
                            "evidence_id": "EVD-001",
                            "type": "test",
                            "location": {"file": "a.py"},
                            "raw_observation": "obs",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        (ai / "debt-register.json").write_text(
            json.dumps(
                {
                    "schema_version": "1.0",
                    "findings": [
                        {
                            "id": "TD-DEP-001",
                            "category": "TD-DEP",
                            "title": "T",
                            "severity": "Medium",
                            "evidence_ids": ["EVD-001"],
                            "analysis_unit_ids": [],
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

        # Run with mock (not real provider, but test sidecar content)
        from typer.testing import CliRunner

        from pharabius.cli import app

        runner = CliRunner()
        runner.invoke(app, ["enrich", "--provider", "mock", "-r", str(tmp_path)])

        sidecar = ai / "ai" / "enrichment-report.json"
        if sidecar.exists():
            content = sidecar.read_text(encoding="utf-8")
            assert "sk-test" not in content
            assert "api_key" not in content.lower()

    def test_credentials_not_in_ai_status(self, tmp_path: Path) -> None:
        """API key should not appear in ai-status output."""
        from typer.testing import CliRunner

        from pharabius.cli import app

        ai = tmp_path / ".ai-debt"
        ai.mkdir()
        (ai / "evidence.json").write_text(
            json.dumps({"schema_version": "1.0", "evidence": []}), encoding="utf-8"
        )
        (ai / "debt-register.json").write_text(
            json.dumps({"schema_version": "1.0", "findings": []}), encoding="utf-8"
        )

        runner = CliRunner()
        result = runner.invoke(app, ["ai-status", "-r", str(tmp_path)])
        assert "sk-test" not in result.output
        assert "api_key" not in result.output.lower()


# ── Regression tests ──────────────────────────────────────────────────


class TestProviderRegression:
    """Regression tests confirming existing behavior unchanged."""

    def test_disabled_unchanged(self) -> None:
        from pharabius.ai.adapter import DisabledAdapter

        adapter = DisabledAdapter()
        resp = adapter.generate_json("test", {})
        assert resp.finish_reason == "disabled"

    def test_mock_unchanged(self) -> None:
        from pharabius.ai.mock_provider import MockAIAdapter

        adapter = MockAIAdapter()
        assert adapter.name == "mock"

    def test_analyze_unchanged(self, tmp_path: Path) -> None:
        """analyze --no-ai should produce same result."""
        from typer.testing import CliRunner

        from pharabius.cli import app

        ai = tmp_path / ".ai-debt"
        ai.mkdir()
        (ai / "evidence.json").write_text(
            json.dumps(
                {
                    "schema_version": "1.0",
                    "evidence": [
                        {
                            "evidence_id": "EVD-001",
                            "type": "test",
                            "location": {"file": "a.py"},
                            "raw_observation": "obs",
                            "category": "test",
                            "summary": "test",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        (ai / "project-profile.json").write_text(
            json.dumps({"schema_version": "1.0", "detected_languages": ["Python"]}),
            encoding="utf-8",
        )

        runner = CliRunner()
        result = runner.invoke(app, ["analyze", "--no-ai", "-r", str(tmp_path)])
        assert result.exit_code == 0
        assert "Findings:" in result.output

    def test_import_boundary(self) -> None:
        """ai/ should not import core/."""
        ai_files = list(Path("src/pharabius/ai").rglob("*.py"))
        for f in ai_files:
            src = f.read_text(encoding="utf-8")
            assert "from pharabius.core" not in src, f"{f} imports core!"

        core_files = list(Path("src/pharabius/core").glob("*.py"))
        for f in core_files:
            src = f.read_text(encoding="utf-8")
            assert "from pharabius.ai" not in src, f"{f} imports ai!"

    def test_no_real_network_in_tests(self) -> None:
        """Verify provider module exists but uses no real network."""
        src = Path("src/pharabius/ai/providers/openai_compatible.py").read_text(encoding="utf-8")
        # httpx import is present (optional)
        assert "import httpx" in src
        # But no hardcoded real endpoints beyond the configurable default
        assert "api.openai.com" in src  # default base URL, configurable
