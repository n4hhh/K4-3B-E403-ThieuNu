"""ChunkBuilder — convert detected sections into LessonChunk objects.

The chunker is intentionally simple:

    * each detected section becomes one chunk
    * the ``content`` field holds the section text
    * ``key_concepts`` are extracted by picking salient noun phrases /
      short sentences from the section body
    * ``page_start`` / ``page_end`` are preserved for traceability
"""

from __future__ import annotations

import re
from typing import List

from app.models.lesson import LessonChunk
from app.services.section_detector import DetectedSection


# Matches short, complete sentences suitable as "key concepts".
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-ZÀ-Ỹ])")


class ChunkBuilder:
    """Build ``LessonChunk`` instances from sections."""

    def build(self, sections: List[DetectedSection]) -> List[LessonChunk]:
        """Return one ``LessonChunk`` per detected section."""
        chunks: List[LessonChunk] = []
        for idx, section in enumerate(sections, start=1):
            chunk = LessonChunk(
                id=self._slugify(section.title, idx),
                title=section.title,
                description=self._first_paragraph(section.content),
                content=section.content,
                key_points=self._extract_key_points(section.content),
                key_concepts=self._extract_key_concepts(section.content),
                quality_bar=None,
                page_start=section.start_page,
                page_end=section.end_page or section.start_page,
            )
            chunks.append(chunk)
        return chunks

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _slugify(title: str, fallback_index: int) -> str:
        """Generate a stable, URL-safe id for the chunk."""
        text = title.lower().strip()
        text = re.sub(r"[^a-z0-9à-ỹ\s-]", "", text)
        text = re.sub(r"\s+", "-", text)
        text = text.strip("-")
        return text or f"chunk-{fallback_index}"

    @staticmethod
    def _first_paragraph(content: str) -> str:
        """Return the first non-empty paragraph of the section, truncated."""
        if not content:
            return ""
        for para in content.split("\n\n"):
            para = para.strip()
            if para:
                return para[:280]
        return ""

    @staticmethod
    def _extract_key_points(content: str, limit: int = 5) -> List[str]:
        """Pick a handful of short sentences as ``key_points``.

        This is a deterministic fallback used by the existing UI / validator
        when no quiz JSON exists.
        """
        if not content:
            return []
        sentences = _SENTENCE_SPLIT_RE.split(content)
        points: List[str] = []
        for sentence in sentences:
            sentence = sentence.strip()
            if 12 <= len(sentence) <= 160:
                points.append(sentence)
            if len(points) >= limit:
                break
        if not points and content.strip():
            points = [content.strip()[:160]]
        return points

    @staticmethod
    def _extract_key_concepts(content: str, limit: int = 8) -> List[str]:
        """Extract simple ``key_concepts`` — capitalized noun phrases."""
        if not content:
            return []
        concept_re = re.compile(r"\b([A-ZÀ-Ỹ][a-zA-ZÀ-ỹ]{2,}(?:\s+[A-ZÀ-Ỹ][a-zA-ZÀ-ỹ]{2,})*)\b")
        seen: set[str] = set()
        out: List[str] = []
        for match in concept_re.finditer(content):
            phrase = match.group(1).strip()
            if phrase and phrase not in seen:
                seen.add(phrase)
                out.append(phrase)
            if len(out) >= limit:
                break
        return out
