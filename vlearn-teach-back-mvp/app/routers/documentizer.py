"""Phase 3A.5 — Documentizer FastAPI routes.

Endpoints (all under ``/api`` to follow the existing router
conventions):

    POST /api/documentizer/{document_id}
        Run the full pipeline (optionally with a custom provider
        override for ad-hoc calls). Publishes ``published.json`` when
        validation passes.

    GET /api/documentizer/{document_id}/status
        Lightweight introspection — does the document have a saved
        RawDocument? Does a published.json exist? What is the latest
        validation status?

The actual provider used by the live app is selected at startup from
the ``AI_PROVIDER`` env var. This router exposes a ``provider`` query
parameter that lets tests force ``mock`` without touching the env.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app.config import LESSON_DIR, PROCESSED_DIR
from app.repositories.published_lesson_repository import (
    PublishedLessonRepository,
)
from app.services.ai import build_provider
from app.services.documentizer_pipeline import (
    DocumentizerFailedError,
    DocumentizerPipeline,
    DocumentizerPipelineConfig,
)


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/documentizer", tags=["documentizer"])


# ---------------------------------------------------------------------------
# Request / response payloads
# ---------------------------------------------------------------------------


class DocumentizerRunResponse(BaseModel):
    document_id: str
    status: str
    validation_status: str
    grounding_score: float
    attempts: int
    chunk_count: int
    concept_count: int
    published_path: Optional[str] = None
    validation_path: Optional[str] = None


class DocumentizerStatusResponse(BaseModel):
    document_id: str
    raw_document_exists: bool
    published_exists: bool
    validation_status: Optional[str] = None
    schema_version: Optional[str] = None
    documentizer_version: Optional[str] = None
    source_sha256: Optional[str] = None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post(
    "/{document_id}",
    response_model=DocumentizerRunResponse,
    name="api_documentizer_run",
)
def run_documentizer(
    request: Request,
    document_id: str,
    provider: str = Query(
        default=None,
        description=(
            "Optional provider override. Defaults to AI_PROVIDER env var. "
            "Use 'mock' for tests."
        ),
    ),
    publish: bool = Query(default=True, description="Write published.json on PASS/WARN"),
):
    """Run Phase 3A.5 end-to-end for a saved RawDocument.

    The provider used at runtime is selected by:

        1. ``provider`` query parameter (if set),
        2. ``AI_PROVIDER`` env var (default ``gemini``).
    """
    try:
        prov = build_provider(provider)
    except Exception as exc:  # noqa: BLE001
        # Provider construction failed (e.g. missing key) — surface as 503.
        raise HTTPException(
            status_code=503,
            detail=f"Provider unavailable: {exc}",
        ) from exc

    config = DocumentizerPipelineConfig()
    pipeline = DocumentizerPipeline(
        provider=prov,
        config=config,
    )

    try:
        result = pipeline.process(document_id, publish=publish)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DocumentizerFailedError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "message": str(exc),
                "attempts": exc.attempts,
                "report": exc.report.model_dump(mode="json") if exc.report else None,
            },
        ) from exc

    published_path = (
        str(result.published_path) if result.published_path is not None else None
    )
    validation_path = (
        str(result.published_path.parent / "validation.json")
        if result.published_path is not None
        else None
    )

    return DocumentizerRunResponse(
        document_id=document_id,
        status="ok",
        validation_status=result.validation.status.value,
        grounding_score=result.validation.grounding_score,
        attempts=result.attempts,
        chunk_count=len(result.lesson.chunks),
        concept_count=len(result.lesson.concepts),
        published_path=published_path,
        validation_path=validation_path,
    )


@router.get(
    "/{document_id}/status",
    response_model=DocumentizerStatusResponse,
    name="api_documentizer_status",
)
def documentizer_status(
    request: Request,
    document_id: str,
):
    """Lightweight status check — does this document have a published.json?"""
    published_repo = PublishedLessonRepository(
        processed_dir=PROCESSED_DIR, lesson_dir=LESSON_DIR
    )
    raw_path = PROCESSED_DIR / document_id / "raw.json"
    raw_exists = raw_path.exists()
    published_exists = published_repo.exists(document_id)

    schema_version = None
    documentizer_version = None
    validation_status = None
    source_sha256 = None

    if published_exists:
        lesson = published_repo.load(document_id)
        if lesson is not None:
            schema_version = lesson.metadata.schema_version
            documentizer_version = lesson.metadata.documentizer_version
            source_sha256 = lesson.metadata.source_sha256
        sidecar = published_repo._published_path(document_id).parent / "validation.json"
        if sidecar.exists():
            try:
                import json

                with sidecar.open("r", encoding="utf-8") as fh:
                    payload = json.load(fh)
                validation_status = payload.get("status")
            except (OSError, json.JSONDecodeError):
                validation_status = None

    return DocumentizerStatusResponse(
        document_id=document_id,
        raw_document_exists=raw_exists,
        published_exists=published_exists,
        validation_status=validation_status,
        schema_version=schema_version,
        documentizer_version=documentizer_version,
        source_sha256=source_sha256,
    )


__all__ = ["router"]