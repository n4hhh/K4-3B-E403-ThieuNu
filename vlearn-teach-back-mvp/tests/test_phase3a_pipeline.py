"""Tests for Phase 3A: PDF to RawDocument pipeline.

These tests verify:
- PDF discovery
- Text extraction
- RawDocument generation
- Storage and retrieval
- Pipeline orchestration

IMPORTANT: No Gemini calls in Phase 3A tests.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.models.raw_document import PageText, RawDocument
from app.services.phase3a_pipeline import Phase3APipeline
from app.services.pdf_reader import PDFReader
from app.services.raw_document_service import RawDocumentService


# ---------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------


@pytest.fixture()
def lesson_dir(tmp_path: Path) -> Path:
    """Create a temporary lesson directory."""
    return tmp_path / "lesson"


@pytest.fixture()
def processed_dir(tmp_path: Path) -> Path:
    """Create a temporary processed directory."""
    return tmp_path / "processed"


@pytest.fixture()
def pdf_reader(lesson_dir: Path) -> PDFReader:
    """Create a PDFReader with the test lesson directory."""
    return PDFReader(lesson_dir=lesson_dir)


@pytest.fixture()
def raw_doc_service(processed_dir: Path, lesson_dir: Path) -> RawDocumentService:
    """Create a RawDocumentService with test directories."""
    return RawDocumentService(processed_dir=processed_dir, lesson_dir=lesson_dir)


@pytest.fixture()
def phase3a_pipeline(
    lesson_dir: Path,
    processed_dir: Path,
    pdf_reader: PDFReader,
    raw_doc_service: RawDocumentService,
) -> Phase3APipeline:
    """Create a Phase3APipeline with test dependencies."""
    return Phase3APipeline(
        lesson_dir=lesson_dir,
        processed_dir=processed_dir,
        pdf_reader=pdf_reader,
        raw_doc_service=raw_doc_service,
    )


# ---------------------------------------------------------------------
# PDFReader Tests
# ---------------------------------------------------------------------


def test_pdf_reader_discovers_pdfs(lesson_dir: Path):
    """Test PDF discovery returns empty list when no PDFs exist."""
    from tests._make_pdf import write_synthetic_pdf

    # Create some PDFs
    write_synthetic_pdf(lesson_dir / "a.pdf", ["Page A"])
    write_synthetic_pdf(lesson_dir / "b.pdf", ["Page B"])

    reader = PDFReader(lesson_dir=lesson_dir)
    pdfs = reader.discover_pdfs()

    assert len(pdfs) == 2
    assert [p.name for p in pdfs] == ["a.pdf", "b.pdf"]


def test_pdf_reader_returns_empty_for_missing_dir():
    """Test PDF discovery returns empty list for missing directory."""
    reader = PDFReader(lesson_dir=Path("nonexistent"))
    pdfs = reader.discover_pdfs()
    assert pdfs == []


def test_pdf_reader_returns_empty_for_empty_dir(lesson_dir: Path):
    """Test PDF discovery returns empty list for empty directory."""
    reader = PDFReader(lesson_dir=lesson_dir)
    pdfs = reader.discover_pdfs()
    assert pdfs == []


def test_pdf_reader_extracts_pages(tmp_path: Path):
    """Test page extraction from a synthetic PDF."""
    from tests._make_pdf import write_synthetic_pdf

    pdf_path = write_synthetic_pdf(
        tmp_path / "sample.pdf",
        ["Hello world", "This is page two", "Page three content"],
    )

    reader = PDFReader()
    pages = reader.read_pages(pdf_path)

    assert len(pages) == 3
    assert pages[0].page_number == 1
    assert pages[1].page_number == 2
    assert pages[2].page_number == 3
    assert "Hello world" in pages[0].text
    assert "page two" in pages[1].text
    assert "three" in pages[2].text


def test_pdf_reader_handles_missing_file():
    """Test that missing file raises FileNotFoundError."""
    reader = PDFReader()
    with pytest.raises(FileNotFoundError):
        reader.read_pages(Path("nonexistent.pdf"))


def test_pdf_reader_get_page_count(tmp_path: Path):
    """Test page count extraction without full text extraction."""
    from tests._make_pdf import write_synthetic_pdf

    pdf_path = write_synthetic_pdf(
        tmp_path / "count.pdf",
        ["Page 1", "Page 2", "Page 3", "Page 4", "Page 5"],
    )

    reader = PDFReader()
    count = reader.get_page_count(pdf_path)
    assert count == 5


def test_pdf_reader_extracts_raw_document(tmp_path: Path):
    """Test complete RawDocument extraction."""
    from tests._make_pdf import write_synthetic_pdf

    pdf_path = write_synthetic_pdf(
        tmp_path / "test.pdf",
        ["First page content", "Second page content", "Third page content"],
    )

    reader = PDFReader()
    raw_doc = reader.extract_raw_document(pdf_path)

    assert raw_doc.document_id == "test"
    assert raw_doc.source_file == "test.pdf"
    # source_path should store only the filename (relative), not absolute filesystem paths
    assert raw_doc.source_path == "test.pdf"
    assert raw_doc.page_count == 3
    assert len(raw_doc.pages) == 3
    assert raw_doc.has_text is True
    assert raw_doc.total_words > 0


def test_pdf_reader_normalizes_whitespace(tmp_path: Path):
    """Test that whitespace is normalized correctly."""
    from tests._make_pdf import write_synthetic_pdf

    pdf_path = write_synthetic_pdf(tmp_path / "ws.pdf", ["a    b\t\tc"])
    reader = PDFReader()
    pages = reader.read_pages(pdf_path)
    # Multiple internal spaces / tabs collapsed to single space
    assert pages[0].text == "a b c"


# ---------------------------------------------------------------------
# RawDocument Model Tests
# ---------------------------------------------------------------------


def test_raw_document_model():
    """Test RawDocument model creation and derived fields."""
    doc = RawDocument(
        document_id="test-doc",
        source_file="test.pdf",
        source_path="/path/to/test.pdf",
        page_count=2,
        pages=[
            PageText(page_number=1, text="First page text"),
            PageText(page_number=2, text="Second page text"),
        ],
    )

    assert doc.document_id == "test-doc"
    assert doc.page_count == 2
    assert doc.total_characters == len("First page text") + len("Second page text")
    assert doc.total_words == 6  # "First" "page" "text" + "Second" "page" "text"
    assert doc.has_text is True


def test_raw_document_model_empty_pages():
    """Test RawDocument with empty pages."""
    doc = RawDocument(
        document_id="empty-doc",
        source_file="empty.pdf",
        source_path="/path/to/empty.pdf",
        page_count=1,
        pages=[PageText(page_number=1, text="")],
    )

    assert doc.has_text is False
    assert doc.total_characters == 0
    assert doc.total_words == 0


def test_raw_document_get_page():
    """Test getting a specific page from RawDocument."""
    doc = RawDocument(
        document_id="test",
        source_file="test.pdf",
        source_path="/path",
        page_count=3,
        pages=[
            PageText(page_number=1, text="Page 1"),
            PageText(page_number=2, text="Page 2"),
            PageText(page_number=3, text="Page 3"),
        ],
    )

    assert doc.get_page(1).text == "Page 1"
    assert doc.get_page(2).text == "Page 2"
    assert doc.get_page(99) is None


def test_raw_document_full_transcript():
    """Test getting full transcript from RawDocument."""
    doc = RawDocument(
        document_id="test",
        source_file="test.pdf",
        source_path="/path",
        page_count=2,
        pages=[
            PageText(page_number=1, text="First"),
            PageText(page_number=2, text="Second"),
        ],
    )

    assert "First" in doc.full_transcript
    assert "Second" in doc.full_transcript


# ---------------------------------------------------------------------
# RawDocumentService Tests
# ---------------------------------------------------------------------


def test_raw_document_service_save_load(
    raw_doc_service: RawDocumentService,
):
    """Test saving and loading a RawDocument."""
    doc = RawDocument(
        document_id="save-test",
        source_file="test.pdf",
        source_path="/path/test.pdf",
        page_count=1,
        pages=[PageText(page_number=1, text="Test content")],
    )

    # Save
    save_path = raw_doc_service.save(doc)
    assert save_path.exists()

    # Load
    loaded = raw_doc_service.load("save-test")
    assert loaded is not None
    assert loaded.document_id == doc.document_id
    assert loaded.source_file == doc.source_file
    assert loaded.pages[0].text == "Test content"


def test_raw_document_service_load_nonexistent(
    raw_doc_service: RawDocumentService,
):
    """Test loading a non-existent document returns None."""
    assert raw_doc_service.load("nonexistent") is None


def test_raw_document_service_exists(
    raw_doc_service: RawDocumentService,
):
    """Test checking document existence."""
    doc = RawDocument(
        document_id="exists-test",
        source_file="test.pdf",
        source_path="/path",
        page_count=1,
        pages=[PageText(page_number=1, text="Content")],
    )

    assert raw_doc_service.exists("exists-test") is False
    raw_doc_service.save(doc)
    assert raw_doc_service.exists("exists-test") is True


def test_raw_document_service_list_documents(
    raw_doc_service: RawDocumentService,
):
    """Test listing available documents."""
    doc1 = RawDocument(
        document_id="doc-a",
        source_file="a.pdf",
        source_path="/a",
        page_count=1,
        pages=[PageText(page_number=1, text="A")],
    )
    doc2 = RawDocument(
        document_id="doc-b",
        source_file="b.pdf",
        source_path="/b",
        page_count=1,
        pages=[PageText(page_number=1, text="B")],
    )

    raw_doc_service.save(doc1)
    raw_doc_service.save(doc2)

    docs = raw_doc_service.list_documents()
    assert len(docs) == 2
    assert "doc-a" in docs
    assert "doc-b" in docs


def test_raw_document_service_delete(
    raw_doc_service: RawDocumentService,
):
    """Test deleting a RawDocument."""
    doc = RawDocument(
        document_id="delete-test",
        source_file="test.pdf",
        source_path="/path",
        page_count=1,
        pages=[PageText(page_number=1, text="Content")],
    )

    raw_doc_service.save(doc)
    assert raw_doc_service.exists("delete-test") is True

    raw_doc_service.delete("delete-test")
    assert raw_doc_service.exists("delete-test") is False


# ---------------------------------------------------------------------
# Phase3APipeline Tests
# ---------------------------------------------------------------------


def test_phase3a_pipeline_discovers_pdfs(
    phase3a_pipeline: Phase3APipeline,
    lesson_dir: Path,
):
    """Test pipeline PDF discovery."""
    from tests._make_pdf import write_synthetic_pdf

    write_synthetic_pdf(lesson_dir / "a.pdf", ["Page A"])
    write_synthetic_pdf(lesson_dir / "b.pdf", ["Page B"])

    results = phase3a_pipeline.discover()

    assert len(results) == 2
    assert results[0].filename == "a.pdf"
    assert results[1].filename == "b.pdf"


def test_phase3a_pipeline_extracts_pdfs(
    phase3a_pipeline: Phase3APipeline,
    lesson_dir: Path,
):
    """Test pipeline PDF extraction."""
    from tests._make_pdf import write_synthetic_pdf

    write_synthetic_pdf(
        lesson_dir / "extract-test.pdf",
        ["First page", "Second page", "Third page"],
    )

    results = phase3a_pipeline.run()

    assert len(results) == 1
    assert results[0].document_id == "extract-test"
    assert results[0].page_count == 3
    assert results[0].raw_document is not None
    assert results[0].error is None


def test_phase3a_pipeline_empty_directory(
    phase3a_pipeline: Phase3APipeline,
):
    """Test pipeline with empty lesson directory."""
    results = phase3a_pipeline.run()
    assert results == []


def test_phase3a_pipeline_handles_corrupted_pdf(
    phase3a_pipeline: Phase3APipeline,
    lesson_dir: Path,
):
    """Test pipeline handles corrupted/invalid PDF."""
    from tests._make_pdf import write_synthetic_pdf

    # Valid PDF
    write_synthetic_pdf(lesson_dir / "valid.pdf", ["Valid content"])

    # Invalid PDF (not a real PDF)
    (lesson_dir / "invalid.pdf").write_bytes(b"this is not a pdf")

    results = phase3a_pipeline.run()

    # Should have 2 results
    assert len(results) == 2

    # Find each result
    valid_result = next(r for r in results if r.source_file == "valid.pdf")
    invalid_result = next(r for r in results if r.source_file == "invalid.pdf")

    assert valid_result.raw_document is not None
    assert valid_result.error is None
    assert invalid_result.raw_document is None
    assert invalid_result.error is not None


def test_phase3a_pipeline_multiple_pdfs(
    phase3a_pipeline: Phase3APipeline,
    lesson_dir: Path,
):
    """Test pipeline with multiple PDFs."""
    from tests._make_pdf import write_synthetic_pdf

    write_synthetic_pdf(lesson_dir / "alpha.pdf", ["Alpha content"])
    write_synthetic_pdf(lesson_dir / "beta.pdf", ["Beta content"])
    write_synthetic_pdf(lesson_dir / "gamma.pdf", ["Gamma content"])

    results = phase3a_pipeline.run()

    assert len(results) == 3
    successful = [r for r in results if r.raw_document is not None]
    assert len(successful) == 3


def test_phase3a_pipeline_get_raw_document(
    phase3a_pipeline: Phase3APipeline,
    lesson_dir: Path,
):
    """Test retrieving a specific raw document."""
    from tests._make_pdf import write_synthetic_pdf

    write_synthetic_pdf(lesson_dir / "retrieve.pdf", ["Retrieve content"])

    phase3a_pipeline.run()

    doc = phase3a_pipeline.get_raw_document("retrieve")
    assert doc is not None
    assert doc.document_id == "retrieve"


def test_phase3a_pipeline_summary(
    phase3a_pipeline: Phase3APipeline,
    lesson_dir: Path,
):
    """Test pipeline summary generation."""
    from tests._make_pdf import write_synthetic_pdf

    write_synthetic_pdf(lesson_dir / "summary.pdf", ["Word " * 100])

    phase3a_pipeline.run()

    summary = phase3a_pipeline.get_summary()
    assert summary["documents_processed"] == 1
    assert summary["pdfs_discovered"] == 1
    assert summary["total_pages"] >= 1


# ---------------------------------------------------------------------
# Source PDF Integrity Tests
# ---------------------------------------------------------------------


def test_source_pdf_untouched_after_extraction(
    lesson_dir: Path,
    tmp_path: Path,
):
    """Test that source PDF is not modified during extraction."""
    from tests._make_pdf import write_synthetic_pdf

    pdf_path = lesson_dir / "intact.pdf"
    write_synthetic_pdf(pdf_path, ["Original content"])

    # Get original file size and content
    original_size = pdf_path.stat().st_size
    original_content = pdf_path.read_bytes()

    # Run extraction
    reader = PDFReader(lesson_dir=lesson_dir)
    reader.extract_raw_document(pdf_path)

    # Verify file unchanged
    assert pdf_path.stat().st_size == original_size
    assert pdf_path.read_bytes() == original_content
