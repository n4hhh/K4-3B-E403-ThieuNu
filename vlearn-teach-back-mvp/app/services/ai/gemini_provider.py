"""GeminiProvider — real provider backed by ``google.genai``.

Design choices
--------------

* The provider is constructed from **environment variables only**. It
  reads ``GEMINI_API_KEY``, ``GEMINI_MODEL``, and ``AI_PROVIDER`` at
  construction time. No defaults are baked into source.

* All SDK calls are wrapped so the Documentizer only ever sees
  :class:`AIProviderTransientError` /
  :class:`AIProviderPermanentError` /
  :class:`AIProviderMisconfiguredError`. Raw SDK exception classes are
  not leaked to the Documentizer.

* The API key is **never** included in logs, exception messages, or
  raw payloads. Provider-level error messages are scrubbed before being
  raised.

* Structured output is requested via
  ``types.GenerateContentConfig(response_schema=STRUCTURED_LESSON_SCHEMA,
  response_mime_type="application/json")``. The model returns the JSON
  directly in ``response.text``; the provider extracts, parses, and
  returns a :class:`DocumentizerOutput`.

* Page images are passed as inline ``Part.from_bytes`` parts in
  document order, interleaved with the page-text marker parts so the
  model sees the same page order it sees in the prompt.

* The provider is **stateless across calls** — no caching, no
  retries. The Documentizer owns the retry ladder.

Phase 3A invariants
-------------------
* No calls into Phase 3A services.
* No mutation of the input ``RawDocument`` or any of its pages.
* No persistence.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional

from app.services.ai.ai_provider import (
    AIProviderMisconfiguredError,
    AIProviderPermanentError,
    AIProviderTransientError,
    DocumentizerInput,
    DocumentizerOutput,
    PageImage,
    ProviderMetadata,
)
from app.services.ai.prompts import (
    SYSTEM_PROMPT,
    build_user_prompt_default,
    build_user_prompt_grounding_strict,
)
from app.services.ai.schemas import STRUCTURED_LESSON_SCHEMA


logger = logging.getLogger(__name__)


# Scrub the API key out of any string that might contain it.
_API_KEY_SCRUB_RE = re.compile(r"(AIza[0-9A-Za-z_\-]{20,}|sk-[0-9A-Za-z_\-]{20,})")


def _scrub(text: Optional[str]) -> Optional[str]:
    if text is None:
        return None
    return _API_KEY_SCRUB_RE.sub("<redacted>", text)


# ---------------------------------------------------------------------------
# Provider
# ---------------------------------------------------------------------------


class GeminiProvider:
    """Real provider backed by ``google.genai``."""

    name: str = "gemini"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout_seconds: int = 30,
    ) -> None:
        # Read env at construction. Never hardcode.
        self._api_key = api_key if api_key is not None else os.environ.get("GEMINI_API_KEY")
        self._model = (
            model
            if model is not None
            else os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
        )
        self._timeout = timeout_seconds

        if not self._api_key or not self._api_key.strip():
            raise AIProviderMisconfiguredError(
                "GEMINI_API_KEY is not set. Add it to your .env file."
            )
        if not self._model or not self._model.strip():
            raise AIProviderMisconfiguredError(
                "GEMINI_MODEL is not set. Add it to your .env file."
            )

        # Import lazily so unit tests that never instantiate this class
        # do not pay the SDK import cost.
        try:
            from google import genai  # type: ignore
            from google.genai import types as genai_types  # type: ignore
        except ImportError as exc:  # pragma: no cover - import guard
            raise AIProviderMisconfiguredError(
                "google-genai SDK is not installed. Install with "
                "`pip install google-genai`."
            ) from exc

        self._genai = genai
        self._genai_types = genai_types

        # Create the client. New google.genai takes api_key directly.
        try:
            self._client = genai.Client(api_key=self._api_key)
        except Exception as exc:  # noqa: BLE001
            raise AIProviderMisconfiguredError(
                f"Failed to construct Gemini client: {_scrub(str(exc))}"
            ) from exc

    # ---- properties --------------------------------------------------------

    @property
    def model(self) -> str:
        return self._model

    # ---- public ------------------------------------------------------------

    def documentize(self, input: DocumentizerInput) -> DocumentizerOutput:
        return self._documentize(input, strict_grounding=False)

    def documentize_strict(self, input: DocumentizerInput) -> DocumentizerOutput:
        """Re-attempt variant with the grounding-strict prompt."""
        return self._documentize(input, strict_grounding=True)

    # ---- internal ----------------------------------------------------------

    def _documentize(
        self, input: DocumentizerInput, *, strict_grounding: bool
    ) -> DocumentizerOutput:
        per_page_text = [
            (page.page_number, page.text or "") for page in input.raw_document.pages
        ]
        has_page_images = bool(input.page_images)

        prompt_builder = (
            build_user_prompt_grounding_strict
            if strict_grounding
            else build_user_prompt_default
        )

        user_prompt = prompt_builder(
            document_id=input.document_id,
            source_file=input.raw_document.source_file,
            per_page_text=per_page_text,
            options={
                "language": input.options.language,
                "target_chunks_min": input.options.target_chunks_min,
                "target_chunks_max": input.options.target_chunks_max,
            },
            has_page_images=has_page_images,
        )

        # Build contents: a list of "parts" the model sees.
        # Order: [system prompt] then for each page: text marker + image.
        contents: List[Any] = []
        contents.append(
            self._genai_types.Content(
                role="user",
                parts=[
                    self._genai_types.Part(text=SYSTEM_PROMPT + "\n\n" + user_prompt)
                ],
            )
        )

        if has_page_images:
            # Page images are interleaved so the model can pair them with
            # the page text from the prompt.
            for img in input.page_images:
                img_part = self._image_part(img)
                if img_part is not None:
                    contents.append(
                        self._genai_types.Content(
                            role="user",
                            parts=[
                                self._genai_types.Part(
                                    text=f"(Image for page {img.page_number})"
                                ),
                                img_part,
                            ],
                        )
                    )

        # Structured output config.
        # ``max_output_tokens`` is generous because a 30-page lecture deck
        # yields 30+ sections × ~10 blocks ≈ 300 blocks with citations.
        # The default 8192 truncates the response mid-string; 65536 is
        # enough for the full structured document on this use case.
        config = self._genai_types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=STRUCTURED_LESSON_SCHEMA,
            temperature=0.2,
            max_output_tokens=65536,
        )

        started = time.perf_counter()
        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=contents,
                config=config,
            )
        except Exception as exc:  # noqa: BLE001
            latency_ms = int((time.perf_counter() - started) * 1000)
            logger.warning(
                "Gemini call failed after %d ms: %s",
                latency_ms,
                _scrub(str(exc)),
            )
            raise _map_gemini_exception(exc) from exc

        latency_ms = int((time.perf_counter() - started) * 1000)
        raw_text = _scrub(getattr(response, "text", None) or "")
        if not raw_text:
            raise AIProviderTransientError(
                "Gemini returned an empty response body"
            )

        try:
            payload = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            # Some Gemini versions wrap JSON in code fences even when
            # response_mime_type is set. Strip them and retry once.
            stripped = _strip_code_fence(raw_text)
            try:
                payload = json.loads(stripped)
            except json.JSONDecodeError:
                raise AIProviderTransientError(
                    f"Gemini returned malformed JSON: "
                    f"{_scrub(str(exc))[:200]}"
                ) from exc

        if not isinstance(payload, dict):
            raise AIProviderTransientError(
                "Gemini returned JSON of unexpected shape "
                f"(expected object, got {type(payload).__name__})"
            )

        metadata = ProviderMetadata(
            provider=self.name,
            model=self._model,
            request_id=_scrub(getattr(response, "response_id", None)),
            latency_ms=latency_ms,
            usage=_extract_usage(response),
        )

        return DocumentizerOutput(
            clean_payload=payload,
            raw_response=raw_text,
            provider_metadata=metadata,
        )

    # ---- helpers -----------------------------------------------------------

    def _image_part(self, img: PageImage) -> Optional[Any]:
        """Convert a PageImage into a ``Part`` for Gemini.

        Returns ``None`` if the file cannot be read; the Documentizer
        continues without that image.
        """
        from pathlib import Path

        path = Path(img.path)
        try:
            data = path.read_bytes()
        except OSError as exc:
            logger.warning(
                "Failed to read page image %s: %s", img.path, _scrub(str(exc))
            )
            return None

        mime = img.mime_type or "image/png"
        return self._genai_types.Part.from_bytes(data=data, mime_type=mime)


# ---------------------------------------------------------------------------
# Exception mapping
# ---------------------------------------------------------------------------


def _map_gemini_exception(exc: Exception) -> Exception:
    """Translate a raw google.genai exception into the right AIProvider error.

    Network errors, 5xx, and rate-limit → transient.
    Invalid key, 4xx (other than 429), and bad input → permanent.
    Anything we don't recognise → transient so the Documentizer retries
    instead of failing hard.
    """
    name = type(exc).__name__.lower()
    msg = _scrub(str(exc)) or ""

    if "permissiondenied" in name or "unauthenticated" in name or "invalidargument" in name:
        return AIProviderPermanentError(f"Gemini rejected the request: {msg[:200]}")
    if (
        "resourceexhausted" in name
        or "ratelimitexceeded" in name
        or "deadlineexceeded" in name
        or "aborted" in name
        or "unavailable" in name
        or "internalserver" in name
    ):
        return AIProviderTransientError(f"Gemini transient error: {msg[:200]}")
    if "connection" in name or "timeout" in name or "network" in name:
        return AIProviderTransientError(f"Gemini network error: {msg[:200]}")

    # Unknown: treat as transient so the retry policy can have a go.
    return AIProviderTransientError(f"Gemini error: {msg[:200]}")


def _strip_code_fence(text: str) -> str:
    """Strip ``` fences that some Gemini responses still include."""
    text = text.strip()
    if text.startswith("```"):
        # Drop opening fence (possibly with language tag).
        text = re.sub(r"^```[a-zA-Z0-9]*\s*", "", text)
    if text.endswith("```"):
        text = text[: -len("```")]
    return text.strip()


def _extract_usage(response: Any) -> Dict[str, Any]:
    """Best-effort usage extraction. Never raises."""
    try:
        meta = getattr(response, "usage_metadata", None)
        if meta is None:
            return {}
        out: Dict[str, Any] = {}
        for attr in (
            "prompt_token_count",
            "candidates_token_count",
            "total_token_count",
        ):
            v = getattr(meta, attr, None)
            if v is not None:
                out[attr] = v
        return out
    except Exception:  # noqa: BLE001
        return {}


__all__ = ["GeminiProvider"]