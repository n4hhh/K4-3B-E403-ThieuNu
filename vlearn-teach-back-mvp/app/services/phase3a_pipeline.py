"""Phase 3A Pipeline — orchestrates PDF → RawDocument extraction.

This pipeline:
    1. Discovers PDFs in the lesson directory
    2. Extracts text from each PDF
    3. Creates RawDocument objects
    4. Saves them to the processed directory

Phase 3A outputs:
    data/lesson/processed/{document_id}/raw.json

This is Phase 3A ONLY. No AI processing, no Gemini calls.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
from pathlib import Path
from typing import Dict, List, Optional

from app.config import LESSON_DIR, PROCESSED_DIR
from app.models.raw_document import RawDocument, RawDocumentMetadata
from app.services.pdf_reader import PDFReader
from app.services.raw_document_service import RawDocumentService


logger = logging.getLogger(__name__)


@dataclass
class PDFDiscoveryResult:
    """Result of discovering a single PDF."""
    filename: str
    path: Path
    size_bytes: int
    page_count: Optional[int] = None


@dataclass
class ExtractionResult:
    """Result of extracting a single PDF."""
    document_id: str
    source_file: str
    page_count: int
    total_words: int
    raw_document: Optional[RawDocument] = None
    error: Optional[str] = None


class Phase3APipeline:
    """Orchestrates the Phase 3A PDF → RawDocument pipeline.

    Usage:
        pipeline = Phase3APipeline()
        results = pipeline.run()
    """

    def __init__(
        self,
        lesson_dir: Optional[Path] = None,
        processed_dir: Optional[Path] = None,
        pdf_reader: Optional[PDFReader] = None,
        raw_doc_service: Optional[RawDocumentService] = None,
    ) -> None:
        self._lesson_dir = Path(lesson_dir) if lesson_dir else LESSON_DIR
        self._processed_dir = Path(processed_dir) if processed_dir else PROCESSED_DIR
        self._pdf_reader = pdf_reader or PDFReader(lesson_dir=self._lesson_dir)
        self._raw_doc_service = raw_doc_service or RawDocumentService(
            processed_dir=self._processed_dir,
            lesson_dir=self._lesson_dir,
        )

        self._discovery_results: List[PDFDiscoveryResult] = []
        self._extraction_results: List[ExtractionResult] = []
        self._ran = False

    @property
    def lesson_dir(self) -> Path:
        return self._lesson_dir

    @property
    def processed_dir(self) -> Path:
        return self._processed_dir

    def discover(self) -> List[PDFDiscoveryResult]:
        """Discover all PDFs in the lesson directory.

        Returns:
            List of discovered PDFs with metadata.
        """
        pdfs = self._pdf_reader.discover_pdfs()
        results = []

        for pdf_path in pdfs:
            try:
                size = pdf_path.stat().st_size
            except OSError:
                size = 0

            results.append(PDFDiscoveryResult(
                filename=pdf_path.name,
                path=pdf_path,
                size_bytes=size,
            ))

        self._discovery_results = results
        return results

    def extract_all(self) -> List[ExtractionResult]:
        """Extract all discovered PDFs to RawDocuments.

        Returns:
            List of extraction results, one per discovered PDF.
        """
        if not self._discovery_results:
            self.discover()

        results = []

        for discovery in self._discovery_results:
            result = self._extract_single(discovery)
            results.append(result)
            self._extraction_results.append(result)

        return results

    def _extract_single(self, discovery: PDFDiscoveryResult) -> ExtractionResult:
        """Extract a single PDF to RawDocument.

        Returns:
            ExtractionResult with the extracted document or error.
        """
        try:
            raw_doc = self._pdf_reader.extract_raw_document(discovery.path)

            # Save to processed directory
            save_path = self._raw_doc_service.save(raw_doc)
            logger.info("Saved to: %s", save_path)

            return ExtractionResult(
                document_id=raw_doc.document_id,
                source_file=raw_doc.source_file,
                page_count=raw_doc.page_count,
                total_words=raw_doc.total_words,
                raw_document=raw_doc,
            )

        except FileNotFoundError as exc:
            logger.error("PDF not found: %s", discovery.path)
            return ExtractionResult(
                document_id=self._pdf_reader._slugify(discovery.path.stem),
                source_file=discovery.filename,
                page_count=0,
                total_words=0,
                error=f"File not found: {exc}",
            )

        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to extract %s: %s", discovery.filename, exc)
            return ExtractionResult(
                document_id=self._pdf_reader._slugify(discovery.path.stem),
                source_file=discovery.filename,
                page_count=0,
                total_words=0,
                error=str(exc),
            )

    def run(self) -> List[ExtractionResult]:
        """Run the full Phase 3A pipeline.

        Discovers PDFs, extracts them, and saves RawDocuments.

        Returns:
            List of extraction results.
        """
        self._ran = True

        logger.info("=" * 60)
        logger.info("PHASE 3A PIPELINE STARTING")
        logger.info("=" * 60)
        logger.info("Lesson directory: %s", self._lesson_dir)
        logger.info("Processed directory: %s", self._processed_dir)

        # Discover
        discovery_results = self.discover()
        logger.info("PDFs discovered: %d", len(discovery_results))

        if not discovery_results:
            logger.warning(
                "No PDF files found in %s. "
                "Place PDF files in this directory to process them.",
                self._lesson_dir,
            )
            return []

        # Extract all
        extraction_results = self.extract_all()

        # Summary
        successful = sum(1 for r in extraction_results if r.raw_document is not None)
        failed = sum(1 for r in extraction_results if r.error is not None)

        logger.info("=" * 60)
        logger.info("PHASE 3A PIPELINE COMPLETE")
        logger.info("Successful: %d", successful)
        logger.info("Failed: %d", failed)
        logger.info("=" * 60)

        return extraction_results

    def get_raw_document(self, document_id: str) -> Optional[RawDocument]:
        """Get a specific raw document by ID.

        Args:
            document_id: The document ID.

        Returns:
            RawDocument if found, None otherwise.
        """
        return self._raw_doc_service.load(document_id)

    def list_raw_documents(self) -> List[str]:
        """List all available raw document IDs.

        Returns:
            List of document IDs.
        """
        return self._raw_doc_service.list_documents()

    def get_summary(self) -> Dict[str, object]:
        """Get a summary of the pipeline state.

        Returns:
            Dictionary with pipeline summary.
        """
        documents = self._raw_doc_service.list_documents()
        total_words = 0
        total_pages = 0

        for doc_id in documents:
            doc = self._raw_doc_service.load(doc_id)
            if doc:
                total_words += doc.total_words
                total_pages += doc.page_count

        return {
            "lesson_dir": str(self._lesson_dir),
            "processed_dir": str(self._processed_dir),
            "pdfs_discovered": len(self._discovery_results),
            "documents_processed": len(documents),
            "total_pages": total_pages,
            "total_words": total_words,
            "ran": self._ran,
        }
