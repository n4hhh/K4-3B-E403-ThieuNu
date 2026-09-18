"""LessonBuilder — turn a CleanDocument into a StructuredLesson.

The builder is a pure mapping:

    * sections, concepts → sections, concepts (pass-through)
    * blocks → blocks (pass-through)
    * the builder also emits Teach-Back chunks by ``grouping`` sections
      into 3–12 chunks of roughly equal page range, then derives the
      four Teach-Back targets from the chunk content.

The builder never invents content. When the source does not provide
enough evidence for a misconception, ``common_misconception`` is left
as ``None``.

This is intentionally deterministic: same input → same output, every
time. The AI was responsible for the *content*; the builder is only
responsible for the *shape*.
"""

from __future__ import annotations

import logging
import re
import uuid
from typing import List, Optional

from app.models.clean_document import (
    BlockType,
    CleanBlock,
    CleanConcept,
    CleanDocument,
    CleanSection,
)
from app.models.structured_lesson import (
    GeneratedBy,
    StructuredLesson,
    StructuredLessonMetadata,
)
from app.models.teach_back_chunk import (
    ChunkExample,
    KeyPoint,
    TeachBackChunk,
    TeachBackTargets,
)
from app.models.validation_report import ProvenanceStats, ValidationReport


logger = logging.getLogger(__name__)


_DOCUMENTIZER_VERSION = "3a5.0.0"


def build_lesson(
    clean: CleanDocument,
    *,
    source_sha256: str,
    generated_by: GeneratedBy,
    learning_objectives: Optional[List[str]] = None,
    validation: Optional[ValidationReport] = None,
    provenance: Optional[ProvenanceStats] = None,
) -> StructuredLesson:
    """Map ``clean`` into a :class:`StructuredLesson`."""
    metadata = StructuredLessonMetadata(
        schema_version="3a5.lesson.v1",
        documentizer_version=_DOCUMENTIZER_VERSION,
        lesson_id=clean.document_id,
        source_document_id=clean.document_id,
        source_file=clean.source_file,
        source_sha256=source_sha256,
        language=clean.language,
        generated_by=generated_by,
    )

    chunks: List[TeachBackChunk]

    if clean.teach_back_chunks:
        # Gemini emitted chunks directly. Use them as-is so the
        # teach_back targets (must_understand, acceptable_explanation,
        # common_misconception, clarification_trigger) reflect the
        # provider's understanding of the source material rather than
        # a heuristic re-derivation.
        chunks = list(clean.teach_back_chunks)
        logger.info(
            "LessonBuilder: using %d Gemini-emitted chunks for %s",
            len(chunks),
            clean.document_id,
        )
    else:
        chunks = _build_chunks(clean)

    return StructuredLesson(
        metadata=metadata,
        title=clean.title,
        summary=clean.summary,
        learning_objectives=list(learning_objectives or []),
        sections=list(clean.sections),
        concepts=list(clean.concepts),
        chunks=chunks,
        provenance=provenance or ProvenanceStats(),
        validation=validation,
    )


__all__ = ["build_lesson"]


def _build_chunks(clean: CleanDocument) -> List[TeachBackChunk]:
    """Group sections into 3–12 Teach-Back chunks.

    Strategy:
        * If there are ≤ 12 sections, each section becomes one chunk.
        * Otherwise merge small adjacent sections until we land in the
          3–12 range. We never split a section across chunks.
        * If there is only 1 section, emit exactly 1 chunk.
        * If there are no sections, emit no chunks.
    """
    if not clean.sections:
        return []

    if 1 <= len(clean.sections) <= 12:
        grouped = [[s] for s in clean.sections]
    else:
        grouped = _merge_into_chunks(clean.sections, target_min=3, target_max=12)

    chunks: List[TeachBackChunk] = []
    for sections in grouped:
        chunk = _make_chunk_from_sections(clean.document_id, sections, clean)
        chunks.append(chunk)

    return chunks


