"""AIProvider — Phase 3A.5 contract.

The Documentizer talks to ``AIProvider`` and nothing else. New
providers (OpenAI, Claude, a local LLM) plug in by implementing this
Protocol.

The provider MUST:

    * be stateless across calls (other than config it loaded at
      construction time);
    * not mutate any input;
    * not log secrets;
    * raise one of the provider errors declared below on failure;
    * never return a half-parsed payload — either ``DocumentizerOutput``
      is fully populated or an exception is raised.

The provider MUST NOT:

    * persist anything itself;
    * depend on Phase 3A services;
    * import from ``app.routers`` or ``app.main``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from app.models.raw_document import RawDocument


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class AIProviderError(Exception):
    """Base class for every provider-level error.

    Subclasses carry enough structure for the Documentizer to decide
    whether to retry (``AIProviderTransientError``) or fail fast
    (``AIProviderPermanentError``).
    """


class AIProviderTransientError(AIProviderError):
    """Recoverable error: timeout, 5xx, rate-limit, malformed JSON.

    The Documentizer will retry with backoff.
    """


class AIProviderPermanentError(AIProviderError):
    """Non-recoverable error: bad API key, 4xx other than rate-limit.

    The Documentizer will fail the document after the configured number
    of attempts.
    """


class AIProviderMisconfiguredError(AIProviderPermanentError):
    """API key missing/invalid or model name unrecognised.

    Raised at construction time by providers that cannot proceed.
    """


class AINoClaimError(AIProviderPermanentError):
    """Provider returned an empty / ungrounded payload.

    The Documentizer treats this as a "did not converge" outcome and
    surfaces it through the validation report.
    """


# ---------------------------------------------------------------------------
# Provider I/O types
# ---------------------------------------------------------------------------


@dataclass
class PageImage:
    """One optional page image to send alongside the page text.

    ``path`` is the on-disk path; ``page_number`` is the 1-based PDF
    page this image corresponds to. ``mime_type`` is used to set the
    right ``Part`` MIME when sending to Gemini.
    """

    page_number: int
    path: str
    mime_type: str = "image/png"


@dataclass
class DocumentizerOptions:
    """Provider-agnostic knobs that influence how the AI call is built.

    None of these may change the *meaning* of the result — they only
    affect what the provider is asked to produce.
    """

    language: str = "auto"
    target_chunks_min: int = 3
    target_chunks_max: int = 12
    include_definitions: bool = True
    include_examples: bool = True
    include_tables: bool = True
    include_diagrams: bool = True
    include_relationships: bool = True
    emit_page_images: bool = False


@dataclass
class DocumentizerInput:
    """Everything the Documentizer hands to a provider.

    ``raw_document`` is the Phase 3A ``RawDocument`` — treated as
    immutable source evidence. ``page_images`` is an optional,
    page-ordered list of rendered page images (for slide PDFs).
    """

    document_id: str
    raw_document: RawDocument
    page_images: List[PageImage] = field(default_factory=list)
    options: DocumentizerOptions = field(default_factory=DocumentizerOptions)
    run_id: Optional[str] = None  # cache key suffix


@dataclass
class ProviderMetadata:
    """Audit info returned by every provider call."""

    provider: str
    model: str
    request_id: Optional[str] = None
    latency_ms: int = 0
    usage: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DocumentizerOutput:
    """The provider's response.

    ``clean_payload`` is the raw parsed JSON dict (already validated
    as a :class:`~app.models.clean_document.CleanDocument` by the
    Documentizer before this object is returned to the caller).
    ``raw_response`` keeps the verbatim provider text for audit and
    cache replay. ``provider_metadata`` carries the audit fields.
    """

    clean_payload: Dict[str, Any]
    raw_response: str
    provider_metadata: ProviderMetadata


# ---------------------------------------------------------------------------
# AIProvider protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class AIProvider(Protocol):
    """The contract every provider must implement.

    ``documentize`` returns a parsed :class:`DocumentizerOutput`. Any
    failure must raise one of the AIProvider*Error classes declared
    in this module — never a generic ``Exception`` from the underlying
    SDK.
    """

    name: str
    model: str

    def documentize(self, input: DocumentizerInput) -> DocumentizerOutput:
        """Run the AI on ``input`` and return a parsed output.

        Raises:
            AIProviderTransientError: recoverable — Documentizer retries.
            AIProviderPermanentError: unrecoverable — Documentizer fails.
        """
        ...


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


SUPPORTED_PROVIDERS = ("gemini", "mock")


def coerce_provider_name(raw: Optional[str]) -> str:
    """Normalise the ``AI_PROVIDER`` env var.

    Falls back to ``"gemini"`` when unset, raises
    :class:`AIProviderMisconfiguredError` for unsupported values.
    """
    if not raw:
        return "gemini"
    name = raw.strip().lower()
    if name not in SUPPORTED_PROVIDERS:
        raise AIProviderMisconfiguredError(
            f"Unsupported AI_PROVIDER={raw!r}. Supported: {SUPPORTED_PROVIDERS}"
        )
    return name


__all__ = [
    "AIProvider",
    "AIProviderError",
    "AIProviderMisconfiguredError",
    "AIProviderPermanentError",
    "AIProviderTransientError",
    "AINoClaimError",
    "DocumentizerInput",
    "DocumentizerOptions",
    "DocumentizerOutput",
    "PageImage",
    "ProviderMetadata",
    "SUPPORTED_PROVIDERS",
    "coerce_provider_name",
]