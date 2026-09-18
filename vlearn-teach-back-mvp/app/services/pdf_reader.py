"""PDFReader — low-level wrapper around ``pypdf``.

Responsibilities:
    * discover PDF files in a directory
    * open a PDF file in read-only mode
    * extract text page by page
    * preserve page numbers
    * normalize obvious extraction noise
    * return deterministic raw document data

This is Phase 3A only — no AI processing, no Gemini calls.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import List, Optional

import pypdf

from app.config import LESSON_DIR
from app.models.raw_document import PageText, RawDocument


logger = logging.getLogger(__name__)


class PDFReader:
    """Reads PDF files and returns structured page data.

    The reader does not mutate the file; pypdf is used in strict read-only
    mode. Any IO or parsing error is re-raised so the caller can decide
    whether to skip the file or surface the problem.
    """

    def __init__(self, lesson_dir: Optional[Path] = None) -> None:
        """Initialize PDFReader with optional lesson directory.

        Args:
            lesson_dir: Directory to search for PDFs. Defaults to LESSON_DIR from config.
        """
        self._lesson_dir = Path(lesson_dir) if lesson_dir else LESSON_DIR

    @property
    def lesson_dir(self) -> Path:
        """Return the configured lesson directory."""
        return self._lesson_dir

    def discover_pdfs(self) -> List[Path]:
        """Discover all PDF files in the configured lesson directory.

        Returns:
            Sorted list of Path objects for discovered PDFs.
        """
        if not self._lesson_dir.exists() or not self._lesson_dir.is_dir():
            logger.warning(
                "PDF directory does not exist or is not a directory: %s",
                self._lesson_dir,
            )
            return []

        pdfs = sorted(self._lesson_dir.glob("*.pdf"))
        logger.info(
            "PDF directory: %s\nPDF files discovered: %d",
            self._lesson_dir,
            len(pdfs),
        )

        return pdfs

    def read_pages(self, pdf_path: Path) -> List[PageText]:
        """Return one ``PageText`` per page in the PDF (1-based numbering).

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            List of PageText objects with page number and normalized text.

        Raises:
            FileNotFoundError: If the PDF file doesn't exist.
            pypdf.errors.PdfReadError: If the PDF cannot be read.
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        pages: List[PageText] = []
        try:
            reader = pypdf.PdfReader(str(pdf_path), strict=False)
        except Exception as exc:  # noqa: BLE001 — pypdf raises many types
            logger.error("Failed to open PDF %s: %s", pdf_path, exc)
            raise

        for idx, page in enumerate(reader.pages, start=1):
            try:
                raw = page.extract_text() or ""
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Failed to extract text from page %s of %s: %s",
                    idx, pdf_path.name, exc,
                )
                raw = ""
            pages.append(PageText(
                page_number=idx,
                text=self._normalize(raw),
            ))

        logger.info(
            "Extracted %d pages from %s",
            len(pages),
            pdf_path.name,
        )

        return pages

    def get_page_count(self, pdf_path: Path) -> int:
        """Return the page count without extracting text."""
        pdf_path = Path(pdf_path)
        reader = pypdf.PdfReader(str(pdf_path), strict=False)
        return len(reader.pages)

    def extract_raw_document(self, pdf_path: Path) -> RawDocument:
        """Extract a complete RawDocument from a PDF file.

        This is the main Phase 3A extraction method.

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            RawDocument containing all extracted pages.

        Raises:
            FileNotFoundError: If the PDF file doesn't exist.
        """
        pdf_path = Path(pdf_path)
        document_id = self._slugify(pdf_path.stem)

        pages = self.read_pages(pdf_path)

        raw_document = RawDocument(
            document_id=document_id,
            source_file=pdf_path.name,
            source_path=pdf_path.name,  # relative path only — no absolute filesystem paths in artifacts
            page_count=len(pages),
            pages=pages,
        )

        logger.info(
            "Raw document generated: %s\nPage count: %d\nTotal words: %d",
            document_id,
            raw_document.page_count,
            raw_document.total_words,
        )

        return raw_document

    @staticmethod
    def _normalize(text: str) -> str:
        """Normalize PDF text.

        Steps:
            * collapse carriage returns and form feeds
            * fix hyphenated line breaks (``exam-\\nple`` -> ``example``)
            * collapse runs of whitespace inside a line
            * drop empty lines
        """
        if not text:
            return ""

        text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\f", "\n")

        # Fix hyphenated breaks: word-\nword  →  wordword
        # Only when the hyphen is followed by a single newline and a lowercase
        # letter (avoid removing intentional hyphens at line ends).
        text = re.sub(r"-\n([a-zà-ỹ])", r"\1", text)

        # Collapse multiple spaces / tabs on a line
        lines = []
        for line in text.split("\n"):
            cleaned = re.sub(r"[ \t]+", " ", line).strip()
            if cleaned:
                lines.append(cleaned)
        return "\n".join(lines)

    @staticmethod
    def _slugify(text: str) -> str:
        """Build a stable kebab-case id from a string."""
        text = text.lower().strip()
        text = re.sub(r"[^a-z0-9à-ỹ\s-]", "", text)
        text = re.sub(r"\s+", "-", text)
        return text.strip("-") or "document"
