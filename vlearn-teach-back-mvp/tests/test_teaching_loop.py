"""Tests for the teaching loop (mock agent + mock validator)."""

from fastapi.testclient import TestClient

from app.main import app


def test_student_message_returns_validation(client):
    created = client.post(
        "/api/teaching-sessions", json={"lesson_id": "rest-api-http-methods"}
    ).json()
    session_id = created["id"]

    explanation = (
        "REST is an architectural style that uses URLs to identify resources. "
        "Clients send HTTP requests to a server."
    )
    response = client.post(
        f"/api/teaching-sessions/{session_id}/messages",
        json={"content": explanation},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert "validation" in body
    assert "agent_message" in body
    assert body["validation"]["chunk_id"] == "rest-api"


def test_student_message_records_two_messages(client):
    created = client.post(
        "/api/teaching-sessions", json={"lesson_id": "rest-api-http-methods"}
    ).json()
    session_id = created["id"]

    client.post(
        f"/api/teaching-sessions/{session_id}/messages",
        json={"content": "REST uses URLs and HTTP."},
    )
    fetched = client.get(f"/api/teaching-sessions/{session_id}").json()
    # Opening agent message + student message + agent reply
    assert len(fetched["messages"]) == 3


def test_advance_chunk_moves_forward(client):
    created = client.post(
        "/api/teaching-sessions", json={"lesson_id": "rest-api-http-methods"}
    ).json()
    session_id = created["id"]

    client.post(
        f"/api/teaching-sessions/{session_id}/messages",
        json={
            "content": (
                "REST is an architectural style. Resources are identified by URLs. "
                "Communication uses HTTP. Representations are exchanged."
            )
        },
    )
    response = client.post(f"/api/teaching-sessions/{session_id}/next")
    assert response.status_code == 200
    body = response.json()
    # After advancing past chunk 0, the new current chunk is "client-server"
    assert body["chunk_states"]["rest-api"] == "completed"
    assert body["chunk_states"]["client-server"] == "current"
