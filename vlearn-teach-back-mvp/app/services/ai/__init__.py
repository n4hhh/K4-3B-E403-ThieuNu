"""Public surface for the Phase 3A.5 AI integration package."""

from app.services.ai.ai_provider import (
    AIProvider,
    AIProviderError,
    AIProviderMisconfiguredError,
    AIProviderPermanentError,
    AIProviderTransientError,
    AINoClaimError,
    DocumentizerInput,
    DocumentizerOptions,
    DocumentizerOutput,
    PageImage,
    ProviderMetadata,
    SUPPORTED_PROVIDERS,
    coerce_provider_name,
)
from app.services.ai.documentizer import (
    Documentizer,
    DocumentizerConfig,
    DocumentizerResult,
)
from app.services.ai.mock_provider import MockProvider
from app.services.ai.provider_factory import build_provider


__all__ = [
    # Errors
    "AIProvider",
    "AIProviderError",
    "AIProviderMisconfiguredError",
    "AIProviderPermanentError",
    "AIProviderTransientError",
    "AINoClaimError",
    # IO
    "DocumentizerInput",
    "DocumentizerOptions",
    "DocumentizerOutput",
    "PageImage",
    "ProviderMetadata",
    "SUPPORTED_PROVIDERS",
    "coerce_provider_name",
    # Concrete providers
    "MockProvider",
    "build_provider",
    # Higher-level orchestrator
    "Documentizer",
    "DocumentizerConfig",
    "DocumentizerResult",
]