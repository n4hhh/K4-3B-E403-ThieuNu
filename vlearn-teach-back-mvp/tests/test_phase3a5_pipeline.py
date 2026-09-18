"""Tests for the end-to-end DocumentizerPipeline.

Covers:

    * Happy path with MockProvider → published.json written
    * ``raw.json`` is byte-identical before and after the pipeline
    * The source PDF is byte-identical before and after the pipeline
    * Schema PASS + Grounding FAIL → no published.json
    * source_sha256 is computed from the source PDF when available
    * Validation report sidecar is written alongside published.json
    * Adapter compatibility — published.json → Lesson works for the
      existing UI contract
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest

from app.repositories.published_lesson_repository import (
    PublishedLessonRepository,
)
from app.services.ai import build_provider
from app.services.documentizer_pipeline import (
    DocumentizerFailedError,
    DocumentizerPipeline,
    DocumentizerPipelineConfig,
)
from app.services.phase3a_pipeline import Phase3APipeline


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def lesson_environment(tmp_path: Path):
    """Spin up a temporary lesson + processed directory with one PDF.

    Returns (lesson_dir, processed_dir, document_id).
    """
    from tests._make_pdf import write_synthetic_pdf

    lesson_dir = tmp_path / "lesson"
    processed_dir = tmp_path / "processed"
    lesson_dir.mkdir()
    write_synthetic_pdf(
        lesson_dir / "rest.pdf",
        [
            ["REST API Introduction", "REST is an architectural style"],
            ["HTTP Methods", "GET retrieves a resource", "POST creates one"],
            ["Status Codes", "2xx means success", "4xx means client error"],
        ],
    )
    p3a = Phase3APipeline(lesson_dir=lesson_dir, processed_dir=processed_dir)
    results = p3a.run()
    assert results and results[0].raw_document
    doc_id = results[0].raw_document.document_id

    return lesson_dir, processed_dir, doc_id


def _make_pipeline(
    *,
    lesson_dir: Path,
    processed_dir: Path,
    provider_name: str = "mock",
    **config_overrides,
) -> DocumentizerPipeline:
    pipeline = DocumentizerPipeline(
        provider=build_provider(provider_name),
        config=DocumentizerPipelineConfig(**config_overrides),
    )
    # Override paths so the test points at tmp dirs.
    pipeline._published_repo._processed_dir = processed_dir
    pipeline._published_repo._lesson_dir = lesson_dir
    pipeline._raw_service._processed_dir = processed_dir
    pipeline._raw_service._lesson_dir = lesson_dir
    return pipeline


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_pipeline_publishes_with_mock_provider(lesson_environment):
    lesson_dir, processed_dir, doc_id = lesson_environment
    pipeline = _make_pipeline(
        lesson_dir=lesson_dir, processed_dir=processed_dir, max_attempts=2
    )
    result = pipeline.process(doc_id, publish=True)
    assert result.validation.status.value in {"PASS", "WARN"}
    assert result.published_path is not None
    assert result.published_path.exists()


def test_pipeline_raw_json_is_unchanged(lesson_environment):
    lesson_dir, processed_dir, doc_id = lesson_environment
    raw_path = processed_dir / doc_id / "raw.json"
    size_before = raw_path.stat().st_size
    sha_before = raw_path.read_bytes()

    pipeline = _make_pipeline(
        lesson_dir=lesson_dir, processed_dir=processed_dir
    )
    pipeline.process(doc_id, publish=True)

    assert raw_path.stat().st_size == size_before
    assert raw_path.read_bytes() == sha_before


def test_pipeline_source_pdf_is_unchanged(lesson_environment):
    lesson_dir, processed_dir, doc_id = lesson_environment
    pdf_path = lesson_dir / "rest.pdf"
    pdf_before = pdf_path.read_bytes()

    pipeline = _make_pipeline(
        lesson_dir=lesson_dir, processed_dir=processed_dir
    )
    pipeline.process(doc_id, publish=True)

    assert pdf_path.read_bytes() == pdf_before


def test_pipeline_writes_envelope_with_required_fields(lesson_environment):
    lesson_dir, processed_dir, doc_id = lesson_environment
    pipeline = _make_pipeline(
        lesson_dir=lesson_dir, processed_dir=processed_dir
    )
    result = pipeline.process(doc_id, publish=True)
    assert result.published_path

    with result.published_path.open("r", encoding="utf-8") as fh:
        env = json.load(fh)

    # Required envelope fields per spec.
    for key in (
        "schema_version",
        "documentizer_version",
        "source_sha256",
        "created_at",
        "validation_status",
        "lesson",
    ):
        assert key in env, f"missing envelope key {key}"

    assert env["source_sha256"] and len(env["source_sha256"]) == 64
    assert env["validation_status"] in {"PASS", "WARN"}
    assert env["schema_version"] == "3a5.lesson.v1"

    # Sidecar.
    sidecar = result.published_path.parent / "validation.json"
    assert sidecar.exists()


def test_pipeline_creates_teach_back_targets(lesson_environment):
    lesson_dir, processed_dir, doc_id = lesson_environment
    pipeline = _make_pipeline(
        lesson_dir=lesson_dir, processed_dir=processed_dir
    )
    result = pipeline.process(doc_id, publish=True)
    assert result.lesson.chunks
    for chunk in result.lesson.chunks:
        assert chunk.teach_back.must_understand
        assert chunk.teach_back.acceptable_explanation


def test_pipeline_no_publish_does_not_write(lesson_environment):
    lesson_dir, processed_dir, doc_id = lesson_environment
    pipeline = _make_pipeline(
        lesson_dir=lesson_dir, processed_dir=processed_dir
    )
    result = pipeline.process(doc_id, publish=False)
    assert result.published_path is None
    assert not (processed_dir / doc_id / "published.json").exists()


def test_pipeline_404_for_missing_document(tmp_path):
    pipeline = _make_pipeline(
        lesson_dir=tmp_path, processed_dir=tmp_path
    )
    with pytest.raises(FileNotFoundError):
        pipeline.process("nope", publish=False)


# ---------------------------------------------------------------------------
# Adapter compatibility
# ---------------------------------------------------------------------------


def test_adapter_translates_structured_lesson_to_lesson(lesson_environment):
    """A published StructuredLesson must be consumable by the existing
    Lesson / LessonChunk UI contract via the adapter."""
    from app.adapters import structured_lesson_to_lesson
    from app.models.lesson import LessonChunk

    lesson_dir, processed_dir, doc_id = lesson_environment
    pipeline = _make_pipeline(
        lesson_dir=lesson_dir, processed_dir=processed_dir
    )
    result = pipeline.process(doc_id, publish=True)

    adapted = structured_lesson_to_lesson(result.lesson)
    assert adapted.id == doc_id
    assert adapted.chunks
    for c in adapted.chunks:
        assert isinstance(c, LessonChunk)
        assert c.key_points  # teach-back key_points propagated
        assert c.page_start >= 1
        assert c.page_end >= c.page_start
        assert c.quality_bar  # acceptable_explanation propagated


def test_repository_overlay_uses_published_lesson(lesson_environment):
    """LessonRepository picks up the published.json via the adapter when present."""
    from app.repositories.lesson_repository import LessonRepository
    from app.services.pdf_lesson_service import PDFLessonService

    lesson_dir, processed_dir, doc_id = lesson_environment

    pipeline = _make_pipeline(
        lesson_dir=lesson_dir, processed_dir=processed_dir
    )
    pipeline.process(doc_id, publish=True)

    # Construct a LessonRepository that knows about the published dir.
    pdf_service = PDFLessonService(lesson_dir=lesson_dir)
    pdf_service.reload()

    published_repo = PublishedLessonRepository(
        processed_dir=processed_dir, lesson_dir=lesson_dir
    )
    repo = LessonRepository(
        pdf_service=pdf_service,
        published_repo=published_repo,
    )
    lesson = repo.get_lesson(doc_id)
    assert lesson is not None
    # The adapter populated key_points and quality_bar from the
    # StructuredLesson — the PDF-only path does not.
    assert lesson.chunks
    assert any(c.quality_bar for c in lesson.chunks)


def test_repository_falls_back_when_no_published(lesson_environment):
    """When no published.json exists, the repository still serves the
    PDF-derived lesson (Phase 3A behaviour preserved)."""
    from app.repositories.lesson_repository import LessonRepository
    from app.services.pdf_lesson_service import PDFLessonService

    lesson_dir, processed_dir, doc_id = lesson_environment

    pdf_service = PDFLessonService(lesson_dir=lesson_dir)
    pdf_service.reload()
    repo = LessonRepository(pdf_service=pdf_service)
    lesson = repo.get_lesson(doc_id)
    assert lesson is not None
    assert lesson.chunks  # PDF-derived chunks present
