"""Shared pytest fixtures.

The suite must be hermetic: no network, no dependency on the VLearn data
pack being present, and no cache written into the developer's working
copy. The ``client`` fixture therefore builds the real application and
then rebinds its services onto the built-in demo lesson
(``data/lessons.json``) and the offline mock provider.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app as production_app
from app.main import create_app
from app.repositories.lesson_repository import LessonRepository
from app.services.ai.chat_provider import MockChatProvider
from app.services.ai_validator_service import AIValidatorService
from app.services.lesson_service import LessonService
from app.services.session_log_service import SessionLogService
from app.services.teach_back_agent_service import TeachBackAgentService
from app.services.teaching_service import TeachingService

DEMO_LESSONS_FILE = Path(__file__).resolve().parent.parent / "data" / "lessons.json"
DEMO_LESSON_ID = "rest-api-http-methods"


@pytest.fixture()
def demo_lesson_id() -> str:
    """The lesson id the hermetic fixtures serve."""
    return DEMO_LESSON_ID


@pytest.fixture()
def client(tmp_path) -> TestClient:
    """TestClient over an app pinned to the demo lesson and mock AI."""
    application = create_app()

    repository = LessonRepository(lessons_file=DEMO_LESSONS_FILE)
    lesson_service = LessonService(repository=repository)
    provider = MockChatProvider()

    application.state.chat_provider = provider
    application.state.lesson_repository = repository
    application.state.lesson_service = lesson_service
    # ``enabled=False`` keeps the validator on its deterministic
    # heuristic path, so assertions do not depend on model output.
    application.state.validator_service = AIValidatorService(
        provider=provider, max_attempts=4, enabled=False
    )
    application.state.agent_service = TeachBackAgentService()
    application.state.session_log_service = SessionLogService(
        log_dir=tmp_path / "session-logs"
    )
    application.state.teaching_service = TeachingService(
        lesson_service=lesson_service,
        validator=application.state.validator_service,
        agent=application.state.agent_service,
        session_log=application.state.session_log_service,
    )
    return TestClient(application)


@pytest.fixture()
def production_client() -> TestClient:
    """TestClient over the app exactly as it boots in production.

    Only for tests that check wiring (routes exist, app starts). Anything
    asserting on lesson content should use ``client`` instead.
    """
    return TestClient(production_app)
