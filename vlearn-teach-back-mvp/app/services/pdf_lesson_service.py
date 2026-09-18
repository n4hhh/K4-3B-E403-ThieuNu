"""PDFLessonService — discover PDFs and convert them into ``Lesson`` objects.

Pipeline
--------

    PDF file on disk
        ↓
    PDFReader.read_pages()           ← pypdf
        ↓
    List[PageText]
        ↓
    SectionDetector.detect()         ← heading heuristics
        ↓
    List[DetectedSection]
        ↓
    ChunkBuilder.build()             ← LessonChunk instances
        ↓
    Lesson                           ← with source_file + total_pages metadata

Caching
-------
Lessons are extracted once on first access and cached in-memory for the
lifetime of the process. No HTTP request triggers extraction work.

Fallback
--------
If the lesson directory does not exist or contains no PDFs, the service
returns an empty list. The caller (``LessonRepository``) decides whether
to fall back to the bundled ``data/lessons.json``.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from app.models.lesson import Lesson
from app.services.chunk_builder import ChunkBuilder
from app.services.pdf_reader import PDFReader
from app.services.section_detector import SectionDetector


logger = logging.getLogger(__name__)


@dataclass
class PDFLessonSummary:
    """Small summary describing a discovered PDF lesson."""

    filename: str
    lesson_id: str
    title: str
    total_pages: int
    chunk_count: int
    file_size_bytes: int


class PDFLessonService:
    """Service that turns PDFs in a directory into ``Lesson`` objects."""

    def __init__(
        self,
        lesson_dir: Path,
        reader: Optional[PDFReader] = None,
        detector: Optional[SectionDetector] = None,
        builder: Optional[ChunkBuilder] = None,
    ) -> None:
        self._lesson_dir = Path(lesson_dir)
        self._reader = reader or PDFReader()
        self._detector = detector or SectionDetector()
        self._builder = builder or ChunkBuilder()

        self._lessons: Dict[str, Lesson] = {}
        self._lessons_list: List[Lesson] = []
        self._summaries: List[PDFLessonSummary] = []
        self._summaries_list: List[PDFLessonSummary] = []
        self._loaded = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def lesson_dir(self) -> Path:
        return self._lesson_dir

    def discover(self) -> List[Path]:
        """Return the list of PDF files in the configured directory.

        Files are returned in sorted order so the demo lesson is
        deterministic.
        """
        if not self._lesson_dir.exists() or not self._lesson_dir.is_dir():
            return []
        return sorted(self._lesson_dir.glob("*.pdf"))

    def list_lessons(self) -> List[Lesson]:
        """Lazy-load all PDFs and return the resulting lessons."""
        self._ensure_loaded()
        # Return the cached list directly so repeated calls are O(1) and
        # callers can rely on object identity.
        return self._lessons_list

    def get_lesson(self, lesson_id: str) -> Optional[Lesson]:
        self._ensure_loaded()
        return self._lessons.get(lesson_id)

    def get_summary(self) -> List[PDFLessonSummary]:
        self._ensure_loaded()
        return self._summaries_list

    def reload(self) -> None:
        """Force re-extraction (mainly for tests)."""
        self._loaded = False
        self._lessons.clear()
        self._lessons_list = []
        self._summaries.clear()
        self._summaries_list = []
        self._ensure_loaded()

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        self._loaded = True

        pdfs = self.discover()
        if not pdfs:
            logger.warning(
                "No PDF lessons found in %s. "
                "LessonRepository will fall back to JSON if available.",
                self._lesson_dir,
            )
            return

        for pdf_path in pdfs:
            try:
                lesson = self._build_lesson_from_pdf(pdf_path)
            except Exception as exc:  # noqa: BLE001
                logger.error("Skipping PDF %s: %s", pdf_path.name, exc)
                continue

            self._lessons[lesson.id] = lesson
            try:
                size = pdf_path.stat().st_size
            except OSError:
                size = 0
            self._summaries.append(
                PDFLessonSummary(
                    filename=pdf_path.name,
                    lesson_id=lesson.id,
                    title=lesson.title,
                    total_pages=lesson.total_pages or 0,
                    chunk_count=len(lesson.chunks),
                    file_size_bytes=size,
                )
            )
            logger.info(
                "Loaded PDF lesson '%s' from %s (%d chunks, %d pages)",
                lesson.title,
                pdf_path.name,
                len(lesson.chunks),
                lesson.total_pages or 0,
            )

        # Build cached lists once after all PDFs are processed.
        self._lessons_list = list(self._lessons.values())
        self._summaries_list = list(self._summaries)

    # ------------------------------------------------------------------
    # Per-PDF building
    # ------------------------------------------------------------------

    def _build_lesson_from_pdf(self, pdf_path: Path) -> Lesson:
        pages = self._reader.read_pages(pdf_path)
        if not pages:
            raise ValueError(f"PDF contains no extractable pages: {pdf_path}")

        sections = self._detector.detect(pages)
        chunks = self._builder.build(sections)

        title = self._title_from_filename(pdf_path)
        summary = self._summary_from_chunks(chunks)
        description = self._description_from_chunks(chunks)

        # The transcript is the full text — used by the validator.
        transcript = "\n\n".join(p.text for p in pages if p.text)

        return Lesson(
            id=self._slugify(pdf_path.stem),
            title=title,
            summary=summary,
            description=description,
            transcript=transcript,
            duration_minutes=max(1, len(pages)),
            chunks=chunks,
            source_file=pdf_path.name,
            total_pages=len(pages),
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _slugify(text: str) -> str:
        """Build a stable kebab-case id from a string."""
        text = text.lower().strip()
        text = re.sub(r"[^a-z0-9à-ỹ\s-]", "", text)
        text = re.sub(r"\s+", "-", text)
        return text.strip("-") or "lesson"

    @staticmethod
    def _title_from_filename(pdf_path: Path) -> str:
        """Derive a human-friendly title from the PDF filename."""
        stem = pdf_path.stem.replace("_", " ").replace("-", " ").strip()
        # Title-case while preserving known all-caps acronyms.
        words = []
        for word in stem.split():
            if word.isupper() and len(word) <= 5:
                words.append(word)
            else:
                words.append(word.capitalize())
        return " ".join(words) or pdf_path.stem

    @staticmethod
    def _summary_from_chunks(chunks) -> str:
        """Build a short summary from the first chunk description."""
        if not chunks:
            return ""
        first = chunks[0]
        desc = first.description or first.title
        if len(desc) > 200:
            return desc[:197].rstrip() + "…"
        return desc

    @staticmethod
    def _description_from_chunks(chunks) -> str:
        """Build a multi-paragraph description from the chunk list."""
        if not chunks:
            return ""
        parts = []
        for chunk in chunks:
            line = f"• {chunk.title}"
            if chunk.description:
                line += f": {chunk.description}"
            parts.append(line)
        return "\n".join(parts)
