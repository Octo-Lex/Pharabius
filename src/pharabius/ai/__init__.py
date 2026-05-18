"""Pharabius AI adapter package.

Provider-neutral, evidence-constrained AI enrichment.
Operates only on existing deterministic evidence.
Never mutates canonical artifacts.
"""

from pharabius.ai.adapter import AIAdapter, AIResponse
from pharabius.ai.enricher import enrich_findings
from pharabius.ai.mock_provider import MockAIAdapter

__all__ = [
    "AIAdapter",
    "AIResponse",
    "MockAIAdapter",
    "enrich_findings",
]
