"""Tests for the three validation gates.

Covers:

    Gate A — Schema validation (rejects inverted page ranges,
             missing must_understand, etc.)
    Gate B — Source grounding (SG-1..SG-7)
    Gate C — Confidence (low-confidence + hallucination guard)
"""

from __future__ import annotations

import pytest

from app.models.clean_document import (
    BlockType,
    CleanBlock,
    CleanConcept,
    CleanDocument,
    CleanSection,
    ConceptKind,
)
from app.models.raw_document import PageText, RawDocument
from app.models.structured_lesson import (
    GeneratedBy,
    StructuredLesson,
    StructuredLessonMetadata,
)
from app.models.teach_back_chunk import (
    TeachBackChunk,
    TeachBackTargets,
)
from app.models.validation_report import GateOutcome, ValidationPolicy
from app.services.validators import (
    ConfidenceValidator,
    SchemaValidator,
    SourceGroundingValidator,
)


def _raw() -> RawDocument:
    return RawDocument(
        document_id="d",
        source_file="d.pdf",
        source_path="d.pdf",
        page_count=2,
        pages=[
            PageText(page_number=1, text="REST API\nREST is an architectural style"),
            PageText(page_number=2, text="HTTP Methods\nGET retrieves a resource"),
        ],
    )


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


# ---------------------------------------------------------------------------
# Gate A
# ---------------------------------------------------------------------------


def test_schema_validator_catches_missing_must_understand():
    """Defensive: when the gate's view of the lesson has empty
    must_understand, it should flag the chunk.

    Bypasses the model validator via ``model_construct``.
    """
    from app.models.teach_back_chunk import TeachBackTargets as TBTT

    tb = TBTT.model_construct(
        must_understand=[],
        acceptable_explanation="exp",
        common_misconception=None,
        clarification_trigger=None,
    )
    chunk = TeachBackChunk.model_construct(
        id="c",
        title="c",
        summary="",
        page_start=1,
        page_end=1,
        concept_ids=[],
        key_points=[],
        examples=[],
        teach_back=tb,
        confidence=0.9,
    )
    lesson = StructuredLesson(metadata=_meta(), title="t", chunks=[chunk])
    res = SchemaValidator().validate_structured_lesson(lesson)
    codes = {i.code for i in res.issues}
    assert "chunk_must_understand_empty" in codes


def test_schema_validator_requires_clarification_trigger():
    """When the misconception is set without a trigger, the gate should
    flag it. We bypass Pydantic's own model validator via
    ``model_construct`` to construct an offending payload and assert
    the gate catches it."""
    from app.models.teach_back_chunk import TeachBackTargets as TBTT

    tb = TBTT.model_construct(
        must_understand=["x"],
        acceptable_explanation="exp",
        common_misconception="mis",
        clarification_trigger=None,
    )
    chunk = TeachBackChunk.model_construct(
        id="c",
        title="c",
        summary="",
        page_start=1,
        page_end=1,
        concept_ids=[],
        key_points=[],
        examples=[],
        teach_back=tb,
        confidence=0.9,
    )
    lesson = StructuredLesson(
        metadata=_meta(),
        title="t",
        chunks=[chunk],
    )
    res = SchemaValidator().validate_structured_lesson(lesson)
    codes = {i.code for i in res.issues}
    assert "chunk_clarification_required" in codes


# ---------------------------------------------------------------------------
# Gate B
# ---------------------------------------------------------------------------


def test_grounding_validator_passes_for_grounded_blocks():
    cd = CleanDocument(
        document_id="d",
        source_file="d.pdf",
        title="t",
        summary="",
        sections=[
            CleanSection(
                id="s1",
                title="REST API",
                page_start=1,
                page_end=2,
                blocks=[
                    CleanBlock(
                        id="b1",
                        type=BlockType.HEADING,
                        text="REST API",
                        source_pages=[1],
                        citation="REST API",
                    ),
                    CleanBlock(
                        id="b2",
                        type=BlockType.BULLET,
                        text="REST is an architectural style",
                        source_pages=[1],
                        citation="REST is an architectural style",
                    ),
                    CleanBlock(
                        id="b3",
                        type=BlockType.HEADING,
                        text="HTTP Methods",
                        source_pages=[2],
                        citation="HTTP Methods",
                    ),
                    CleanBlock(
                        id="b4",
                        type=BlockType.BULLET,
                        text="GET retrieves a resource",
                        source_pages=[2],
                        citation="GET retrieves a resource",
                    ),
                ],
            )
        ],
        concepts=[
            CleanConcept(
                id="c1",
                name="REST",
                summary="",
                source_pages=[1],
                citation="REST is an architectural style",
            )
        ],
    )
    res, prov = SourceGroundingValidator().validate_clean_document(cd, _raw())
    assert res.outcome.value in {"PASS", "WARN"}
    assert prov.grounded_blocks == 2


