"""Pharabius AI adapter package.

Provider-neutral, evidence-constrained AI enrichment.
Operates only on existing deterministic evidence.
Never mutates canonical artifacts.
"""

from pharabius.ai.adapter import AIAdapter, AIResponse
from pharabius.ai.enricher import enrich_findings, format_context_preview, preview_context
from pharabius.ai.mock_provider import MockAIAdapter
from pharabius.ai.status_reader import SidecarStatus, read_ai_status

__all__ = [
    "AIAdapter",
    "AIResponse",
    "MockAIAdapter",
    "SidecarStatus",
    "enrich_findings",
    "format_context_preview",
    "preview_context",
    "read_ai_status",
]
