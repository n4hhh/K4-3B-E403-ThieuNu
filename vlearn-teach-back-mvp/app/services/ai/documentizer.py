"""Documentizer — RawDocument → CleanDocument orchestrator.

Responsibilities:

    1. Build a :class:`DocumentizerInput` from a ``RawDocument`` and
       optional page images.
    2. Call the provider's :meth:`documentize`.
    3. Validate the response shape against the ``CleanDocument`` model
       and against the JSON schema for the StructuredLesson top level.
    4. Return a parsed ``CleanDocument`` to the pipeline (which later
       wraps it in a ``StructuredLesson``).

The Documentizer is **provider-agnostic** — it depends only on the
:protocol:`AIProvider` interface and never imports ``google.genai``.

Retry ladder
------------

``DocumentizerConfig`` controls:

    * ``max_attempts`` — total AI calls before giving up.
    * ``grounding_retry_attempts`` — number of additional attempts that
      use the grounding-strict prompt (e.g. for ``GeminiProvider``,
      this triggers ``documentize_strict`` on attempt ≥ 2).
    * ``backoff_seconds`` — linear backoff base.

Failure semantics:

    * :class:`AIProviderTransientError` → retry up to ``max_attempts``.
    * :class:`AIProviderPermanentError` → fail immediately.
    * :class:`AIProviderMisconfiguredError` → fail immediately.
    * ``CleanDocument`` validation failure → retry (transient, may be
      malformed output).
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from app.models.clean_document import CleanDocument
from app.models.raw_document import RawDocument

from app.services.ai.ai_provider import (
    AIProvider,
    AIProviderError,
    AIProviderMisconfiguredError,
    AIProviderPermanentError,
    AIProviderTransientError,
    DocumentizerInput,
    DocumentizerOptions,
    DocumentizerOutput,
    PageImage,
)


logger = logging.getLogger(__name__)


@dataclass
class DocumentizerConfig:
    """Configuration knobs for one Documentizer call.

    These are passed in by the pipeline (which reads them from
    ``.env`` / config). Defaults are conservative.
    """

    max_attempts: int = 3
    grounding_retry_attempts: int = 1  # attempts 2..1+ are "strict"
    backoff_seconds: float = 1.0

    language: str = "auto"
    target_chunks_min: int = 3
    target_chunks_max: int = 12

    include_definitions: bool = True
    include_examples: bool = True
    include_tables: bool = True
    include_diagrams: bool = True
    include_relationships: bool = True
    emit_page_images: bool = False

    def to_options(self) -> DocumentizerOptions:
        return DocumentizerOptions(
            language=self.language,
            target_chunks_min=self.target_chunks_min,
            target_chunks_max=self.target_chunks_max,
            include_definitions=self.include_definitions,
            include_examples=self.include_examples,
            include_tables=self.include_tables,
            include_diagrams=self.include_diagrams,
            include_relationships=self.include_relationships,
            emit_page_images=self.emit_page_images,
        )


@dataclass
class DocumentizerResult:
    """One Documentizer call's outcome."""

    clean_document: CleanDocument
    raw_response: str
    attempts: int
    provider_metadata: Dict[str, Any]
    issues: List[str]


