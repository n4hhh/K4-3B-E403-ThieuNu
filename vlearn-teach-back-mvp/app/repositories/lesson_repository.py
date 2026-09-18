"""LessonRepository — exposes lessons to the rest of the app.

Lesson source priority:

    1. Lecture transcripts parsed by ``TranscriptLessonService`` from the
       VLearn data pack (``data/vlearn-pack/transcript``). These carry
       per-paragraph citation codes, so the teach-back agent can point at
       the exact passage behind a verdict.
    2. PDFs discovered by ``PDFLessonService`` in ``VLEARN_LESSON_DIR``
       (or the default ``../data/lesson``).
    3. Fallback to ``data/lessons.json`` when neither is available.

Transcripts and PDFs are merged into one catalogue: a deployment with
both slide decks and transcripts shows both. The JSON fallback is used
only when nothing else produced a lesson, so a fresh checkout without
the data pack still has something clickable.

The repository never reads source files on the HTTP path — all
extraction is performed once at startup (or on first call) and cached.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

from app.config import JSON_FALLBACK_FILE
from app.models.lesson import Lesson, Quiz
from app.repositories.published_lesson_repository import (
    PublishedLessonRepository,
)
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    # Imported only for type checking to avoid a runtime circular
    # import: app.services.__init__ imports app.services.lesson_service
    # which imports app.repositories.lesson_repository.
    from app.services.pdf_lesson_service import PDFLessonService


logger = logging.getLogger(__name__)


class LessonRepository:
    """Reads lessons, preferring PDFs over the JSON fallback."""

    def __init__(
        self,
        pdf_service: Optional[PDFLessonService] = None,
        json_fallback: Optional[Path] = None,
        # Backward-compat aliases. Older callers (and existing tests) pass
        # ``lessons_file=`` to point at a specific JSON file.
        lessons_file: Optional[Path] = None,
        # Phase 3A.5 — when provided, the repository prefers published
        # StructuredLessons over PDF-derived lessons (when available).
        published_repo: Optional[PublishedLessonRepository] = None,
        # Teach-Back — lessons built from the data pack's transcripts.
        transcript_service: Optional[object] = None,
    ) -> None:
        self._pdf_service = pdf_service
        self._transcript_service = transcript_service
        if json_fallback is None and lessons_file is not None:
            json_fallback = Path(lessons_file)
        self._json_fallback = (
            Path(json_fallback) if json_fallback is not None else JSON_FALLBACK_FILE
        )
        self._published_repo = published_repo

        self._lessons: Dict[str, Lesson] = {}
        self._quizzes: Dict[str, Quiz] = {}
        self._lessons_list: List[Lesson] = []
        self._loaded = False
        self._source: str = "unloaded"

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def _load(self) -> None:
        """Load lessons from PDF (preferred) or JSON (fallback)."""
        if self._loaded:
            return
        self._loaded = True

        sources: List[str] = []

        if self._transcript_service is not None:
            try:
                transcript_lessons = self._transcript_service.list_lessons()
            except Exception as exc:  # noqa: BLE001 - never block startup
                logger.warning("TranscriptLessonService failed: %s", exc)
                transcript_lessons = []
            if transcript_lessons:
                for lesson in transcript_lessons:
                    self._lessons[lesson.id] = lesson
                sources.append("transcript")
                logger.info(
                    "LessonRepository loaded %d lesson(s) from transcripts.",
                    len(transcript_lessons),
                )

        if self._pdf_service is not None:
            pdf_lessons = self._pdf_service.list_lessons()
            if pdf_lessons:
                for lesson in pdf_lessons:
                    self._lessons[lesson.id] = lesson
                sources.append("pdf")
                logger.info(
                    "LessonRepository loaded %d lesson(s) from PDFs.",
                    len(pdf_lessons),
                )

        if self._lessons:
            self._lessons_list = list(self._lessons.values())
            self._source = "+".join(sources)
            self._overlay_published_lessons()
            return

        logger.info(
            "No transcript or PDF lessons — falling back to JSON at %s.",
            self._json_fallback,
        )
        self._load_from_json()
        self._lessons_list = list(self._lessons.values())
        self._source = "json"
        self._overlay_published_lessons()

    def _overlay_published_lessons(self) -> None:
        """Phase 3A.5 overlay — replace each PDF-derived lesson with
        its published (StructuredLesson → Lesson adapter) form when one
        exists. Lessons without a ``published.json`` are kept as-is.

        This is purely additive: if the overlay repo is not configured,
        or no published lesson matches, the existing behaviour is
        preserved.
        """
        if self._published_repo is None:
            return

        # Lazy import: avoid hard dependency for code paths that do not
        # use the adapter (e.g. JSON-fallback deployments).
        try:
            from app.adapters.structured_lesson_adapter import (
                StructuredLessonAdapter,
            )
        except ImportError:  # pragma: no cover - defensive
            logger.warning(
                "StructuredLessonAdapter unavailable; "
                "skipping published-lesson overlay."
            )
            return

        adapter = StructuredLessonAdapter()
        overlaid = 0
        for lesson_id in list(self._lessons.keys()):
            structured = self._published_repo.load(lesson_id)
            if structured is None:
                continue
            try:
                adapted = adapter.to_lesson(structured)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Failed to adapt published lesson %s: %s — "
                    "keeping the PDF-derived version.",
                    lesson_id,
                    exc,
                )
                continue
            self._lessons[lesson_id] = adapted
            overlaid += 1
        if overlaid:
            self._lessons_list = list(self._lessons.values())
            logger.info(
                "LessonRepository overlaid %d lesson(s) with Phase 3A.5 "
                "published versions.",
                overlaid,
            )

    def _load_from_json(self) -> None:
        if not self._json_fallback.exists():
            logger.warning(
                "No PDF lessons and no JSON fallback at %s.",
                self._json_fallback,
            )
            return
        try:
            with self._json_fallback.open("r", encoding="utf-8") as fh:
                payload = json.load(fh)
        except (OSError, json.JSONDecodeError) as exc:
            logger.error("Failed to load JSON fallback: %s", exc)
            return

        for lesson_data in payload.get("lessons", []):
            lesson = Lesson.model_validate(lesson_data)
            self._lessons[lesson.id] = lesson

        for quiz_data in payload.get("quizzes", []):
            quiz = Quiz.model_validate(quiz_data)
            self._quizzes[quiz.lesson_id] = quiz

        logger.info(
            "LessonRepository loaded %d lesson(s) from JSON fallback.",
            len(self._lessons),
        )

    # ------------------------------------------------------------------
    # Read API
    # ------------------------------------------------------------------

    def list_lessons(self) -> List[Lesson]:
        self._load()
        # Return the cached list directly so repeated calls are O(1).
        return self._lessons_list

    def get_lesson(self, lesson_id: str) -> Optional[Lesson]:
        self._load()
        return self._lessons.get(lesson_id)

    def get_quiz(self, lesson_id: str) -> Optional[Quiz]:
        self._load()
        return self._quizzes.get(lesson_id)

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    @property
    def source(self) -> str:
        """Return which source supplied the lessons (``pdf`` / ``json``)."""
        self._load()
        return self._source

    @property
    def pdf_service(self) -> Optional[PDFLessonService]:
        return self._pdf_service
