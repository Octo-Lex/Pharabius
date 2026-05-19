"""AI adapter interface and response types.

Defines the provider-neutral adapter contract.
Real providers are NOT included in v0.8.0.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field

from pharabius.schemas.ai_enrichment import AIUsageSummary


class AIResponse(BaseModel):
    """Response from an AI provider call."""

    provider: str
    model: str
    raw_text: str = ""
    parsed_json: dict[str, Any] | None = None
    usage: AIUsageSummary = Field(default_factory=AIUsageSummary)
    finish_reason: str = ""
    errors: list[str] = Field(default_factory=list)
    request_id: str = ""
    latency_ms: int = 0
    response_truncated: bool = False
    provider_error_code: str = ""
    provider_error_message: str = ""


class AIAdapter(ABC):
    """Provider-neutral AI adapter interface.

    Implementations must:
    - Return schema-valid JSON in parsed_json
    - Set usage metrics
    - Report errors via errors list
    - Never make network calls unless explicitly approved
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name for logging and output."""

    @property
    @abstractmethod
    def model(self) -> str:
        """Model identifier for logging and output."""

    @abstractmethod
    def generate_json(
        self,
        prompt: str,
        context: dict[str, Any],
        schema_hint: dict[str, Any] | None = None,
        *,
        timeout_seconds: int = 30,
    ) -> AIResponse:
        """Generate a JSON response from the provider.

        Args:
            prompt: Instruction text for the provider.
            context: Structured context (evidence, finding, units, etc.).
            schema_hint: Optional schema describing expected output shape.
            timeout_seconds: Timeout for provider call (default 30s).

        Returns:
            AIResponse with parsed_json set if successful.
        """


class DisabledAdapter(AIAdapter):
    """No-op adapter for when AI is disabled.

    Returns an empty response with a clear message.
    """

    @property
    def name(self) -> str:
        return "disabled"

    @property
    def model(self) -> str:
        return "none"

    def generate_json(
        self,
        prompt: str,
        context: dict[str, Any],
        schema_hint: dict[str, Any] | None = None,
        *,
        timeout_seconds: int = 30,
    ) -> AIResponse:
        return AIResponse(
            provider=self.name,
            model=self.model,
            raw_text="",
            parsed_json=None,
            usage=AIUsageSummary(provider=self.name, model=self.model),
            finish_reason="disabled",
            errors=["AI provider is disabled. Use --provider mock for local testing."],
        )
