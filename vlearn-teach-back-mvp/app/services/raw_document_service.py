"""RawDocumentService — storage layer for Phase 3A output.

This service handles:
    - Loading RawDocument from cached JSON files
    - Saving RawDocument to processed/ directory
    - Listing available raw documents

Output location:
    data/lesson/processed/{document_id}/raw.json
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import List, Optional

from app.config import PROCESSED_DIR, LESSON_DIR
from app.models.raw_document import RawDocument, RawDocumentMetadata


logger = logging.getLogger(__name__)


class RawDocumentService:
    """Service for storing and retrieving RawDocument objects."""

    def __init__(
        self,
        processed_dir: Optional[Path] = None,
        lesson_dir: Optional[Path] = None,
    ) -> None:
        self._processed_dir = Path(processed_dir) if processed_dir else PROCESSED_DIR
        self._lesson_dir = Path(lesson_dir) if lesson_dir else LESSON_DIR

        # Ensure processed directory exists
        self._processed_dir.mkdir(parents=True, exist_ok=True)

    @property
    def processed_dir(self) -> Path:
        return self._processed_dir

    def _get_raw_document_path(self, document_id: str) -> Path:
        """Get the path to the raw.json file for a document."""
        return self._processed_dir / document_id / "raw.json"

    def save(self, raw_document: RawDocument) -> Path:
        """Save a RawDocument to the processed directory.

        Returns the path where the document was saved.
        """
        output_path = self._get_raw_document_path(raw_document.document_id)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Serialize to JSON
        json_data = raw_document.to_dict()

        with output_path.open("w", encoding="utf-8") as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)

        logger.info(
            "Saved RawDocument '%s' to %s",
            raw_document.document_id,
            output_path,
        )

        return output_path

    def load(self, document_id: str) -> Optional[RawDocument]:
        """Load a RawDocument from the processed directory.

        Returns None if the document doesn't exist.
        """
        input_path = self._get_raw_document_path(document_id)
        if not input_path.exists():
            logger.debug(
                "RawDocument '%s' not found at %s",
                document_id,
                input_path,
            )
            return None

        try:
            with input_path.open("r", encoding="utf-8") as f:
                json_data = json.load(f)
            return RawDocument.from_dict(json_data)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            logger.error(
                "Failed to load RawDocument '%s' from %s: %s",
                document_id,
                input_path,
                exc,
            )
            return None

    def exists(self, document_id: str) -> bool:
        """Check if a RawDocument exists."""
        return self._get_raw_document_path(document_id).exists()

    def list_documents(self) -> List[str]:
        """List all available document IDs in the processed directory."""
        if not self._processed_dir.exists():
            return []

        document_ids = []
        for item in self._processed_dir.iterdir():
            if item.is_dir():
                raw_path = item / "raw.json"
                if raw_path.exists():
                    document_ids.append(item.name)

        return sorted(document_ids)

    def get_metadata(self, document_id: str) -> Optional[RawDocumentMetadata]:
        """Get metadata for a document without loading full content."""
        raw_doc = self.load(document_id)
        if raw_doc is None:
            return None

        # Get file size if available
        raw_path = self._get_raw_document_path(document_id)
        file_size = 0
        if raw_path.exists():
            try:
                file_size = raw_path.stat().st_size
            except OSError:
                pass

        return RawDocumentMetadata(
            document_id=raw_doc.document_id,
            source_file=raw_doc.source_file,
            page_count=raw_doc.page_count,
            total_words=raw_doc.total_words,
            created_at=raw_doc.created_at,
            file_size_bytes=file_size,
        )

    def delete(self, document_id: str) -> bool:
        """Delete a RawDocument from the processed directory.

        Returns True if deleted, False if it didn't exist.
        """
        doc_dir = self._get_raw_document_path(document_id).parent
        if not doc_dir.exists():
            return False

        try:
            # Delete the raw.json file
            raw_path = doc_dir / "raw.json"
            if raw_path.exists():
                raw_path.unlink()

            # Remove the directory if empty
            if not any(doc_dir.iterdir()):
                doc_dir.rmdir()

            logger.info("Deleted RawDocument '%s'", document_id)
            return True
        except OSError as exc:
            logger.error("Failed to delete RawDocument '%s': %s", document_id, exc)
            return False
