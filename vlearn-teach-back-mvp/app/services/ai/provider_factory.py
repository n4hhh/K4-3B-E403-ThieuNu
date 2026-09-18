"""Provider factory — selects the concrete provider at runtime.

Selection rule (in order):

    1. ``AI_PROVIDER`` env var (case-insensitive).
       Supported values: ``"gemini"`` (default) and ``"mock"``.
    2. If unset, defaults to ``"gemini"``.

Construction:

    * ``gemini``  → :class:`GeminiProvider` reads ``GEMINI_API_KEY`` and
                    ``GEMINI_MODEL`` at construction; raises
                    :class:`AIProviderMisconfiguredError` if missing.
    * ``mock``    → :class:`MockProvider` (no env vars needed).

The factory itself NEVER stores the key, the model, or the provider
instance — every call to :func:`build_provider` returns a fresh
instance. This avoids accidental cross-test leakage.
"""

from __future__ import annotations

import logging
from typing import Any

from app.services.ai.ai_provider import (
    AIProvider,
    AIProviderMisconfiguredError,
    coerce_provider_name,
)


logger = logging.getLogger(__name__)


def build_provider(name: Any = None) -> AIProvider:
    """Return a fresh provider for the requested name.

    Args:
        name: One of ``"gemini"`` or ``"mock"``. If ``None``, the
            factory uses ``AI_PROVIDER`` env var.
    """
    provider_name = coerce_provider_name(name)
    if provider_name == "mock":
        from app.services.ai.mock_provider import MockProvider

        logger.info("ProviderFactory: selected MockProvider")
        return MockProvider()

    if provider_name == "gemini":
        from app.services.ai.gemini_provider import GeminiProvider

        logger.info("ProviderFactory: selected GeminiProvider")
        return GeminiProvider()

    # coerce_provider_name already validated; this is defensive.
    raise AIProviderMisconfiguredError(f"Unknown provider name: {provider_name!r}")


__all__ = ["build_provider"]