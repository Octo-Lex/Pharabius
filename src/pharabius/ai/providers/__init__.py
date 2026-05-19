"""AI provider adapters package.

Real providers are isolated here to keep the deterministic core boundary clean.
Provider modules may import only: stdlib, their dependency, ai.adapter, schemas.
"""

from __future__ import annotations


def _try_import_openai_compatible() -> type | None:
    """Attempt to import OpenAICompatibleAdapter, returning None if httpx is missing."""
    try:
        from pharabius.ai.providers.openai_compatible import OpenAICompatibleAdapter

        return OpenAICompatibleAdapter
    except ImportError:
        return None
