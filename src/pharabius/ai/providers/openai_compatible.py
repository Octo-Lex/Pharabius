"""OpenAI-compatible provider adapter.

Implements the AIAdapter interface for any endpoint that supports the
expected OpenAI-compatible /v1/chat/completions request and response shape.

Requires the ``openai-compatible`` extra: ``pip install "pharabius[openai-compatible]"``
"""

from __future__ import annotations

import os
import time
from typing import Any

try:
    import httpx

    _HTTPEX_AVAILABLE = True
except ImportError:
    httpx = None  # type: ignore[assignment]
    _HTTPEX_AVAILABLE = False

from pharabius.ai.adapter import AIAdapter, AIResponse
from pharabius.schemas.ai_enrichment import AIUsageSummary


class OpenAICompatibleAdapter(AIAdapter):
    """Provider adapter for OpenAI-compatible /v1/chat/completions endpoints.

    Configuration (environment variables):
        PHARABIUS_OPENAI_API_KEY   — Required. API key.
        PHARABIUS_OPENAI_MODEL     — Required if --model not passed.
        PHARABIUS_OPENAI_BASE_URL  — Optional. Defaults to https://api.openai.com

    No hardcoded model default. Model must be provided explicitly.
    """

    def __init__(
        self,
        *,
        model: str = "",
        transport: Any = None,
    ) -> None:
        if not _HTTPEX_AVAILABLE:
            raise ImportError(
                "Provider 'openai-compatible' requires httpx. "
                'Install with: pip install "pharabius[openai-compatible]"'
            )

        # Credentials — environment variables only
        api_key = os.environ.get("PHARABIUS_OPENAI_API_KEY", "")
        if not api_key:
            raise ValueError(
                "API key not found. Set PHARABIUS_OPENAI_API_KEY environment variable."
            )
        self._api_key = api_key

        # Model — must be provided, no default
        resolved_model = model or os.environ.get("PHARABIUS_OPENAI_MODEL", "")
        if not resolved_model:
            raise ValueError(
                "Model is required for provider 'openai-compatible'. "
                "Pass --model or set PHARABIUS_OPENAI_MODEL."
            )
        self._model = resolved_model

        # Base URL — safe default
        self._base_url = os.environ.get(
            "PHARABIUS_OPENAI_BASE_URL",
            "https://api.openai.com",
        ).rstrip("/")

        self._transport = transport  # None = real HTTP, httpx.MockTransport = test

    @property
    def name(self) -> str:
        return "openai-compatible"

    @property
    def model(self) -> str:
        return self._model

    def generate_json(
        self,
        prompt: str,
        context: dict[str, Any],
        schema_hint: dict[str, Any] | None = None,
        *,
        timeout_seconds: int = 30,
    ) -> AIResponse:
        """Call the OpenAI-compatible endpoint and return AIResponse."""
        system_msg = _build_system_message()
        user_msg = prompt

        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }

        url = f"{self._base_url}/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        start = time.monotonic()
        try:
            if self._transport is not None:
                client = httpx.Client(transport=self._transport, timeout=timeout_seconds)
            else:
                client = httpx.Client(timeout=timeout_seconds)
            with client:
                resp = client.post(url, json=payload, headers=headers)
            latency_ms = int((time.monotonic() - start) * 1000)
        except httpx.TimeoutException:
            latency_ms = int((time.monotonic() - start) * 1000)
            return AIResponse(
                provider=self.name,
                model=self._model,
                errors=["Provider request timed out."],
                finish_reason="timeout",
                latency_ms=latency_ms,
                provider_error_code="timeout",
                provider_error_message="Provider request timed out.",
            )
        except httpx.ConnectError as exc:
            latency_ms = int((time.monotonic() - start) * 1000)
            return AIResponse(
                provider=self.name,
                model=self._model,
                errors=[f"Network error: {exc}"],
                finish_reason="network_error",
                latency_ms=latency_ms,
                provider_error_code="network_error",
                provider_error_message=str(exc),
            )
        except Exception as exc:
            latency_ms = int((time.monotonic() - start) * 1000)
            return AIResponse(
                provider=self.name,
                model=self._model,
                errors=[f"Provider error: {exc}"],
                finish_reason="error",
                latency_ms=latency_ms,
                provider_error_code="unknown",
                provider_error_message=str(exc),
            )

        # Handle HTTP errors
        if resp.status_code == 401:
            return AIResponse(
                provider=self.name,
                model=self._model,
                errors=["Authentication failed. Check PHARABIUS_OPENAI_API_KEY."],
                finish_reason="auth_failed",
                latency_ms=latency_ms,
                provider_error_code="auth_failed",
                provider_error_message="Authentication failed.",
            )
        if resp.status_code == 429:
            return AIResponse(
                provider=self.name,
                model=self._model,
                errors=["Rate limit exceeded."],
                finish_reason="rate_limit",
                latency_ms=latency_ms,
                provider_error_code="rate_limit",
                provider_error_message="Rate limit exceeded.",
            )
        if resp.status_code >= 500:
            return AIResponse(
                provider=self.name,
                model=self._model,
                errors=[f"Provider server error: HTTP {resp.status_code}"],
                finish_reason="server_error",
                latency_ms=latency_ms,
                provider_error_code="server_error",
                provider_error_message=f"HTTP {resp.status_code}",
            )
        if resp.status_code != 200:
            return AIResponse(
                provider=self.name,
                model=self._model,
                errors=[f"Unexpected HTTP {resp.status_code}"],
                finish_reason="error",
                latency_ms=latency_ms,
                provider_error_code=f"http_{resp.status_code}",
                provider_error_message=f"HTTP {resp.status_code}",
            )

        # Parse successful response
        try:
            body = resp.json()
        except Exception as exc:
            return AIResponse(
                provider=self.name,
                model=self._model,
                errors=[f"Malformed response JSON: {exc}"],
                finish_reason="malformed_response",
                latency_ms=latency_ms,
                provider_error_code="malformed_response",
                provider_error_message=str(exc),
            )

        # Extract content
        choices = body.get("choices", [])
        if not choices:
            return AIResponse(
                provider=self.name,
                model=self._model,
                errors=["Empty choices in provider response."],
                finish_reason="empty",
                latency_ms=latency_ms,
            )

        choice = choices[0]
        message = choice.get("message", {})
        content = message.get("content", "")
        finish_reason = choice.get("finish_reason", "unknown")

        # Handle content filter
        if finish_reason == "content_filter":
            return AIResponse(
                provider=self.name,
                model=self._model,
                raw_text=content,
                errors=["Content filtered by provider safety system."],
                finish_reason="content_filter",
                latency_ms=latency_ms,
                provider_error_code="content_filter",
                provider_error_message="Content filtered by provider safety system.",
            )

        # Extract usage
        usage_data = body.get("usage", {})
        prompt_tokens = usage_data.get("prompt_tokens", 0) or 0
        completion_tokens = usage_data.get("completion_tokens", 0) or 0
        total_tokens = usage_data.get("total_tokens", 0) or 0

        # Extract request ID
        request_id = resp.headers.get("x-request-id", "")

        truncated = finish_reason == "length"

        return AIResponse(
            provider=self.name,
            model=self._model,
            raw_text=content,
            usage=AIUsageSummary(
                provider=self.name,
                model=self._model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                estimated_cost=0.0,  # No cost calculation in v0.9.0
            ),
            finish_reason=finish_reason,
            latency_ms=latency_ms,
            request_id=request_id,
            response_truncated=truncated,
        )


_SYSTEM_MESSAGE = """\
You are a technical debt analysis assistant. You MUST respond with strict JSON only.
No markdown. No comments. No prose outside the JSON.

Requirements:
- Output a JSON object with an "enrichments" array
- Each enrichment must include: finding_id, evidence_ids, confidence (High/Medium/Low),\
  limitations (non-empty array)
- Only use finding IDs provided in the context
- Only use evidence IDs provided in the context
- Do not invent new findings, categories, or file paths
- Do not suggest code modifications or remediation execution
- Include explanation, risk_rationale, recommended_action_refinement, uncertainty_notes

Schema:
{
  "enrichments": [
    {
      "finding_id": "<from context>",
      "evidence_ids": ["<from context>"],
      "confidence": "High|Medium|Low",
      "limitations": ["AI-generated enrichment - validate before acting"],
      "explanation": "...",
      "risk_rationale": "...",
      "recommended_action_refinement": "...",
      "uncertainty_notes": "..."
    }
  ]
}
"""


def _build_system_message() -> str:
    """Return the system message for the provider request."""
    return _SYSTEM_MESSAGE
