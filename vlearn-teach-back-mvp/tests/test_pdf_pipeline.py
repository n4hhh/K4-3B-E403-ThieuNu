"""Tests for the PDF-based lesson pipeline.

These tests build a synthetic PDF in a temporary directory, point the
service at it, and verify the full extraction → chunking flow. They do
NOT require any real PDF file to be present on disk.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.services.chunk_builder import ChunkBuilder
from app.services.pdf_lesson_service import PDFLessonService
from app.services.pdf_reader import PDFReader
from app.services.section_detector import SectionDetector


# Use a fixture directory for all tests so we never touch the real lesson dir.
@pytest.fixture()
def lesson_dir(tmp_path: Path) -> Path:
    return tmp_path / "lesson"


# ---------------------------------------------------------------------
# PDFReader
# ---------------------------------------------------------------------


def test_pdf_reader_extracts_pages(tmp_path: Path):
    from tests._make_pdf import write_synthetic_pdf

    pdf_path = write_synthetic_pdf(
        tmp_path / "sample.pdf",
        ["Hello world", "This is page two"],
    )

    reader = PDFReader()
    pages = reader.read_pages(pdf_path)

    assert len(pages) == 2
    assert pages[0].page_number == 1
    assert pages[1].page_number == 2
    assert "Hello world" in pages[0].text
    assert "page two" in pages[1].text


def test_pdf_reader_normalizes_whitespace(tmp_path: Path):
    from tests._make_pdf import write_synthetic_pdf

    pdf_path = write_synthetic_pdf(tmp_path / "ws.pdf", ["a    b\t\tc"])
    reader = PDFReader()
    pages = reader.read_pages(pdf_path)
    # Multiple internal spaces / tabs collapsed to single space.
    assert pages[0].text == "a b c"


def test_pdf_reader_handles_missing_file(tmp_path: Path):
    reader = PDFReader()
    with pytest.raises(FileNotFoundError):
        reader.read_pages(tmp_path / "does_not_exist.pdf")


def test_pdf_reader_returns_empty_for_empty_pdf(tmp_path: Path):
    """A PDF with zero content lines still yields one page with empty text."""
    from tests._make_pdf import write_synthetic_pdf

    pdf_path = write_synthetic_pdf(tmp_path / "empty.pdf", [""])
    reader = PDFReader()
    pages = reader.read_pages(pdf_path)
    assert len(pages) == 1
    assert pages[0].text == ""


# ---------------------------------------------------------------------
# SectionDetector
# ---------------------------------------------------------------------


def test_section_detector_finds_numbered_headings():
    from app.services.page_text import PageText

    pages = [
        PageText(1, "1. Introduction\nWelcome to the lesson."),
        PageText(2, "Some content."),
        PageText(3, "2. Methods\nWe discuss methods here."),
    ]
    sections = SectionDetector().detect(pages)
    assert len(sections) == 2
    assert "Introduction" in sections[0].title
    assert sections[0].start_page == 1
    assert sections[0].end_page == 2
    assert "Methods" in sections[1].title
    assert sections[1].start_page == 3


def test_section_detector_finds_chapter_headings():
    from app.services.page_text import PageText

    pages = [
        PageText(1, "Chapter 1: Getting Started"),
        PageText(2, "Body text here."),
    ]
    sections = SectionDetector().detect(pages)
    assert len(sections) == 1
    assert "Chapter 1" in sections[0].title


def test_section_detector_falls_back_to_per_page_when_no_headings():
    from app.services.page_text import PageText

    pages = [
        PageText(1, "Just a paragraph with no heading."),
        PageText(2, "Another page with no heading."),
    ]
    sections = SectionDetector().detect(pages)
    # No headings → one section per page
    assert len(sections) == 2


def test_section_detector_handles_empty_input():
    sections = SectionDetector().detect([])
    assert sections == []


def test_section_detector_ignores_short_caps_lines():
    from app.services.page_text import PageText

    pages = [PageText(1, "AB\nReal content here.")]
    sections = SectionDetector().detect(pages)
    # "AB" is too short to count as a heading.
    assert len(sections) == 1
    assert sections[0].start_page == 1


# ---------------------------------------------------------------------
# ChunkBuilder
# ---------------------------------------------------------------------


def test_chunk_builder_creates_one_chunk_per_section():
    from app.services.section_detector import DetectedSection
    from app.services.page_text import PageText

    sections = [
        DetectedSection(
            title="1. Intro",
            start_page=1,
            end_page=1,
            pages=[PageText(page_number=1, text="Intro body. It is short.")],
        ),
        DetectedSection(
            title="2. Body",
            start_page=2,
            end_page=3,
            pages=[PageText(page_number=2, text="Body line one."), PageText(page_number=3, text="Body line two.")],
        ),
    ]
    chunks = ChunkBuilder().build(sections)
    assert len(chunks) == 2
    assert chunks[0].title == "1. Intro"
    assert chunks[0].page_start == 1
    assert chunks[0].page_end == 1
    assert chunks[1].page_start == 2
    assert chunks[1].page_end == 3
    assert "Body line two" in chunks[1].content


def test_chunk_builder_slugifies_ids():
    from app.services.section_detector import DetectedSection
    from app.services.page_text import PageText

    sections = [
        DetectedSection(
            title="HTTP Methods & Status Codes!",
            start_page=1,
            end_page=1,
            pages=[PageText(page_number=1, text="content")],
        ),
    ]
    chunks = ChunkBuilder().build(sections)
    assert chunks[0].id.isascii() or chunks[0].id  # stable id
    assert "&" not in chunks[0].id and "!" not in chunks[0].id


def test_chunk_builder_extracts_key_points():
    from app.services.section_detector import DetectedSection
    from app.services.pdf_reader import PageText

    body = (
        "This is the first sentence about the topic. "
        "This is a second sentence. "
        "And a third sentence for completeness."
    )
    sections = [
        DetectedSection(
            title="X",
            start_page=1,
            end_page=1,
            pages=[PageText(1, body)],
        ),
    ]
    chunks = ChunkBuilder().build(sections)
    assert chunks[0].key_points
    assert all(isinstance(p, str) for p in chunks[0].key_points)


# ---------------------------------------------------------------------
# PDFLessonService
# ---------------------------------------------------------------------


def test_service_discovers_pdfs(lesson_dir: Path):
    from tests._make_pdf import write_synthetic_pdf

    write_synthetic_pdf(lesson_dir / "a.pdf", ["Page A"])
    write_synthetic_pdf(lesson_dir / "b.pdf", ["Page B"])
    svc = PDFLessonService(lesson_dir=lesson_dir)
    files = svc.discover()
    assert [p.name for p in files] == ["a.pdf", "b.pdf"]


def test_service_returns_empty_when_dir_missing(tmp_path: Path):
    svc = PDFLessonService(lesson_dir=tmp_path / "missing")
    assert svc.discover() == []
    assert svc.list_lessons() == []
    assert svc.get_summary() == []


def test_service_builds_lesson_from_pdf(lesson_dir: Path):
    from tests._make_pdf import write_synthetic_pdf

    write_synthetic_pdf(
        lesson_dir / "intro-to-rest.pdf",
        [
            "1. What is REST\nREST is an architectural style for APIs.",
            "2. HTTP Methods\nGET reads a resource. POST creates a resource.",
            "3. Status Codes\n2xx means success. 4xx means client error.",
        ],
    )
    svc = PDFLessonService(lesson_dir=lesson_dir)
    lessons = svc.list_lessons()
    assert len(lessons) == 1
    lesson = lessons[0]
    assert lesson.source_file == "intro-to-rest.pdf"
    assert lesson.total_pages == 3
    assert len(lesson.chunks) >= 2
    titles = [c.title for c in lesson.chunks]
    assert any("REST" in t for t in titles)
    assert all(c.page_start is not None for c in lesson.chunks)
    assert all(c.page_end is not None for c in lesson.chunks)
    # Full transcript should contain page text.
    assert "architectural style" in lesson.transcript


def test_service_id_is_deterministic_and_unique(lesson_dir: Path):
    from tests._make_pdf import write_synthetic_pdf

    write_synthetic_pdf(lesson_dir / "Lesson One.pdf", ["1. Topic\nBody."])
    write_synthetic_pdf(lesson_dir / "Lesson Two.pdf", ["1. Topic\nBody."])
    svc = PDFLessonService(lesson_dir=lesson_dir)
    lessons = svc.list_lessons()
    ids = [l.id for l in lessons]
    assert len(ids) == len(set(ids))


def test_service_skips_corrupted_pdf(lesson_dir: Path, caplog):
    from tests._make_pdf import write_synthetic_pdf

    write_synthetic_pdf(lesson_dir / "good.pdf", ["1. Title\nBody."])
    (lesson_dir / "bad.pdf").write_bytes(b"this is not a pdf")
    svc = PDFLessonService(lesson_dir=lesson_dir)
    lessons = svc.list_lessons()
    assert len(lessons) == 1
    assert lessons[0].source_file == "good.pdf"


def test_service_caches_results(lesson_dir: Path):
    from tests._make_pdf import write_synthetic_pdf

    write_synthetic_pdf(lesson_dir / "cached.pdf", ["1. Title\nBody."])
    svc = PDFLessonService(lesson_dir=lesson_dir)
    first = svc.list_lessons()
    second = svc.list_lessons()
    assert first == second
    # Same object instances (cache returns same list).
    assert svc.list_lessons() is svc.list_lessons()


# ---------------------------------------------------------------------
# LessonRepository integration
# ---------------------------------------------------------------------


def test_repository_uses_pdfs_when_available(tmp_path: Path):
    from tests._make_pdf import write_synthetic_pdf

    lesson_dir = tmp_path / "lessons"
    write_synthetic_pdf(lesson_dir / "x.pdf", ["1. Topic\nBody text here."])
    pdf_svc = PDFLessonService(lesson_dir=lesson_dir)

    from app.repositories.lesson_repository import LessonRepository

    repo = LessonRepository(pdf_service=pdf_svc)
    lessons = repo.list_lessons()
    assert repo.source == "pdf"
    assert len(lessons) == 1
    assert lessons[0].source_file == "x.pdf"


def test_repository_falls_back_to_json(tmp_path: Path):
    # PDF service returns nothing.
    pdf_svc = PDFLessonService(lesson_dir=tmp_path / "no_such_dir")
    json_path = tmp_path / "lessons.json"
    json_path.write_text(
        '{"lessons": [{"id": "json-lesson", "title": "From JSON", '
        '"summary": "s", "description": "d", "transcript": "t", '
        '"duration_minutes": 1, "chunks": []}], "quizzes": []}',
        encoding="utf-8",
    )

    from app.repositories.lesson_repository import LessonRepository

    repo = LessonRepository(pdf_service=pdf_svc, json_fallback=json_path)
    lessons = repo.list_lessons()
    assert repo.source == "json"
    assert len(lessons) == 1
    assert lessons[0].id == "json-lesson"


def test_repository_empty_when_no_source(tmp_path: Path):
    pdf_svc = PDFLessonService(lesson_dir=tmp_path / "no_dir")
    from app.repositories.lesson_repository import LessonRepository

    repo = LessonRepository(
        pdf_service=pdf_svc,
        json_fallback=tmp_path / "no_lessons.json",
    )
    assert repo.list_lessons() == []
    assert repo.source == "json"
