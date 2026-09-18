"""API routes — JSON endpoints consumed by the front-end JavaScript.

These skeletons return placeholder / mock data. Real behaviour
(LLM validation, transcript mining, persistence) will be wired in
subsequent phases.
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.services.lesson_service import LessonService
from app.services.teaching_service import TeachingService


router = APIRouter(prefix="/api", tags=["api"])


def get_teaching_service(request: Request) -> TeachingService:
    """Return the teaching service attached to app state."""
    return request.app.state.teaching_service


def get_lesson_service(request: Request) -> LessonService:
    """Return the lesson service attached to app state."""
    return request.app.state.lesson_service


# ---------------------------------------------------------------------------
# Request / response payloads
# ---------------------------------------------------------------------------


class CreateSessionRequest(BaseModel):
    lesson_id: str = Field(..., description="ID of the lesson to teach back")


class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, description="Student's explanation")


# ---------------------------------------------------------------------------
# Lessons
# ---------------------------------------------------------------------------


@router.get("/lessons/{lesson_id}", name="api_get_lesson")
def get_lesson(request: Request, lesson_id: str):
    """Return a lesson (metadata + chunks)."""
    lesson_service = get_lesson_service(request)
    lesson = lesson_service.get_lesson(lesson_id)
    if lesson is None:
        raise HTTPException(status_code=404, detail=f"Lesson '{lesson_id}' not found")
    return lesson.model_dump()


@router.get("/lessons/{lesson_id}/quiz", name="api_get_quiz")
def get_quiz(request: Request, lesson_id: str):
    """Return the quiz for a lesson."""
    lesson_service = get_lesson_service(request)
    lesson = lesson_service.get_lesson(lesson_id)
    if lesson is None:
        raise HTTPException(status_code=404, detail=f"Lesson '{lesson_id}' not found")
    quiz = lesson_service.get_quiz(lesson_id)
    return quiz.model_dump()


# ---------------------------------------------------------------------------
# Teaching sessions
# ---------------------------------------------------------------------------


@router.post("/teaching-sessions", status_code=201, name="api_create_session")
def create_session(request: Request, payload: CreateSessionRequest):
    """Start a new teaching session for a lesson."""
    teaching_service = get_teaching_service(request)
    session = teaching_service.create_session(payload.lesson_id)
    if session is None:
        raise HTTPException(
            status_code=404, detail=f"Lesson '{payload.lesson_id}' not found"
        )
    return session.model_dump()


@router.get(
    "/teaching-sessions/{session_id}", name="api_get_session",
)
def get_session(request: Request, session_id: str):
    """Return the current state of a teaching session."""
    teaching_service = get_teaching_service(request)
    session = teaching_service.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    return session.model_dump()


@router.post(
    "/teaching-sessions/{session_id}/messages",
    name="api_send_message",
)
def send_message(request: Request, session_id: str, payload: SendMessageRequest):
    """Submit a student explanation. Returns the agent's reply + validation."""
    teaching_service = get_teaching_service(request)
    response = teaching_service.handle_student_message(session_id, payload.content)
    if response is None:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    return response


@router.post(
    "/teaching-sessions/{session_id}/next",
    name="api_next_chunk",
)
def next_chunk(request: Request, session_id: str):
    """Advance the session to the next chunk."""
    teaching_service = get_teaching_service(request)
    session = teaching_service.advance_chunk(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    return session.model_dump()


@router.get(
    "/teaching-sessions/{session_id}/result",
    name="api_session_result",
)
def session_result(request: Request, session_id: str):
    """Return the learning result for a finished session."""
    teaching_service = get_teaching_service(request)
    session = teaching_service.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    return {
        "session_id": session.id,
        "lesson_id": session.lesson_id,
        "status": session.status.value,
        "completed_chunks": [
            cid for cid, cs in session.chunk_states.items()
            if cs.value == "completed"
        ],
        "total_chunks": len(session.chunk_states),
    }
