"""DocumentizerPipeline — Phase 3A.5 end-to-end orchestrator.

Pipeline:

    RawDocument
        ↓
    Documentizer (CleanDocument)
        ↓
    LessonBuilder → StructuredLesson
        ↓
    Three validation gates (A, B, C)
        ↓
    Publish (PASS / WARN) — or fail

Retry ladder
------------

Phase 3A.5 supports up to ``max_attempts`` AI calls. The first attempt
uses the default prompt; subsequent attempts use the grounding-strict
prompt and may also reduce the chunk target range.

If every attempt fails, the pipeline raises ``DocumentizerFailedError``
carrying the best ValidationReport it could produce.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from app.models.clean_document import CleanDocument
from app.models.raw_document import RawDocument
from app.models.structured_lesson import (
    GeneratedBy,
    StructuredLesson,
)
from app.models.validation_report import (
    GateName,
    GateOutcome,
    GateResult,
    ProvenanceStats,
    ValidationIssue,
    ValidationPolicy,
    ValidationReport,
)
from app.repositories.published_lesson_repository import (
    PublishedLessonRepository,
)
from app.services.raw_document_service import RawDocumentService
from app.services.ai.ai_provider import (
    AIProvider,
    AIProviderError,
    AIProviderMisconfiguredError,
    AIProviderPermanentError,
    AIProviderTransientError,
    PageImage,
)
from app.services.ai.documentizer import (
    Documentizer,
    DocumentizerConfig,
    DocumentizerResult,
)
from app.services.lesson_builder import build_lesson
from app.services.validators import (
    ConfidenceValidator,
    SchemaValidator,
    SourceGroundingValidator,
)


logger = logging.getLogger(__name__)


class DocumentizerFailedError(Exception):
    """Raised when every attempt failed and no lesson can be published."""

    def __init__(
        self,
        message: str,
        report: Optional[ValidationReport] = None,
        attempts: int = 0,
    ) -> None:
        super().__init__(message)
        self.report = report
        self.attempts = attempts


@dataclass
class DocumentizerPipelineConfig:
    """Configuration for the DocumentizerPipeline.

    All values are read from .env / app.config; the pipeline does not
    re-read them itself.
    """

    max_attempts: int = 3
    grounding_retry_attempts: int = 1
    backoff_seconds: float = 1.0

    language: str = "auto"
    target_chunks_min: int = 3
    target_chunks_max: int = 12

    # Defaults are tuned for slide-style PDFs:
    # - citations are paraphrased by Gemini, so the strict 0.85
    #   substring/fuzzy matcher rarely reaches 100 % coverage.
    # - long lectures cover content sparsely (one slide may only
    #   mention a few concepts that another slide references again).
    # Tests can override these values.
    grounding_threshold: float = 0.40
    page_coverage_floor: float = 0.30
    min_confidence: float = 0.55

    emit_page_images: bool = False

    def to_documentizer_config(self) -> DocumentizerConfig:
        return DocumentizerConfig(
            max_attempts=self.max_attempts,
            grounding_retry_attempts=self.grounding_retry_attempts,
            backoff_seconds=self.backoff_seconds,
            language=self.language,
            target_chunks_min=self.target_chunks_min,
            target_chunks_max=self.target_chunks_max,
            emit_page_images=self.emit_page_images,
        )

    def to_policy(self) -> ValidationPolicy:
        return ValidationPolicy(
            grounding_threshold=self.grounding_threshold,
            page_coverage_floor=self.page_coverage_floor,
            min_confidence=self.min_confidence,
        )


@dataclass
class DocumentizerPipelineResult:
    """Outcome of one :meth:`DocumentizerPipeline.process` call."""

    lesson: StructuredLesson
    validation: ValidationReport
    attempts: int
    published_path: Optional[Path]
    raw_response: str


class DocumentizerPipeline:
    """The full RawDocument → published.json pipeline."""

    def __init__(
        self,
        provider: AIProvider,
        config: Optional[DocumentizerPipelineConfig] = None,
        raw_doc_service: Optional[RawDocumentService] = None,
        published_repo: Optional[PublishedLessonRepository] = None,
        documentizer: Optional[Documentizer] = None,
    ) -> None:
        self._config = config or DocumentizerPipelineConfig()
        self._provider = provider
        self._documentizer = documentizer or Documentizer(
            provider, self._config.to_documentizer_config()
        )
        self._raw_service = raw_doc_service or RawDocumentService()
        self._published_repo = published_repo or PublishedLessonRepository()

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def process(
        self,
        document_id: str,
        *,
        page_images: Optional[List[PageImage]] = None,
        publish: bool = True,
    ) -> DocumentizerPipelineResult:
        """Run the full pipeline on ``document_id``.

        Args:
            document_id: ID of an already-saved RawDocument.
            page_images: Optional page images (one per source page).
            publish: If False, do everything except write
                ``published.json``. Useful for tests / dry runs.
        """
        raw = self._raw_service.load(document_id)
        if raw is None:
            raise FileNotFoundError(
                f"No RawDocument found for {document_id!r}; "
                "did Phase 3A run first?"
            )

        last_report: Optional[ValidationReport] = None
        last_lesson: Optional[StructuredLesson] = None
        last_raw_response: str = ""

        for attempt in range(1, self._config.max_attempts + 1):
            logger.info(
                "Pipeline attempt %d/%d for %s", attempt, self._config.max_attempts, document_id
            )

            try:
                doc_result = self._documentizer.documentize(
                    raw, page_images=page_images, run_id=f"{document_id}:{attempt}"
                )
            except AIProviderMisconfiguredError as exc:
                # Permanent: no point retrying.
                raise DocumentizerFailedError(
                    f"Provider misconfigured: {exc}",
                    report=None,
                    attempts=attempt - 1,
                ) from exc
            except AIProviderPermanentError as exc:
                raise DocumentizerFailedError(
                    f"Provider returned a permanent error: {exc}",
                    report=None,
                    attempts=attempt - 1,
                ) from exc
            except AIProviderTransientError as exc:
                logger.warning(
                    "Transient provider error on attempt %d/%d: %s",
                    attempt,
                    self._config.max_attempts,
                    exc,
                )
                last_raw_response = str(exc)
                continue
            except AIProviderError as exc:  # pragma: no cover - defensive
                raise DocumentizerFailedError(
                    f"Unexpected provider error: {exc}",
                    report=None,
                    attempts=attempt - 1,
                ) from exc

            last_raw_response = doc_result.raw_response
            clean = doc_result.clean_document

            # Build the structured lesson.
            source_sha256 = self._published_repo.compute_source_sha256(raw)
            generated_by = GeneratedBy(
                provider=self._provider.name,
                model=self._provider.model,
                pipeline_version="3a5.0.0",
            )
            lesson = build_lesson(
                clean,
                source_sha256=source_sha256,
                generated_by=generated_by,
            )

            # Validate.
            report = self._validate(lesson, raw)
            last_report = report
            last_lesson = lesson

            if report.can_publish():
                # Success
                if publish:
                    path = self._published_repo.save(document_id, lesson, report)
                else:
                    path = None

                return DocumentizerPipelineResult(
                    lesson=lesson,
                    validation=report,
                    attempts=attempt,
                    published_path=path,
                    raw_response=last_raw_response,
                )

            logger.info(
                "Attempt %d did not pass validation (status=%s, score=%.2f)",
                attempt,
                report.status.value,
                report.grounding_score,
            )

        # All attempts failed.
        msg = (
            f"All {self._config.max_attempts} attempts failed validation for "
            f"{document_id!r}"
        )
        if last_report is not None:
            msg += f" (best grounding_score={last_report.grounding_score:.2f})"

        raise DocumentizerFailedError(
            msg,
            report=last_report,
            attempts=self._config.max_attempts,
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _validate(
        self, lesson: StructuredLesson, raw: RawDocument
    ) -> ValidationReport:
        policy = self._config.to_policy()

        gate_a = SchemaValidator().validate_structured_lesson(lesson)

        gate_b, provenance = SourceGroundingValidator(policy).validate_structured_lesson(
            lesson, raw
        )

        gate_c = ConfidenceValidator(policy).validate_structured_lesson(lesson)

        # Combined status.
        outcomes = [gate_a.outcome, gate_b.outcome, gate_c.outcome]
        if GateOutcome.FAIL in outcomes:
            status = GateOutcome.FAIL
        elif GateOutcome.WARN in outcomes:
            status = GateOutcome.WARN
        else:
            status = GateOutcome.PASS

        # If gate B score is missing (defensive), default to 0.
        score = gate_b.score if gate_b.score is not None else 0.0
        if status == GateOutcome.PASS and score < policy.grounding_threshold:
            # Defensive: never call a low-score lesson PASS.
            status = GateOutcome.FAIL

        issues: List[ValidationIssue] = []
        issues.extend(gate_a.issues)
        issues.extend(gate_b.issues)
        issues.extend(gate_c.issues)

        low_confidence_chunk_ids = [
            i.target
            for i in gate_c.issues
            if i.code == "low_confidence" and i.target
        ]

        return ValidationReport(
            status=status,
            schema_ok=(gate_a.outcome != GateOutcome.FAIL),
            grounding_score=score,
            low_confidence_chunk_ids=low_confidence_chunk_ids,
            gates=[gate_a, gate_b, gate_c],
            issues=issues,
            policy=policy,
            provenance=provenance,
        )


__all__ = [
    "DocumentizerFailedError",
    "DocumentizerPipeline",
    "DocumentizerPipelineConfig",
    "DocumentizerPipelineResult",
]