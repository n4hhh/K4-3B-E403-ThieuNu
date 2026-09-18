"""RawDocument — Phase 3A output model.

This model represents the deterministic extraction of a PDF file.
It is NOT a structured Lesson — that belongs to Phase 3A.5.

RawDocument characteristics:
    - Represents PDF text extraction
    - Page-oriented structure
    - Close to original source
    - Deterministic (same PDF always produces same RawDocument)

Contrast with Lesson (Phase 3A.5):
    - Structured learning representation
    - Concept-oriented
    - AI-derived from RawDocument
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class PageText:
    """Text extracted from a single PDF page.

    Used by both PDFReader (internal) and RawDocument (output).
    This is a dataclass for backward compatibility with existing code.
    """

    page_number: int  # 1-based page number
    text: str = ""   # normalized text content
    character_count: int = 0  # character count of extracted text
    word_count: int = 0  # word count of extracted text

    def __post_init__(self):
        """Calculate derived fields after initialization."""
        if self.character_count == 0:
            self.character_count = len(self.text)
        if self.word_count == 0:
            words = self.text.split() if self.text else []
            self.word_count = len(words)


@dataclass
class RawDocument:
    """Raw document extracted from a PDF file.

    This is the output of Phase 3A: PDF → RawDocument.

    The document contains:
        - Metadata about the source file
        - Page-by-page extracted text
        - No AI processing or interpretation

    This model is stored as raw.json in:
        data/lesson/processed/{document_id}/raw.json
    """

    document_id: str           # Unique identifier derived from source filename
    source_file: str          # Original PDF filename
    source_path: str         # Absolute path to source PDF
    page_count: int           # Total number of pages in the PDF
    pages: List[PageText]    # Extracted text from each page

    # Extraction metadata
    created_at: datetime = None  # Timestamp when extraction was performed (default: now)
    extractor_version: str = "1.0.0"  # Version of the PDFReader extractor

    # Computed fields
    total_characters: int = 0
    total_words: int = 0
    has_text: bool = False

    def __post_init__(self):
        """Calculate derived fields after initialization."""
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.total_characters == 0:
            self.total_characters = sum(p.character_count for p in self.pages)
        if self.total_words == 0:
            self.total_words = sum(p.word_count for p in self.pages)
        self.has_text = self.total_characters > 0

    def get_page(self, page_number: int) -> Optional[PageText]:
        """Get a specific page by 1-based page number."""
        for page in self.pages:
            if page.page_number == page_number:
                return page
        return None

    def get_full_text(self) -> str:
        """Get all page text concatenated with page separators."""
        return "\n\n--- Page {n} ---\n\n".join(
            f"Page {p.page_number}\n{p.text}"
            for p in self.pages if p.text
        )

    @property
    def full_transcript(self) -> str:
        """Get clean full text without page markers."""
        return "\n\n".join(p.text for p in self.pages if p.text)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "document_id": self.document_id,
            "source_file": self.source_file,
            "source_path": self.source_path,
            "page_count": self.page_count,
            "pages": [
                {
                    "page_number": p.page_number,
                    "text": p.text,
                    "character_count": p.character_count,
                    "word_count": p.word_count,
                }
                for p in self.pages
            ],
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            "extractor_version": self.extractor_version,
            "total_characters": self.total_characters,
            "total_words": self.total_words,
            "has_text": self.has_text,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RawDocument":
        """Create a RawDocument from a dictionary."""
        # Parse pages
        pages = []
        for p_data in data.get("pages", []):
            pages.append(PageText(
                page_number=p_data.get("page_number", 0),
                text=p_data.get("text", ""),
                character_count=p_data.get("character_count", 0),
                word_count=p_data.get("word_count", 0),
            ))

        # Parse created_at
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        elif created_at is None:
            created_at = datetime.utcnow()

        return cls(
            document_id=data.get("document_id", ""),
            source_file=data.get("source_file", ""),
            source_path=data.get("source_path", ""),
            page_count=data.get("page_count", 0),
            pages=pages,
            created_at=created_at,
            extractor_version=data.get("extractor_version", "1.0.0"),
            total_characters=data.get("total_characters", 0),
            total_words=data.get("total_words", 0),
            has_text=data.get("has_text", False),
        )


class RawDocumentMetadata:
    """Summary metadata for a raw document."""

    def __init__(
        self,
        document_id: str,
        source_file: str,
        page_count: int,
        total_words: int,
        created_at: datetime,
        file_size_bytes: int = 0,
    ) -> None:
        self.document_id = document_id
        self.source_file = source_file
        self.page_count = page_count
        self.total_words = total_words
        self.created_at = created_at
        self.file_size_bytes = file_size_bytes

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "document_id": self.document_id,
            "source_file": self.source_file,
            "page_count": self.page_count,
            "total_words": self.total_words,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            "file_size_bytes": self.file_size_bytes,
        }
