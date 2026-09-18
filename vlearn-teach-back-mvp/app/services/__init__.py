"""Services package — business logic layer.

The services package deliberately avoids eagerly importing
:class:`~app.services.lesson_service` at module load time, because
doing so triggers a circular import with
:class:`~app.repositories.lesson_repository.LessonRepository`. Downstream
modules that need :class:`LessonService` should import it lazily (e.g.
inside the function that uses it, or via a factory).
"""

from app.services.mock_agent_service import MockAgentService  # noqa: F401
from app.services.pdf_reader import PDFReader  # noqa: F401
from app.services.phase3a_pipeline import Phase3APipeline  # noqa: F401
from app.services.raw_document_service import RawDocumentService  # noqa: F401
from app.services.teaching_service import TeachingService  # noqa: F401
from app.services.validator_service import ValidatorService  # noqa: F401


__all__ = [
    "MockAgentService",
    "PDFReader",
    "Phase3APipeline",
    "RawDocumentService",
    "TeachingService",
    "ValidatorService",
]


def __getattr__(name: str):
    """Lazy import for LessonService to break the circular dependency."""
    if name == "LessonService":
        from app.services.lesson_service import LessonService

        return LessonService
    raise AttributeError(f"module 'app.services' has no attribute {name!r}")
