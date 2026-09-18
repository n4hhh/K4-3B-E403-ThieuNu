"""TranscriptLessonService — build lessons from VLearn transcript files.

The VLearn data pack ships six cleaned lecture transcripts as Markdown.
They are the richest grounding source we have: each paragraph carries a
citation code like ``[T04-021]``, which lets the teach-back agent point
at the exact passage a student should review — that is the "đối chiếu
nguồn" half of the D3 rubric.

Shape of a transcript file::

    # Transcript bài giảng (bản sạch) — Day 1 — Foundation
    > **Nguồn:** ...            <- metadata blockquote, skipped
    ## Lịch sử AI: Turing test và hai mùa đông
    **[T04-003]** Nội dung đoạn...
    **[T04-004]** Nội dung đoạn...

One file becomes one :class:`Lesson`; one ``##`` section becomes one
:class:`LessonChunk`.

The pack is **read-only**. We never write into it, and transcripts are
never copied into the repository — the data-pack rules forbid
redistributing them. Lessons are built in memory at startup.

Session length
--------------

A lecture holds 11–21 sections. Teaching back all of them would take an
hour, so a session keeps only the ``TEACH_BACK_MAX_CHUNKS`` most
substantial sections, in their original order. Housekeeping sections
(introductions, breaks, lab logistics) are dropped first — they contain
no teachable claim.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from app.models.lesson import Lesson, LessonChunk

logger = logging.getLogger(__name__)


# ``**[T04-021]** some text`` — the citation marker opening a paragraph.
_PARA_RE = re.compile(r"^\*\*\[(?P<code>T\d{2}-\d{3})\]\*\*\s*(?P<text>.+)$")
_H1_RE = re.compile(r"^#\s+(?P<title>.+?)\s*$")
_H2_RE = re.compile(r"^##\s+(?P<title>.+?)\s*$")

# Sections that exist for classroom logistics rather than content. A
# student cannot "teach back" a coffee break, and asking them to would
# make the agent look broken during a demo.
_HOUSEKEEPING_PATTERNS = (
    "chào lớp",
    "giới thiệu giảng viên",
    "khảo sát làm quen",
    "nội dung buổi học",
    "nội dung ngày học",
    "hoạt động lớp",
    "giờ giải lao",
    "trò chuyện bên lề",
    "bài lab",
    "bài tập cá nhân",
    "hỏi đáp về phạm vi",
    "lời kết",
)

# A section shorter than this has too little substance to teach back.
_MIN_SECTION_CHARS = 600


def slugify(value: str) -> str:
    """Return an ASCII, url-safe slug for ``value``.

    Vietnamese titles carry diacritics; ``NFKD`` + drop-combining gives
    a readable ASCII slug without pulling in a dependency.
    """
    decomposed = unicodedata.normalize("NFKD", value)
    ascii_only = "".join(c for c in decomposed if not unicodedata.combining(c))
    ascii_only = ascii_only.replace("đ", "d").replace("Đ", "D")
    ascii_only = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_only).strip("-").lower()
    return re.sub(r"-{2,}", "-", ascii_only) or "section"


class _Section:
    """One ``##`` section while the file is being parsed."""

    def __init__(self, title: str) -> None:
        self.title = title
        self.paragraphs: List[Tuple[str, str]] = []  # (citation code, text)

    @property
    def content(self) -> str:
        """Return the section body with citation codes preserved.

        The codes stay in the text on purpose: the validator is asked to
        cite them, so it has to be able to see them.
        """
        return "\n\n".join(f"[{code}] {text}" for code, text in self.paragraphs)

    @property
    def char_count(self) -> int:
        return sum(len(text) for _, text in self.paragraphs)

    @property
    def citation_range(self) -> Optional[str]:
        if not self.paragraphs:
            return None
        first, last = self.paragraphs[0][0], self.paragraphs[-1][0]
        return first if first == last else f"{first}–{last}"


