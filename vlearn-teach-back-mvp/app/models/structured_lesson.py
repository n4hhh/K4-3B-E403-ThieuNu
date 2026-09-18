"""StructuredLesson — Phase 3A.5 published schema.

A StructuredLesson is the **published** form of a lesson derived from a
RawDocument by the AI Documentizer. It carries:

    * slide-aligned sections with typed blocks (from the cleaned
      intermediate);
    * atomic concepts with provenance;
    * Teach-Back chunks with explicit targets;
    * aggregate provenance + last validation report;
    * versioned metadata (schema, documentizer, generation timestamps).

This model is persisted to ``data/processed/{doc_id}/published.json``.
The file is immutable once written — re-runs of the Documentizer
overwrite it (per Phase 3A.5 decisions: overwrite, not versioned).
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.clean_document import (
    BlockType,
    CleanBlock,
    CleanConcept,
    CleanSection,
    ConceptKind,
    DiagramBlock,
    RelationshipKind,
    TableBlock,
)
from app.models.teach_back_chunk import TeachBackChunk
from app.models.validation_report import ProvenanceStats, ValidationReport


class GeneratedBy(BaseModel):
    """Audit info: who/what produced this StructuredLesson."""

    provider: str = Field(..., description="AI provider name (e.g. 'gemini', 'mock')")
    model: str = Field(..., description="Provider model id (e.g. 'gemini-2.5-flash')")
    pipeline_version: str = Field(..., description="Phase 3A.5 pipeline version")


class StructuredLessonMetadata(BaseModel):
    """Document-level metadata."""

    schema_version: str = "3a5.lesson.v1"
    documentizer_version: str = "3a5.0.0"

    lesson_id: str = Field(..., description="Stable kebab-case lesson id")
    source_document_id: str = Field(..., description="RawDocument id")
    source_file: str = Field(..., description="Original PDF filename")
    source_sha256: str = Field(
        ...,
        min_length=64,
        max_length=64,
        description="SHA-256 of the source PDF (hex)",
    )

    language: str = "auto"
    generated_at: datetime = Field(default_factory=datetime.utcnow)

    generated_by: GeneratedBy = Field(..., description="Provenance of generation")


class StructuredLesson(BaseModel):
    """Top-level published lesson.

    This is the **only** object that gets serialised to
    ``published.json``. ``CleanDocument`` and ``LessonDraft`` are
    intermediate and never written to disk.
    """

    metadata: StructuredLessonMetadata = Field(..., alias="schema_version_data")
    title: str = Field(..., min_length=1)
    summary: str = ""
    learning_objectives: List[str] = Field(default_factory=list)

    sections: List[CleanSection] = Field(default_factory=list)
    concepts: List[CleanConcept] = Field(default_factory=list)
    chunks: List[TeachBackChunk] = Field(default_factory=list)

    provenance: ProvenanceStats = Field(default_factory=ProvenanceStats)
    validation: Optional[ValidationReport] = Field(
        default=None,
        description="Last validation report (may be None if never validated)",
    )

    model_config = {"populate_by_name": True}


# The ``StructuredLesson.metadata`` field is named "schema_version_data" so
# that the on-disk JSON shape stays close to the design (``schema_version``
# at the top level). The serialiser below flattens this back out so callers
# see ``metadata.schema_version`` cleanly.

StructuredLesson.__doc__ += (
    "\n\n    On-disk shape:\n"
    "        {\n"
    '          "schema_version": "3a5.lesson.v1",\n'
    '          "documentizer_version": "3a5.0.0",\n'
    '          "lesson_id": "...",\n'
    '          "source_document_id": "...",\n'
    '          "source_file": "...",\n'
    '          "source_sha256": "...",\n'
    '          "language": "auto",\n'
    '          "generated_at": "...",\n'
    '          "generated_by": {...},\n'
    '          "title": "...",\n'
    '          "summary": "...",\n'
    '          "learning_objectives": [...],\n'
    '          "sections": [...],\n'
    '          "concepts": [...],\n'
    '          "chunks": [...],\n'
    '          "provenance": {...},\n'
    '          "validation": {...}\n'
    "        }\n"
)


def lesson_to_dict(lesson: StructuredLesson) -> dict:
    """Serialise a StructuredLesson using the on-disk JSON shape.

    Flattening the ``metadata`` object into the top level keeps
    ``published.json`` close to the Phase 3A.5 design doc.
    """
    payload = lesson.model_dump(by_alias=True, mode="json")
    md = payload.pop("schema_version_data", {}) or {}
    # Flatten metadata fields back to the top level.
    for key, value in md.items():
        if key in payload:
            # Don't clobber explicit top-level fields if any collide.
            continue
        payload[key] = value
    # Always expose schema_version/documentizer_version at top level.
    if "schema_version" not in payload:
        payload["schema_version"] = md.get("schema_version", "3a5.lesson.v1")
    if "documentizer_version" not in payload:
        payload["documentizer_version"] = md.get("documentizer_version", "3a5.0.0")
    return payload


def lesson_from_dict(payload: dict) -> StructuredLesson:
    """Inverse of :func:`lesson_to_dict`.

    Accepts the flattened on-disk shape and re-hydrates into a
    StructuredLesson with ``metadata`` populated.
    """
    payload = dict(payload)
    md_keys = {f for f in StructuredLessonMetadata.model_fields}
    md = {}
    for k in list(payload.keys()):
        if k in md_keys:
            md[k] = payload.pop(k)
    return StructuredLesson(schema_version_data=md, **payload)


__all__ = [
    "GeneratedBy",
    "StructuredLesson",
    "StructuredLessonMetadata",
    "lesson_from_dict",
    "lesson_to_dict",
    # Re-exports so callers can import block types from one place.
    "BlockType",
    "CleanBlock",
    "CleanConcept",
    "CleanSection",
    "ConceptKind",
    "DiagramBlock",
    "RelationshipKind",
    "TableBlock",
    "TeachBackChunk",
    "ProvenanceStats",
    "ValidationReport",
]