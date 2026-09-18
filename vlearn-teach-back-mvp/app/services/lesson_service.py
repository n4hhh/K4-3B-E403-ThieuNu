"""LessonService — read-side service for lessons and quizzes."""

from __future__ import annotations

from typing import List, Optional

from app.models.lesson import Lesson, LessonChunk, Quiz
from app.repositories.lesson_repository import LessonRepository


class LessonService:
    """Loads lessons / chunks / quizzes via the repository.

    ``quiz_service``, when supplied, generates a quiz from the lesson's
    own source text and falls back to whatever the repository holds. It
    is optional so the scaffold (and the tests) can run without it.
    """

    def __init__(
        self,
        repository: Optional[LessonRepository] = None,
        quiz_service: Optional[object] = None,
    ) -> None:
        self._repo = repository or LessonRepository()
        self._quiz_service = quiz_service

    # ------------------------------------------------------------------
    # Lessons
    # ------------------------------------------------------------------

    def list_lessons(self) -> List[Lesson]:
        return self._repo.list_lessons()

    def get_lesson(self, lesson_id: str) -> Optional[Lesson]:
        return self._repo.get_lesson(lesson_id)

    def get_chunk(self, lesson_id: str, chunk_id: str) -> Optional[LessonChunk]:
        lesson = self._repo.get_lesson(lesson_id)
        if lesson is None:
            return None
        for chunk in lesson.chunks:
            if chunk.id == chunk_id:
                return chunk
        return None

    # ------------------------------------------------------------------
    # Quiz
    # ------------------------------------------------------------------

    def get_quiz(self, lesson_id: str) -> Optional[Quiz]:
        """Return the lesson's quiz, generating one when possible."""
        stored = self._repo.get_quiz(lesson_id)
        if self._quiz_service is None:
            return stored

        lesson = self._repo.get_lesson(lesson_id)
        if lesson is None:
            return stored
        return self._quiz_service.get_quiz(lesson, fallback=stored)
