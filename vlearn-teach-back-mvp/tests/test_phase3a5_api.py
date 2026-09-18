"""FastAPI integration tests for the Phase 3A.5 documentizer router.

Covers:

    * GET /api/documentizer/{document_id}/status
    * POST /api/documentizer/{document_id} with provider=mock
    * The router uses the current PROCESSED_DIR / LESSON_DIR — not
      paths captured at app startup.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def app_environment(monkeypatch, tmp_path: Path):
    """Spin up a complete app environment with a tmp lesson + processed dir."""
    from app import config as config_module
    from app.services import raw_document_service
    from app.services import pdf_reader
    from app.services import phase3a_pipeline
    from app.repositories import published_lesson_repository as pub_mod
    from app.routers import documentizer as doc_router_module
    from app.services.phase3a_pipeline import Phase3APipeline
    from tests._make_pdf import write_synthetic_pdf

    lesson_dir = tmp_path / "lesson"
    processed_dir = tmp_path / "processed"
    lesson_dir.mkdir()

    # Patch the module-level constants BEFORE importing the app.
    monkeypatch.setattr(config_module, "LESSON_DIR", lesson_dir)
    monkeypatch.setattr(config_module, "PROCESSED_DIR", processed_dir)
    monkeypatch.setattr(raw_document_service, "PROCESSED_DIR", processed_dir)
    monkeypatch.setattr(raw_document_service, "LESSON_DIR", lesson_dir)
    monkeypatch.setattr(pub_mod, "PROCESSED_DIR", processed_dir)
    monkeypatch.setattr(pub_mod, "LESSON_DIR", lesson_dir)
    monkeypatch.setattr(pdf_reader, "LESSON_DIR", lesson_dir)
    monkeypatch.setattr(phase3a_pipeline, "LESSON_DIR", lesson_dir)
    monkeypatch.setattr(phase3a_pipeline, "PROCESSED_DIR", processed_dir)
    monkeypatch.setattr(doc_router_module, "PROCESSED_DIR", processed_dir)
    monkeypatch.setattr(doc_router_module, "LESSON_DIR", lesson_dir)
    # Rebuild the settings singleton to reflect new values.
    monkeypatch.setattr(
        config_module.settings, "lesson_dir", lesson_dir, raising=False
    )
    monkeypatch.setattr(
        config_module.settings, "processed_dir", processed_dir, raising=False
    )

    write_synthetic_pdf(
        lesson_dir / "demo.pdf",
        [
            ["Intro", "Topic A", "Topic B"],
            ["Body", "Topic C", "Topic D"],
        ],
    )
    Phase3APipeline().run()

    from app.main import app
    # Re-wire the app's LessonRepository + PublishedLessonRepository to
    # point at the tmp dirs. The app instance was constructed at import
    # time against the global LESSON_DIR/PROCESSED_DIR.
    from app.repositories.lesson_repository import LessonRepository
    from app.repositories.published_lesson_repository import (
        PublishedLessonRepository,
    )
    from app.services.pdf_lesson_service import PDFLessonService

    app.state.pdf_lesson_service = PDFLessonService(lesson_dir=lesson_dir)
    app.state.pdf_lesson_service.reload()
    app.state.lesson_repository = LessonRepository(
        pdf_service=app.state.pdf_lesson_service,
        json_fallback=config_module.JSON_FALLBACK_FILE,
        published_repo=PublishedLessonRepository(
            processed_dir=processed_dir, lesson_dir=lesson_dir
        ),
    )

    yield TestClient(app), tmp_path, lesson_dir, processed_dir


def test_status_endpoint_returns_no_published_yet(app_environment):
    client, tmp, lesson_dir, processed_dir = app_environment
    r = client.get("/api/documentizer/demo/status")
    assert r.status_code == 200
    body = r.json()
    assert body["document_id"] == "demo"
    assert body["raw_document_exists"] is True
    assert body["published_exists"] is False


def test_run_endpoint_publishes_with_mock(app_environment):
    client, tmp, lesson_dir, processed_dir = app_environment
    r = client.post(
        "/api/documentizer/demo",
        params={"provider": "mock", "publish": True},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["validation_status"] in {"PASS", "WARN"}
    assert body["chunk_count"] >= 1
    assert body["concept_count"] >= 1
    assert body["published_path"]

    # Now status should reflect the published lesson.
    r2 = client.get("/api/documentizer/demo/status")
    assert r2.status_code == 200
    body2 = r2.json()
    assert body2["published_exists"] is True
    assert body2["validation_status"] in {"PASS", "WARN"}


def test_run_endpoint_returns_404_on_missing_document(app_environment):
    client, *_ = app_environment
    r = client.post(
        "/api/documentizer/nonexistent",
        params={"provider": "mock"},
    )
    # A missing RawDocument is a 404 (resource not found), not 422.
    assert r.status_code == 404


def test_run_endpoint_with_publish_false(app_environment):
    client, tmp, lesson_dir, processed_dir = app_environment
    r = client.post(
        "/api/documentizer/demo",
        params={"provider": "mock", "publish": False},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["published_path"] is None
    # No published.json should exist.
    assert not (processed_dir / "demo" / "published.json").exists()