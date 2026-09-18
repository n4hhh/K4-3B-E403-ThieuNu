"""Page routes — server-rendered HTML via Jinja2.

These are intentionally thin: they delegate to services for data
and just render templates.
"""

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.services.lesson_service import LessonService
from app.services.teaching_service import TeachingService


BASE_DIR = Path(__file__).resolve().parent.parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def get_teaching_service(request: Request) -> TeachingService:
    """Return the teaching service attached to app state (shared with API)."""
    return request.app.state.teaching_service


def get_lesson_service(request: Request) -> LessonService:
    """Return the lesson service attached to app state (shared with API)."""
    return request.app.state.lesson_service


router = APIRouter(tags=["pages"])


@router.get("/", response_class=HTMLResponse, name="home")
def index(request: Request):
    """Landing page. Currently lists the available lessons."""
    lesson_service = get_lesson_service(request)
    lessons = lesson_service.list_lessons()
    return templates.TemplateResponse(
        request=request,
        name="lesson.html",  # reuse lesson template as the index for now
        context={"request": request, "lessons": lessons, "selected": None},
    )


@router.get("/lesson/{lesson_id}", response_class=HTMLResponse, name="lesson_detail")
def lesson_detail(request: Request, lesson_id: str):
    """Lesson detail page: description + chunks overview + 'Teach back' CTA."""
    lesson_service = get_lesson_service(request)
    lesson = lesson_service.get_lesson(lesson_id)
    if lesson is None:
        raise HTTPException(status_code=404, detail=f"Lesson '{lesson_id}' not found")
    return templates.TemplateResponse(
        request=request,
        name="lesson.html",
        context={"request": request, "lesson": lesson, "lessons": [lesson], "selected": lesson},
    )


@router.get(
    "/lesson/{lesson_id}/teach",
    response_class=HTMLResponse,
    name="session_intro",
)
def session_intro(request: Request, lesson_id: str):
    """Intro page before a teaching session begins."""
    lesson_service = get_lesson_service(request)
    lesson = lesson_service.get_lesson(lesson_id)
    if lesson is None:
        raise HTTPException(status_code=404, detail=f"Lesson '{lesson_id}' not found")
    return templates.TemplateResponse(
        request=request,
        name="session_intro.html",
        context={"request": request, "lesson": lesson},
    )


@router.get("/session/{session_id}", response_class=HTMLResponse, name="teaching")
def teaching(request: Request, session_id: str):
    """The main teaching-loop page."""
    teaching_service = get_teaching_service(request)
    lesson_service = get_lesson_service(request)
    session = teaching_service.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    lesson = lesson_service.get_lesson(session.lesson_id)
    return templates.TemplateResponse(
        request=request,
        name="teaching.html",
        context={"request": request, "session": session, "lesson": lesson},
    )


@router.get(
    "/session/{session_id}/result",
    response_class=HTMLResponse,
    name="lesson_result",
)
def lesson_result(request: Request, session_id: str):
    """Lesson learning-result page (after all chunks pass)."""
    teaching_service = get_teaching_service(request)
    lesson_service = get_lesson_service(request)
    session = teaching_service.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    lesson = lesson_service.get_lesson(session.lesson_id)
    return templates.TemplateResponse(
        request=request,
        name="result.html",
        context={"request": request, "session": session, "lesson": lesson},
    )


@router.get("/lesson/{lesson_id}/quiz", response_class=HTMLResponse, name="quiz")
def quiz(request: Request, lesson_id: str):
    """Quiz page."""
    lesson_service = get_lesson_service(request)
    lesson = lesson_service.get_lesson(lesson_id)
    if lesson is None:
        raise HTTPException(status_code=404, detail=f"Lesson '{lesson_id}' not found")
    quiz_data = lesson_service.get_quiz(lesson_id)
    return templates.TemplateResponse(
        request=request,
        name="quiz.html",
        context={"request": request, "lesson": lesson, "quiz": quiz_data},
    )