class Documentizer:
    """Orchestrates ``RawDocument → CleanDocument``."""

    def __init__(
        self,
        provider: AIProvider,
        config: Optional[DocumentizerConfig] = None,
    ) -> None:
        self._provider = provider
        self._config = config or DocumentizerConfig()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def documentize(
        self,
        raw_document: RawDocument,
        page_images: Optional[List[PageImage]] = None,
        run_id: Optional[str] = None,
    ) -> DocumentizerResult:
        """Run the AI on ``raw_document`` and return a parsed result.

        Args:
            raw_document: The immutable Phase 3A source.
            page_images: Optional page images, page-ordered.
            run_id: Optional cache key suffix.

        Raises:
            AIProviderError: When every attempt failed permanently or
                the retry ladder was exhausted.
        """
        input = self._build_input(raw_document, page_images, run_id)
        last_exc: Optional[Exception] = None
        issues: List[str] = []
        last_output: Optional[DocumentizerOutput] = None

        for attempt in range(1, self._config.max_attempts + 1):
            strict = attempt > 1 and attempt <= 1 + self._config.grounding_retry_attempts
            logger.info(
                "Documentizer attempt %d/%d (strict=%s) for %s",
                attempt,
                self._config.max_attempts,
                strict,
                raw_document.document_id,
            )

            try:
                output = self._call_provider(input, strict=strict)
                last_output = output

                clean_doc = self._parse_clean_document(output, raw_document)

                return DocumentizerResult(
                    clean_document=clean_doc,
                    raw_response=output.raw_response,
                    attempts=attempt,
                    provider_metadata=output.provider_metadata.__dict__,
                    issues=issues,
                )
            except AIProviderMisconfiguredError:
                # Re-raise immediately — config error is not transient.
                raise
            except AIProviderPermanentError as exc:
                # Re-raise immediately — there's no point retrying.
                logger.warning(
                    "Permanent provider error on attempt %d: %s",
                    attempt,
                    exc,
                )
                raise
            except AIProviderTransientError as exc:
                issues.append(f"attempt {attempt}: {exc}")
                last_exc = exc
                logger.warning(
                    "Transient provider error on attempt %d: %s",
                    attempt,
                    exc,
                )
            except _CleanDocumentShapeError as exc:
                # The provider returned text, but it didn't parse as a
                # CleanDocument. Treat as transient — strict retry may
                # help; otherwise move on.
                issues.append(f"attempt {attempt}: shape error: {exc}")
                last_exc = exc
                logger.warning("CleanDocument parse failure on attempt %d", attempt)

            if attempt < self._config.max_attempts:
                backoff = self._config.backoff_seconds * attempt
                time.sleep(backoff)

        # Exhausted.
        assert last_exc is not None
        raise last_exc

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _build_input(
        self,
        raw_document: RawDocument,
        page_images: Optional[List[PageImage]],
        run_id: Optional[str],
    ) -> DocumentizerInput:
        return DocumentizerInput(
            document_id=raw_document.document_id,
            raw_document=raw_document,
            page_images=list(page_images or []),
            options=self._config.to_options(),
            run_id=run_id,
        )

    def _call_provider(
        self, input: DocumentizerInput, *, strict: bool
    ) -> DocumentizerOutput:
        # Most providers expose a single ``documentize``; the Gemini
        # provider additionally exposes ``documentize_strict``. We
        # prefer the strict variant when supported, otherwise fall back.
        if strict and hasattr(self._provider, "documentize_strict"):
            return self._provider.documentize_strict(input)  # type: ignore[attr-defined]
        return self._provider.documentize(input)

    def _parse_clean_document(
        self, output: DocumentizerOutput, raw: RawDocument
    ) -> CleanDocument:
        """Coerce provider payload into a validated ``CleanDocument``."""
        payload = output.clean_payload

        # Tolerate a wrapped payload (e.g. ``{"lesson": {...}}``).
        if "sections" not in payload and "lesson" in payload:
            payload = payload["lesson"]

        # Inject stable fields that the Documentizer owns (not Gemini).
        payload.setdefault("document_id", raw.document_id)
        payload.setdefault("source_file", raw.source_file)
        payload.setdefault("language", self._config.language)

        # Gemini's structured-output schema only accepts a single
        # ``type`` per field, so it cannot express ``["string", "null"]``
        # for ``common_misconception`` / ``clarification_trigger``. We
        # therefore coerce empty strings (and the literal "null") to
        # None before Pydantic validates.
        self._normalize_nullable_teach_back_fields(payload)

        # Gemini may return ``chunks`` at the top level. We hoist them
        # out into ``teach_back_chunks`` so CleanDocument carries them
        # forward and the LessonBuilder can use them directly.
        self._extract_gemini_chunks(payload)

        try:
            return CleanDocument.model_validate(payload)
        except Exception as exc:  # noqa: BLE001
            raise _CleanDocumentShapeError(str(exc)) from exc

    # ------------------------------------------------------------------
    # Normalisation helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_nullable_teach_back_fields(payload: Dict[str, Any]) -> None:
        """Coerce empty ``teach_back`` strings to ``None`` in-place.

        Gemini cannot emit JSON-null for these fields because the
        structured-output schema disallows ``"null"`` as a type. We
        therefore tell the model in the prompt to use empty strings to
        mean "no value", and convert here.
        """
        chunks = payload.get("chunks") or []
        if not isinstance(chunks, list):
            return
        for chunk in chunks:
            if not isinstance(chunk, dict):
                continue
            teach_back = chunk.get("teach_back")
            if not isinstance(teach_back, dict):
                continue
            for nullable_field in (
                "common_misconception",
                "clarification_trigger",
            ):
                if nullable_field in teach_back:
                    value = teach_back[nullable_field]
                    if isinstance(value, str):
                        stripped = value.strip()
                        if not stripped or stripped.lower() in {"null", "none"}:
                            teach_back[nullable_field] = None

    @staticmethod
    def _extract_gemini_chunks(payload: Dict[str, Any]) -> None:
        """Move top-level ``chunks`` to ``teach_back_chunks`` in-place.

        CleanDocument does not own a top-level ``chunks`` field, so
        pydantic would otherwise silently drop them. We preserve them
        so the LessonBuilder can use Gemini's teach_back targets.
        """
        if "teach_back_chunks" not in payload and "chunks" in payload:
            payload["teach_back_chunks"] = payload.pop("chunks")


class _CleanDocumentShapeError(AIProviderTransientError):
    """The provider response did not parse as a ``CleanDocument``."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


__all__ = [
    "Documentizer",
    "DocumentizerConfig",
    "DocumentizerResult",
]