def test_grounding_validator_sg6_rejects_ungrounded_citation():
    """SG-6: an excerpt existing SOMEWHERE in the document is NOT
    sufficient; it must appear on one of the cited pages."""
    cd = CleanDocument(
        document_id="d",
        source_file="d.pdf",
        title="t",
        summary="",
        sections=[
            CleanSection(
                id="s1",
                title="s",
                page_start=1,
                page_end=1,
                blocks=[
                    CleanBlock(
                        id="b1",
                        type=BlockType.BULLET,
                        text="REST is an architectural style",
                        # Citation exists in document, but on page 2, not 1.
                        source_pages=[1],
                        citation="GET retrieves a resource",
                    ),
                ],
            )
        ],
        concepts=[],
    )
    res, _ = SourceGroundingValidator().validate_clean_document(cd, _raw())
    assert res.outcome.value == "FAIL"
    assert any(i.code == "SG-6" for i in res.issues)


def test_grounding_validator_sg1_rejects_empty_source_pages():
    cd = CleanDocument(
        document_id="d",
        source_file="d.pdf",
        title="t",
        summary="",
        sections=[
            CleanSection(
                id="s1",
                title="s",
                page_start=1,
                page_end=1,
                blocks=[
                    CleanBlock(
                        id="b1",
                        type=BlockType.BULLET,
                        text="x",
                        source_pages=[],
                        citation="x",
                    ),
                ],
            )
        ],
    )
    res, _ = SourceGroundingValidator().validate_clean_document(cd, _raw())
    assert any(i.code == "SG-1" for i in res.issues)


def test_grounding_validator_sg7_rejects_out_of_range_page():
    cd = CleanDocument(
        document_id="d",
        source_file="d.pdf",
        title="t",
        summary="",
        sections=[
            CleanSection(
                id="s1",
                title="s",
                page_start=1,
                page_end=1,
                blocks=[
                    CleanBlock(
                        id="b1",
                        type=BlockType.BULLET,
                        text="x",
                        source_pages=[99],  # past page_count
                        citation="x",
                    ),
                ],
            )
        ],
    )
    res, _ = SourceGroundingValidator().validate_clean_document(cd, _raw())
    assert any(i.code == "SG-7" for i in res.issues)


def test_grounding_validator_sg2_rejects_empty_citation():
    cd = CleanDocument(
        document_id="d",
        source_file="d.pdf",
        title="t",
        summary="",
        sections=[
            CleanSection(
                id="s1",
                title="s",
                page_start=1,
                page_end=1,
                blocks=[
                    CleanBlock(
                        id="b1",
                        type=BlockType.BULLET,
                        text="x",
                        source_pages=[1],
                        citation="",
                    ),
                ],
            )
        ],
    )
    res, _ = SourceGroundingValidator().validate_clean_document(cd, _raw())
    assert any(i.code == "SG-2" for i in res.issues)


def test_grounding_validator_flags_low_page_coverage():
    """If a page has 90% of its text ungrounded, the validator warns."""
    cd = CleanDocument(
        document_id="d",
        source_file="d.pdf",
        title="t",
        summary="",
        sections=[
            CleanSection(
                id="s1",
                title="s",
                page_start=1,
                page_end=1,
                blocks=[
                    CleanBlock(
                        id="b1",
                        type=BlockType.BULLET,
                        text="REST",
                        source_pages=[1],
                        citation="REST",
                    ),
                ],
            )
        ],
    )
    # Force the threshold to 0.99 so even tiny coverage drops below it.
    res, _ = SourceGroundingValidator(
        ValidationPolicy(page_coverage_floor=0.99)
    ).validate_clean_document(cd, _raw())
    assert any(i.code == "page_coverage_low" for i in res.issues)


# ---------------------------------------------------------------------------
# Gate C
# ---------------------------------------------------------------------------


def test_confidence_validator_flags_low_confidence_chunks():
    lesson = StructuredLesson(
        metadata=_meta(),
        title="t",
        chunks=[
            TeachBackChunk(
                id="c",
                title="c",
                summary="",
                page_start=1,
                page_end=1,
                teach_back=TeachBackTargets(
                    must_understand=["x"],
                    acceptable_explanation="exp",
                    common_misconception=None,
                    clarification_trigger=None,
                ),
                confidence=0.3,
            )
        ],
    )
    res = ConfidenceValidator(ValidationPolicy(min_confidence=0.65)).validate_structured_lesson(
        lesson
    )
    assert any(i.code == "low_confidence" for i in res.issues)


def test_confidence_validator_records_no_misconception():
    lesson = StructuredLesson(
        metadata=_meta(),
        title="t",
        chunks=[
            TeachBackChunk(
                id="c",
                title="c",
                summary="",
                page_start=1,
                page_end=1,
                teach_back=TeachBackTargets(
                    must_understand=["x"],
                    acceptable_explanation="exp",
                    common_misconception=None,
                    clarification_trigger=None,
                ),
                confidence=0.9,
            )
        ],
    )
    res = ConfidenceValidator().validate_structured_lesson(lesson)
    assert any(i.code == "no_misconception" for i in res.issues)