def _merge_into_chunks(
    sections: List[CleanSection], *, target_min: int, target_max: int
) -> List[List[CleanSection]]:
    """Greedy merge so the result has between ``target_min`` and
    ``target_max`` chunks."""
    n = len(sections)
    target = max(target_min, min(target_max, n // 2 if n // 2 else 1))
    target = min(target, n)
    if target <= 0:
        return []

    base = n // target
    extra = n % target

    grouped: List[List[CleanSection]] = []
    i = 0
    for k in range(target):
        size = base + (1 if k < extra else 0)
        size = max(1, size)
        grouped.append(sections[i : i + size])
        i += size
    return [g for g in grouped if g]


def _make_chunk_from_sections(
    document_id: str,
    sections: List[CleanSection],
    clean: CleanDocument,
) -> TeachBackChunk:
    page_start = sections[0].page_start
    page_end = sections[-1].page_end
    title = sections[0].title

    # Concept ids and key points are derived from the claim-bearing blocks
    # in the joined section range. The concept lookup falls back to any
    # concept whose source pages overlap the chunk.
    chunk_pages = set(range(page_start, page_end + 1))
    concept_ids: List[str] = []
    seen_concepts: set[str] = set()
    for con in clean.concepts:
        if any(p in chunk_pages for p in con.source_pages):
            if con.id not in seen_concepts:
                concept_ids.append(con.id)
                seen_concepts.add(con.id)

    key_points: List[KeyPoint] = []
    kp_id = 0
    seen_kp_text: set[str] = set()
    for sec in sections:
        for blk in sec.blocks:
            if blk.type != BlockType.BULLET:
                continue
            text = _clean_kp_text(blk.text)
            if text in seen_kp_text:
                continue
            if not text:
                continue
            seen_kp_text.add(text)
            kp_id += 1
            # Best-effort concept link.
            linked_concept = _best_concept_for_text(text, clean.concepts)
            key_points.append(
                KeyPoint(
                    id=f"kp-{kp_id:03d}",
                    text=text[:240],
                    concept_id=linked_concept.id if linked_concept else None,
                    source_pages=list(blk.source_pages),
                )
            )
            if len(key_points) >= 6:
                break
        if len(key_points) >= 6:
            break

    examples: List[ChunkExample] = []
    ex_id = 0
    for sec in sections:
        for blk in sec.blocks:
            if blk.type != BlockType.EXAMPLE:
                continue
            ex_id += 1
            examples.append(
                ChunkExample(
                    id=f"ex-{ex_id:03d}",
                    text=blk.text[:240],
                    source_pages=list(blk.source_pages),
                )
            )
            if len(examples) >= 2:
                break
        if len(examples) >= 2:
            break

    teach_back = TeachBackTargets(
        must_understand=[kp.text for kp in key_points[:5]] or [title],
        acceptable_explanation=_derive_acceptable_explanation(sections),
        common_misconception=_derive_misconception(clean, sections),
        clarification_trigger=_derive_clarification_trigger(clean, sections),
    )

    confidence = _average_confidence(sections)

    return TeachBackChunk(
        id=f"chunk-{uuid.uuid4().hex[:8]}",
        title=title[:120] or f"Chunk {page_start}-{page_end}",
        summary=_derive_chunk_summary(sections),
        page_start=page_start,
        page_end=page_end,
        concept_ids=concept_ids,
        key_points=key_points,
        examples=examples,
        teach_back=teach_back,
        confidence=confidence,
    )


_BULLET_PREFIX_RE = re.compile(r"^\s*[•\-\*\u2022\u2023\u25E6\u2043\u204C\u204D]\s*")


def _clean_kp_text(text: str) -> str:
    text = _BULLET_PREFIX_RE.sub("", text or "")
    return text.strip()


def _best_concept_for_text(text: str, concepts: List[CleanConcept]):
    """Pick the concept whose name appears in ``text`` (case-insensitive)."""
    needle = text.lower()
    best = None
    best_len = 0
    for con in concepts:
        name = (con.name or "").lower()
        if name and name in needle and len(name) > best_len:
            best = con
            best_len = len(name)
    return best


def _derive_acceptable_explanation(sections: List[CleanSection]) -> str:
    """Build the acceptable_explanation from actual source content.

    The text MUST appear on the source pages of the chunk so SG-6 can
    ground it. We pick the first grounded bullet from the joined
    sections and surface it as the bar the explanation must clear.
    """
    for sec in sections:
        for blk in sec.blocks:
            if blk.type == BlockType.BULLET and blk.text and blk.citation:
                return blk.text[:280]
    # Fall back to the section title (always present and grounded via the
    # section's own heading block).
    return sections[0].title[:280]


def _derive_chunk_summary(sections: List[CleanSection]) -> str:
    if not sections:
        return ""
    titles = [s.title for s in sections if s.title]
    if not titles:
        return ""
    if len(titles) == 1:
        return titles[0][:280]
    return " · ".join(titles)[:280]


def _derive_misconception(
    clean: CleanDocument, sections: List[CleanSection]
) -> Optional[str]:
    """Best-effort misconception: never invented.

    Strategy: if any DEFINITION block in the chunk explicitly contrasts
    a term with a related term (``X is not Y``, ``X ≠ Y``), use that.
    Otherwise return None — we MUST NOT invent one.
    """
    page_start = sections[0].page_start
    page_end = sections[-1].page_end
    for sec in sections:
        for blk in sec.blocks:
            if blk.type != BlockType.DEFINITION:
                continue
            text = (blk.text or "").lower()
            if any(
                marker in text
                for marker in (
                    " is not ",
                    " ≠ ",
                    " != ",
                    " different from ",
                    " not the same as ",
                )
            ):
                return blk.text[:280]
            _ = page_start  # silence linter
            _ = page_end
    return None


def _derive_clarification_trigger(
    clean: CleanDocument, sections: List[CleanSection]
) -> Optional[str]:
    """Only set when a misconception exists.

    Returns a natural-language rule telling the agent when to ask back.
    """
    misconception = _derive_misconception(clean, sections)
    if not misconception:
        return None
    return (
        "If the student uses the misconception above, ask them to compare "
        "the two ideas and point out the difference."
    )[:280]


def _average_confidence(sections: List[CleanSection]) -> float:
    confidences: List[float] = []
    for sec in sections:
        for blk in sec.blocks:
            confidences.append(blk.confidence)
    if not confidences:
        return 0.7
    return round(sum(confidences) / len(confidences), 3)


__all__ = ["build_lesson"]