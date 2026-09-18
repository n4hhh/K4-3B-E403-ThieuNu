"""Tests for teaching-session lifecycle and persistence."""

import pytest

from app.repositories.session_repository import SessionRepository
from app.services.lesson_service import LessonService
from app.services.teaching_service import TeachingService


def test_create_session_via_api(client):
    response = client.post(
        "/api/teaching-sessions", json={"lesson_id": "rest-api-http-methods"}
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["lesson_id"] == "rest-api-http-methods"
    assert body["status"] == "in_progress"
    assert len(body["chunk_order"]) == 5


def test_get_session_returns_state(client):
    created = client.post(
        "/api/teaching-sessions", json={"lesson_id": "rest-api-http-methods"}
    ).json()
    session_id = created["id"]

    response = client.get(f"/api/teaching-sessions/{session_id}")
    assert response.status_code == 200
    assert response.json()["id"] == session_id


def test_get_session_404_when_missing(client):
    response = client.get("/api/teaching-sessions/does-not-exist")
    assert response.status_code == 404


def test_create_session_for_missing_lesson_returns_404(client):
    response = client.post(
        "/api/teaching-sessions", json={"lesson_id": "nope"}
    )
    assert response.status_code == 404


def test_session_repository_roundtrip():
    repo = SessionRepository()
    service = TeachingService(lesson_service=LessonService(), session_repo=repo)
    session = service.create_session("rest-api-http-methods")
    assert session is not None
    fetched = repo.get(session.id)
    assert fetched is not None
    assert fetched.id == session.id
