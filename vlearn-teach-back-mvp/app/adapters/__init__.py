"""Adapters — Phase 3A.5 ↔ existing model bridges."""

from app.adapters.structured_lesson_adapter import (
    StructuredLessonAdapter,
    structured_lesson_to_lesson,
)

__all__ = ["StructuredLessonAdapter", "structured_lesson_to_lesson"]