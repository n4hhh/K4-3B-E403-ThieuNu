"""StructuredLessonAdapter — Phase 3A.5 → existing Lesson.

The existing UI / teaching loop expects a
:class:`~app.models.lesson.Lesson` with :class:`LessonChunk` items
that carry ``key_points`` and ``page_start`` / ``page_end``. We map
each :class:`~app.models.teach_back_chunk.TeachBackChunk` into a
:class:`LessonChunk`, preserving:

    * ``id``               ← ``chunk.id``
    * ``title``            ← ``chunk.title``
    * ``description``      ← ``chunk.summary``
    * ``key_points``       ← the chunk's own ``key_points``
    * ``quality_bar``      ← ``chunk.teach_back.acceptable_explanation``
    * ``content``          ← concatenated block text from the
                              sections the chunk covers
    * ``page_start``/``page_end`` ← from the chunk
    * ``key_concepts``     ← chunk ``concept_ids``

This adapter is the **only** place Phase 3A.5 touches the existing
UI contract. Nothing else in the existing codebase is required to
change.
"""

from __future__ import annotations

from typing import List

from app.models.clean_document import BlockType, CleanBlock, CleanSection
from app.models.lesson import Lesson, LessonChunk
from app.models.structured_lesson import StructuredLesson
from app.models.teach_back_chunk import TeachBackChunk


class StructuredLessonAdapter:
    """Map :class:`StructuredLesson` to :class:`Lesson`."""

    def to_lesson(self, structured: StructuredLesson) -> Lesson:
        chunks = [self._to_chunk(c, structured) for c in structured.chunks]
        return Lesson(
            id=structured.metadata.lesson_id,
            title=structured.title,
            summary=structured.summary,
            description=self._description_from_learning_objectives(
                structured.learning_objectives
            ),
            transcript=self._transcript_from_blocks(structured),
            duration_minutes=max(
                1,
                max((c.page_end for c in structured.chunks), default=1),
            ),
            chunks=chunks,
            source_file=structured.metadata.source_file,
            total_pages=max(
                (c.page_end for c in structured.chunks), default=0
            ),
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _to_chunk(
        self, chunk: TeachBackChunk, structured: StructuredLesson
    ) -> LessonChunk:
        sections = self._sections_for_chunk(chunk, structured)
        content = self._content_from_sections(sections)
        concept_names = [
            con.name
            for con in structured.concepts
            if con.id in chunk.concept_ids
        ]
        key_points = [kp.text for kp in chunk.key_points]

        return LessonChunk(
            id=chunk.id,
            title=chunk.title,
            description=chunk.summary or chunk.title,
            key_points=key_points,
            quality_bar=chunk.teach_back.acceptable_explanation,
            content=content,
            page_start=chunk.page_start,
            page_end=chunk.page_end,
            key_concepts=concept_names,
        )

    def _sections_for_chunk(
        self, chunk: TeachBackChunk, structured: StructuredLesson
    ) -> List[CleanSection]:
        return [
            sec
            for sec in structured.sections
            if not (sec.page_end < chunk.page_start or sec.page_start > chunk.page_end)
        ]

    @staticmethod
    def _content_from_sections(sections: List[CleanSection]) -> str:
        parts: List[str] = []
        for sec in sections:
            parts.append(sec.title)
            for blk in sec.blocks:
                if blk.type in (BlockType.HEADING, BlockType.BULLET):
                    parts.append(blk.text)
        return "\n".join(parts)

    @staticmethod
    def _transcript_from_blocks(structured: StructuredLesson) -> str:
        parts: List[str] = []
        for sec in structured.sections:
            for blk in sec.blocks:
                parts.append(blk.text)
        return "\n\n".join(parts)

    @staticmethod
    def _description_from_learning_objectives(los: List[str]) -> str:
        if not los:
            return ""
        bullets = "\n".join(f"- {lo}" for lo in los)
        return f"Learning objectives:\n{bullets}"


def structured_lesson_to_lesson(structured: StructuredLesson) -> Lesson:
    """Convenience wrapper for :class:`StructuredLessonAdapter`."""
    return StructuredLessonAdapter().to_lesson(structured)


__all__ = ["StructuredLessonAdapter", "structured_lesson_to_lesson"]