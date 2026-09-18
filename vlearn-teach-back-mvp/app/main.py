"""FastAPI application entry point.

This module wires together:
    * the Jinja2 template engine
    * static file serving
    * page routes (server-rendered HTML)
    * API routes (JSON)
    * shared service singletons (so page and API routes use the same in-memory state)

It is intentionally thin: all business logic lives in
`app.services` and `app.repositories`.
"""

from pathlib import Path

import logging

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.routers import api as api_router
from app.routers import documentizer as documentizer_router
from app.routers import pages as pages_router
from app.repositories.lesson_repository import LessonRepository
from app.repositories.published_lesson_repository import (
    PublishedLessonRepository,
)
from app.services.lesson_service import LessonService
from app.services.mock_agent_service import MockAgentService
from app.services.pdf_lesson_service import PDFLessonService
from app.services.teaching_service import TeachingService
from app.services.validator_service import ValidatorService


BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("vlearn")


def create_app() -> FastAPI:
    """Application factory.

    Kept as a factory so tests can instantiate isolated app instances
    in the future if needed.
    """
    application = FastAPI(
        title="VLearn Teach Back Agent MVP",
        description=(
            "Scaffold for the Teach Back Agent: a stateful teaching workflow "
            "where a student explains lesson chunks back to an AI agent, which "
            "validates understanding before allowing the student to continue."
        ),
        version="0.1.0",
    )

    # Shared service singletons (kept on app.state so pages & API routes see
    # the same in-memory state — especially the SessionRepository).
    #
    # Lesson source: PDFs from VLEARN_LESSON_DIR are preferred; the
    # repository falls back to data/lessons.json when no PDFs are present.
    application.state.pdf_lesson_service = PDFLessonService(
        lesson_dir=settings.lesson_dir,
    )
    # Eagerly load PDFs at startup so the first request is fast and we can
    # log a clear message about which source is being used.
    try:
        discovered = application.state.pdf_lesson_service.list_lessons()
        logger.info(
            "PDFLessonService discovered %d lesson(s) in %s.",
            len(discovered), settings.lesson_dir,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to load PDF lessons: %s", exc)
        discovered = []

    application.state.lesson_repository = LessonRepository(
        pdf_service=application.state.pdf_lesson_service,
        json_fallback=settings.json_fallback_file,
        published_repo=PublishedLessonRepository(),
    )
    application.state.lesson_service = LessonService(
        repository=application.state.lesson_repository,
    )
    application.state.validator_service = ValidatorService()
    application.state.agent_service = MockAgentService()
    application.state.teaching_service = TeachingService(
        lesson_service=application.state.lesson_service,
        validator=application.state.validator_service,
        agent=application.state.agent_service,
    )
    logger.info(
        "LessonRepository source: %s (%d lessons).",
        application.state.lesson_repository.source,
        len(application.state.lesson_repository.list_lessons()),
    )

    # Static assets (CSS / JS)
    application.mount(
        "/static",
        StaticFiles(directory=str(STATIC_DIR)),
        name="static",
    )

    # Routers
    application.include_router(pages_router.router)
    application.include_router(api_router.router)
    application.include_router(documentizer_router.router)

    return application


app = create_app()


if __name__ == "__main__":  # pragma: no cover - convenience entry
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
