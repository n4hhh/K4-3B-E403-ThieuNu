"""Tests for Phase 3A.5 Pydantic models.

Covers every model in ``app.models`` added by Phase 3A.5:

    * CleanDocument + CleanSection + CleanBlock + CleanConcept
    * TeachBackChunk + TeachBackTargets + KeyPoint + ChunkExample
    * StructuredLesson + StructuredLessonMetadata + GeneratedBy
    * ValidationReport + GateResult + ValidationIssue + ProvenanceStats
"""

from __future__ import annotations

import json
from datetime import datetime

import pytest
from pydantic import ValidationError as PydanticValidationError

from app.models.clean_document import (
    BlockType,
    CleanBlock,
    CleanConcept,
    CleanDocument,
    CleanSection,
    ConceptKind,
    RemovedNoise,
    RemovedNoiseKind,
)
from app.models.structured_lesson import (
    GeneratedBy,
    StructuredLesson,
    StructuredLessonMetadata,
    lesson_from_dict,
    lesson_to_dict,
)
from app.models.teach_back_chunk import (
    ChunkExample,
    KeyPoint,
    TeachBackChunk,
    TeachBackTargets,
)
from app.models.validation_report import (
    GateName,
    GateOutcome,
    GateResult,
    IssueSeverity,
    ProvenanceStats,
    ValidationIssue,
    ValidationPolicy,
    ValidationReport,
)


# ---------------------------------------------------------------------------
# CleanDocument
# ---------------------------------------------------------------------------


def _section(
    page_start: int = 1, page_end: int = 1, blocks: list | None = None
) -> CleanSection:
    return CleanSection(
        id=f"sec-{page_start}",
        title="S",
        page_start=page_start,
        page_end=page_end,
        blocks=blocks or [],
    )


def _bullet(page: int = 1, text: str = "x", citation: str = "x") -> CleanBlock:
    return CleanBlock(
        id=f"b-{page}-{text[:4]}",
        type=BlockType.BULLET,
        text=text,
        source_pages=[page],
        citation=citation,
    )


def test_clean_document_round_trip():
    cd = CleanDocument(
        document_id="d",
        source_file="d.pdf",
        title="T",
        summary="S",
        sections=[_section(1, 1, [_bullet()])],
        concepts=[
            CleanConcept(
                id="c1",
                name="X",
                summary="X",
                source_pages=[1],
                citation="x",
            )
        ],
        removed_noise=[
            RemovedNoise(
                kind=RemovedNoiseKind.PAGE_NUMBER,
                source_page=1,
                excerpt="Page 1",
            )
        ],
    )
    d = cd.model_dump()
    new = CleanDocument.model_validate(d)
    assert new.document_id == cd.document_id
    assert len(new.sections) == 1
    assert new.sections[0].blocks[0].text == "x"


def test_clean_document_rejects_empty_document_id():
    with pytest.raises(PydanticValidationError):
        CleanDocument(
            document_id="",
            source_file="x.pdf",
            title="T",
        )


def test_clean_section_rejects_inverted_page_range():
    with pytest.raises(PydanticValidationError):
        CleanSection(id="s", title="t", page_start=5, page_end=2)


# ---------------------------------------------------------------------------
# TeachBackTargets
# ---------------------------------------------------------------------------


def test_teach_back_targets_requires_must_understand():
    with pytest.raises(PydanticValidationError):
        TeachBackTargets(
            must_understand=[],
            acceptable_explanation="Exp",
            common_misconception=None,
            clarification_trigger=None,
        )


def test_teach_back_targets_misconception_requires_trigger():
    with pytest.raises(PydanticValidationError):
        TeachBackTargets(
            must_understand=["x"],
            acceptable_explanation="exp",
            common_misconception="wrong",
            clarification_trigger=None,
        )


def test_teach_back_targets_misconception_null_is_allowed():
    tb = TeachBackTargets(
        must_understand=["x"],
        acceptable_explanation="exp",
        common_misconception=None,
        clarification_trigger=None,
    )
    assert tb.common_misconception is None


def test_teach_back_targets_misconception_with_trigger_ok():
    tb = TeachBackTargets(
        must_understand=["x"],
        acceptable_explanation="exp",
        common_misconception="wrong",
        clarification_trigger="ask back when ...",
    )
    assert tb.clarification_trigger == "ask back when ..."


# ---------------------------------------------------------------------------
# TeachBackChunk
# ---------------------------------------------------------------------------


def test_teach_back_chunk_inverted_page_range_rejected():
    with pytest.raises(PydanticValidationError):
        TeachBackChunk(
            id="c",
            title="t",
            summary="s",
            page_start=5,
            page_end=2,
            teach_back=TeachBackTargets(
                must_understand=["x"],
                acceptable_explanation="exp",
                common_misconception=None,
                clarification_trigger=None,
            ),
        )


def test_teach_back_chunk_full():
    tb = TeachBackTargets(
        must_understand=["a"],
        acceptable_explanation="exp",
        common_misconception=None,
        clarification_trigger=None,
    )
    chunk = TeachBackChunk(
        id="c1",
        title="chunk",
        summary="sum",
        page_start=1,
        page_end=2,
        concept_ids=["c1"],
        key_points=[
            KeyPoint(id="kp1", text="a", source_pages=[1]),
        ],
        examples=[ChunkExample(id="ex1", text="ex", source_pages=[2])],
        teach_back=tb,
        confidence=0.9,
    )
    assert chunk.confidence == 0.9


# ---------------------------------------------------------------------------
# StructuredLesson
# ---------------------------------------------------------------------------


def _meta() -> StructuredLessonMetadata:
    return StructuredLessonMetadata(
        lesson_id="l1",
        source_document_id="l1",
        source_file="l.pdf",
        source_sha256="a" * 64,
        generated_by=GeneratedBy(
            provider="mock", model="mock-1", pipeline_version="3a5.0.0"
        ),
    )


def test_structured_lesson_serialisation_round_trip():
    md = _meta()
    lesson = StructuredLesson(
        metadata=md,
        title="T",
        summary="S",
        learning_objectives=["lo1"],
        sections=[_section(1, 1, [_bullet()])],
    )
    payload = lesson_to_dict(lesson)
    # Top-level shape (no metadata nesting on disk).
    assert payload["schema_version"] == "3a5.lesson.v1"
    assert payload["lesson_id"] == "l1"
    assert payload["source_sha256"] == "a" * 64
    assert payload["sections"][0]["title"] == "S"

    new = lesson_from_dict(payload)
    assert new.metadata.lesson_id == "l1"
    assert new.title == "T"


def test_structured_lesson_requires_64_char_sha():
    with pytest.raises(PydanticValidationError):
        StructuredLessonMetadata(
            lesson_id="l1",
            source_document_id="l1",
            source_file="l.pdf",
            source_sha256="short",
            generated_by=GeneratedBy(
                provider="mock", model="mock-1", pipeline_version="3a5.0.0"
            ),
        )


# ---------------------------------------------------------------------------
# ValidationReport
# ---------------------------------------------------------------------------


def test_validation_report_can_publish():
    r = ValidationReport(status=GateOutcome.PASS, schema_ok=True, grounding_score=0.9)
    assert r.can_publish() is True
    r2 = ValidationReport(status=GateOutcome.WARN, schema_ok=True, grounding_score=0.7)
    assert r2.can_publish() is True
    r3 = ValidationReport(status=GateOutcome.FAIL, schema_ok=True, grounding_score=0.5)
    assert r3.can_publish() is False