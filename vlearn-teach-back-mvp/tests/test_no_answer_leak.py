"""The student's browser must never receive the answer.

The agent's wording is carefully built to ask without telling. That
effort is wasted if the JSON behind the page carries the missing key
points anyway — they would be one devtools panel away.
"""

from __future__ import annotations


def test_message_response_omits_the_expected_answers(client, demo_lesson_id):
    session_id = client.post(
        "/api/teaching-sessions", json={"lesson_id": demo_lesson_id}
    ).json()["id"]

    body = client.post(
        f"/api/teaching-sessions/{session_id}/messages",
        json={"content": "REST thì mình nghĩ nó liên quan tới web gì đó thôi."},
    ).json()

    validation = body["validation"]
    assert validation["passed"] is False
    for leaked_field in ("missing_points", "covered_points", "note_for_instructor"):
        assert leaked_field not in validation

    # …and no key point text sneaks through the rest of the payload.
    chunk = client.get(f"/api/lessons/{demo_lesson_id}").json()["chunks"][0]
    serialized = str(body)
    for key_point in chunk["key_points"]:
        assert key_point not in serialized


def test_instructor_log_does_keep_the_detail(client, demo_lesson_id):
    """What the student must not see, the instructor still needs."""
    session_id = client.post(
        "/api/teaching-sessions", json={"lesson_id": demo_lesson_id}
    ).json()["id"]
    client.post(
        f"/api/teaching-sessions/{session_id}/messages",
        json={"content": "REST thì mình nghĩ nó liên quan tới web gì đó thôi."},
    )

    log = client.get(f"/api/teaching-sessions/{session_id}/log").json()
    assert log["gaps"], "the gap should be recorded for the instructor"
    assert log["gaps"][0]["chunk_title"] == "REST API"
