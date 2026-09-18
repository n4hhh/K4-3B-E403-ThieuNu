"""Publication repository — persists StructuredLesson to disk.

Output shape (per Phase 3A.5 decisions):

    data/lesson/processed/{document_id}/
        raw.json                (PHASE 3A, NEVER modified)
        published.json          (NEW — written only on PASS / WARN)

This service:

    * Computes the SHA-256 of the source PDF and freezes it into the
      metadata (``source_sha256``).
    * Never overwrites ``raw.json``.
    * Returns the on-disk path of the written file.
    * Can load a previously-published lesson for the adapter to use.

Phase 3A invariants: this service reads ``RawDocument`` (via
``raw.json``) to compute the source SHA, but never writes it.
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Optional

from app.config import LESSON_DIR, PROCESSED_DIR
from app.models.raw_document import RawDocument
from app.models.structured_lesson import (
    StructuredLesson,
    lesson_from_dict,
    lesson_to_dict,
)
from app.models.validation_report import ValidationReport


logger = logging.getLogger(__name__)


class PublishedLessonRepository:
    """Read/write the ``published.json`` artifact.

    Args:
        processed_dir: Directory containing ``{doc_id}/raw.json``
            (defaults to ``app.config.PROCESSED_DIR``).
        lesson_dir: Directory containing the source PDFs
            (defaults to ``app.config.LESSON_DIR``). Used to compute
            the source SHA-256.
    """

    filename = "published.json"

    def __init__(
        self,
        processed_dir: Optional[Path] = None,
        lesson_dir: Optional[Path] = None,
    ) -> None:
        self._processed_dir = (
            Path(processed_dir) if processed_dir else PROCESSED_DIR
        )
        self._lesson_dir = Path(lesson_dir) if lesson_dir else LESSON_DIR

    # ------------------------------------------------------------------
    # Paths
    # ------------------------------------------------------------------

    def _published_path(self, document_id: str) -> Path:
        return self._processed_dir / document_id / self.filename

    def _raw_path(self, document_id: str) -> Path:
        return self._processed_dir / document_id / "raw.json"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def exists(self, document_id: str) -> bool:
        return self._published_path(document_id).exists()

    def load(self, document_id: str) -> Optional[StructuredLesson]:
        path = self._published_path(document_id)
        if not path.exists():
            return None
        try:
            with path.open("r", encoding="utf-8") as fh:
                payload = json.load(fh)
        except (OSError, json.JSONDecodeError) as exc:
            logger.error(
                "Failed to load published lesson %s: %s", document_id, exc
            )
            return None

        # The file uses the envelope shape ({"schema_version": ..., "lesson": {...}}).
        # Strip the envelope before re-hydrating.
        if isinstance(payload, dict) and "lesson" in payload:
            payload = payload["lesson"]

        try:
            return lesson_from_dict(payload)
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to parse published lesson %s: %s", document_id, exc)
            return None

    def save(
        self,
        document_id: str,
        lesson: StructuredLesson,
        validation: ValidationReport,
    ) -> Path:
        """Persist the lesson + validation report sidecar.

        Writes:
            * ``{doc_id}/published.json`` — the StructuredLesson.
            * ``{doc_id}/validation.json`` — the ValidationReport.

        Returns the published.json path.
        """
        if validation.status.value not in {"PASS", "WARN"}:
            raise ValueError(
                f"Refusing to publish a lesson with status "
                f"{validation.status.value!r} — only PASS / WARN are allowed."
            )

        out_path = self._published_path(document_id)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        # Build the top-level envelope required by the spec.
        payload = lesson_to_dict(lesson)
        envelope = {
            "schema_version": payload.get(
                "schema_version", "3a5.lesson.v1"
            ),
            "documentizer_version": payload.get(
                "documentizer_version", lesson.metadata.documentizer_version
            ),
            "source_sha256": lesson.metadata.source_sha256,
            "created_at": lesson.metadata.generated_at.isoformat()
            if hasattr(lesson.metadata.generated_at, "isoformat")
            else str(lesson.metadata.generated_at),
            "validation_status": validation.status.value,
            "lesson": payload,
        }

        with out_path.open("w", encoding="utf-8") as fh:
            json.dump(envelope, fh, indent=2, ensure_ascii=False)

        # Sidecar
        sidecar = out_path.parent / "validation.json"
        with sidecar.open("w", encoding="utf-8") as fh:
            json.dump(
                validation.model_dump(mode="json"),
                fh,
                indent=2,
                ensure_ascii=False,
            )

        logger.info("Published lesson %s → %s", document_id, out_path)
        return out_path

    # ------------------------------------------------------------------
    # Source SHA
    # ------------------------------------------------------------------

    def compute_source_sha256(self, raw_document: RawDocument) -> str:
        """Compute the SHA-256 of the source PDF by hashing its bytes.

        Falls back to a content hash of the RawDocument if the file is
        unreachable — but logs a warning, because that defeats the
        purpose of source-attestation.
        """
        # The RawDocument stores only the source filename (relative
        # path). We resolve it against LESSON_DIR.
        candidate = self._lesson_dir / raw_document.source_file
        if candidate.exists() and candidate.is_file():
            h = hashlib.sha256()
            with candidate.open("rb") as fh:
                for chunk in iter(lambda: fh.read(65536), b""):
                    h.update(chunk)
            return h.hexdigest()
        logger.warning(
            "Source PDF not found at %s; falling back to RawDocument content hash",
            candidate,
        )
        # Fallback: hash the JSON representation so the field is still
        # stable. This is intentionally weak; tests assert the file
        # path is used when available.
        body = json.dumps(raw_document.to_dict(), sort_keys=True).encode()
        return hashlib.sha256(body).hexdigest()


__all__ = ["PublishedLessonRepository"]