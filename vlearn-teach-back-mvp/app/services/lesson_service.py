"""LessonService — read-side service for lessons and quizzes."""

from __future__ import annotations

from typing import List, Optional

from app.models.lesson import Lesson, LessonChunk, Quiz
from app.repositories.lesson_repository import LessonRepository


class LessonService:
    """Loads lessons / chunks / quizzes via the repository."""

    def __init__(self, repository: Optional[LessonRepository] = None) -> None:
        self._repo = repository or LessonRepository()

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
        return self._repo.get_quiz(lesson_id)
