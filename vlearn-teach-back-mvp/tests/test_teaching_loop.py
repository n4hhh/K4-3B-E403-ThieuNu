"""Tests for the teaching loop.

These run against the hermetic ``client`` fixture: the demo lesson plus
the validator's deterministic heuristic path, so no model is called and
the assertions are stable.
"""


def _start(client, lesson_id):
    created = client.post(
        "/api/teaching-sessions", json={"lesson_id": lesson_id}
    ).json()
    return created["id"]


def test_student_message_returns_validation(client, demo_lesson_id):
    session_id = _start(client, demo_lesson_id)

    response = client.post(
        f"/api/teaching-sessions/{session_id}/messages",
        json={
            "content": (
                "REST là một kiểu kiến trúc cho web API, mỗi tài nguyên có "
                "một địa chỉ riêng."
            )
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert "validation" in body
    assert "agent_message" in body
    assert body["validation"]["chunk_id"] == "rest-api"


def test_student_message_records_two_messages(client, demo_lesson_id):
    session_id = _start(client, demo_lesson_id)

    client.post(
        f"/api/teaching-sessions/{session_id}/messages",
        json={"content": "REST dùng URL để chỉ tới tài nguyên trên server."},
    )
    fetched = client.get(f"/api/teaching-sessions/{session_id}").json()
    # Opening agent message + student message + agent reply
    assert len(fetched["messages"]) == 3


def test_thin_explanation_never_passes(client, demo_lesson_id):
    """A one-liner must not satisfy the agent (hard test: "hiểu quá dễ")."""
    session_id = _start(client, demo_lesson_id)

    body = client.post(
        f"/api/teaching-sessions/{session_id}/messages",
        json={"content": "Cái này là về REST thôi."},
    ).json()

    assert body["validation"]["passed"] is False
    assert body["validation"]["ask_back"]


def test_pasted_source_is_rejected(client, demo_lesson_id):
    """Pasting the lesson text back is not teaching (hard test)."""
    session_id = _start(client, demo_lesson_id)
    chunk = client.get(f"/api/lessons/{demo_lesson_id}").json()["chunks"][0]

    body = client.post(
        f"/api/teaching-sessions/{session_id}/messages",
        json={"content": chunk["content"]},
    ).json()

    assert body["validation"]["passed"] is False
    assert body["validation"]["is_copied"] is True
    assert body["validation"]["gap_type"] == "copied"


def test_advance_chunk_moves_forward(client, demo_lesson_id):
    session_id = _start(client, demo_lesson_id)

    client.post(
        f"/api/teaching-sessions/{session_id}/messages",
        json={
            "content": (
                "REST là một kiểu kiến trúc chứ không phải giao thức. "
                "Mỗi tài nguyên được định danh bằng một URL riêng. "
                "Client và server tách rời nhau nên hai bên phát triển độc lập."
            )
        },
    )
    response = client.post(f"/api/teaching-sessions/{session_id}/next")
    assert response.status_code == 200
    body = response.json()
    assert body["chunk_states"]["rest-api"] == "completed"
    assert body["chunk_states"]["client-server"] == "current"


def test_attempt_limit_lets_the_student_move_on(client, demo_lesson_id):
    """The loop must not trap a student — practice, not an exam."""
    session_id = _start(client, demo_lesson_id)

    last = {}
    for _ in range(4):
        last = client.post(
            f"/api/teaching-sessions/{session_id}/messages",
            json={"content": "Mình nghĩ nó liên quan tới mạng máy tính gì đó."},
        ).json()

    assert last["validation"]["passed"] is True
    assert last["validation"]["needs_review"] is True
    assert last["session"]["needs_review_chunks"] == ["rest-api"]


def test_result_reports_learning_behaviour(client, demo_lesson_id):
    session_id = _start(client, demo_lesson_id)
    client.post(
        f"/api/teaching-sessions/{session_id}/messages",
        json={"content": "Mình chưa rõ lắm nhưng hình như nó là kiểu gì đó."},
    )

    result = client.get(f"/api/teaching-sessions/{session_id}/result").json()
    assert result["total_chunks"] == 5
    assert result["teaching_loops"] == 1
    assert result["clarifications"] == 1
    assert result["clarified_areas"]