class TranscriptLessonService:
    """Discovers and parses transcript Markdown into :class:`Lesson`s."""

    def __init__(
        self,
        transcript_dir: Path,
        max_chunks: int = 5,
        min_section_chars: int = _MIN_SECTION_CHARS,
    ) -> None:
        self._dir = Path(transcript_dir)
        self._max_chunks = max(1, max_chunks)
        self._min_section_chars = min_section_chars
        self._cache: Optional[List[Lesson]] = None

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def discover(self) -> List[Path]:
        """Return the transcript files, sorted by name.

        ``README.md`` documents the pack; it is not a lecture.
        """
        if not self._dir.is_dir():
            logger.info("Transcript directory %s does not exist.", self._dir)
            return []
        return sorted(
            p
            for p in self._dir.glob("*.md")
            if p.name.lower() != "readme.md"
        )

    def list_lessons(self) -> List[Lesson]:
        """Return every lesson built from the transcript directory."""
        if self._cache is not None:
            return self._cache

        lessons: List[Lesson] = []
        for path in self.discover():
            try:
                lesson = self.build_lesson(path)
            except OSError as exc:
                logger.warning("Could not read transcript %s: %s", path.name, exc)
                continue
            except Exception as exc:  # noqa: BLE001 - one bad file must not
                # take the whole catalogue down.
                logger.warning("Could not parse transcript %s: %s", path.name, exc)
                continue
            if lesson is not None:
                lessons.append(lesson)

        self._cache = lessons
        logger.info(
            "TranscriptLessonService built %d lesson(s) from %s.",
            len(lessons),
            self._dir,
        )
        return lessons

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    def build_lesson(self, path: Path) -> Optional[Lesson]:
        """Parse one transcript file into a :class:`Lesson`."""
        text = path.read_text(encoding="utf-8")
        title, sections = self._parse(text)
        if not sections:
            logger.info("Transcript %s has no usable sections.", path.name)
            return None

        selected = self._select_sections(sections)
        if not selected:
            logger.info("Transcript %s has no section long enough.", path.name)
            return None

        lesson_id = path.stem  # e.g. "transcript-04-clean"
        chunks: List[LessonChunk] = []
        for index, section in enumerate(selected, start=1):
            chunks.append(
                LessonChunk(
                    id=f"{lesson_id}-c{index}-{slugify(section.title)[:40]}",
                    title=section.title,
                    description=self._describe(section),
                    key_points=[],  # filled in by LessonPrepService
                    content=section.content,
                )
            )

        full_text = "\n\n".join(s.content for s in sections)
        # ~150 spoken words per minute; Vietnamese averages ~5 chars per word.
        duration = max(1, round(len(full_text) / (150 * 5)))

        return Lesson(
            id=lesson_id,
            title=self._clean_title(title or path.stem),
            summary=self._summarize(selected),
            description=(
                "Bài giảng được dựng từ transcript bản sạch của VLearn. "
                f"Phiên dạy lại gồm {len(chunks)} phần trọng tâm."
            ),
            transcript=full_text,
            duration_minutes=duration,
            chunks=chunks,
            source_file=path.name,
        )

    def _parse(self, text: str) -> Tuple[Optional[str], List[_Section]]:
        """Split raw Markdown into a title and its ``##`` sections."""
        title: Optional[str] = None
        sections: List[_Section] = []
        current: Optional[_Section] = None

        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue

            h1 = _H1_RE.match(stripped)
            if h1 and title is None:
                title = h1.group("title")
                continue

            h2 = _H2_RE.match(stripped)
            if h2:
                current = _Section(h2.group("title"))
                sections.append(current)
                continue

            para = _PARA_RE.match(stripped)
            if para and current is not None:
                current.paragraphs.append((para.group("code"), para.group("text")))

        return title, [s for s in sections if s.paragraphs]

    def _select_sections(self, sections: List[_Section]) -> List[_Section]:
        """Pick the sections worth teaching back, in their original order."""
        candidates = [
            s
            for s in sections
            if s.char_count >= self._min_section_chars and not self._is_housekeeping(s)
        ]
        if not candidates:
            # Nothing cleared the bar — fall back to the longest sections so
            # the lesson still exists rather than vanishing from the catalogue.
            candidates = sorted(sections, key=lambda s: s.char_count, reverse=True)[
                : self._max_chunks
            ]
            return sorted(candidates, key=lambda s: sections.index(s))

        if len(candidates) <= self._max_chunks:
            return candidates

        strongest = sorted(candidates, key=lambda s: s.char_count, reverse=True)[
            : self._max_chunks
        ]
        return sorted(strongest, key=lambda s: sections.index(s))

    @staticmethod
    def _is_housekeeping(section: _Section) -> bool:
        lowered = section.title.lower()
        return any(pattern in lowered for pattern in _HOUSEKEEPING_PATTERNS)

    @staticmethod
    def _clean_title(raw: str) -> str:
        """Turn the file's H1 into something a lesson card can show."""
        cleaned = re.sub(
            r"^Transcript bài giảng\s*\(bản sạch\)\s*[—-]\s*", "", raw
        ).strip()
        return cleaned or raw

    @staticmethod
    def _describe(section: _Section) -> str:
        """Return a one-line description shown above the chat composer."""
        if not section.paragraphs:
            return ""
        first = section.paragraphs[0][1]
        if len(first) <= 220:
            return first
        return first[:217].rsplit(" ", 1)[0] + "…"

    @staticmethod
    def _summarize(sections: List[_Section]) -> str:
        titles = " · ".join(s.title for s in sections[:4])
        return titles

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def source_map(self) -> Dict[str, str]:
        """Return ``{lesson_id: source filename}`` for the instructor log."""
        return {p.stem: p.name for p in self.discover()}


__all__ = ["TranscriptLessonService", "slugify"]
