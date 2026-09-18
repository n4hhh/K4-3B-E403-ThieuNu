"""MockAgentService — generates agent messages.

This is a clean stub: deterministic, no external calls. It exists so
the rest of the application can be developed and tested without any
real LLM integration. The next phase will swap this for a real
Gemini / OpenAI client.
"""

from __future__ import annotations

from typing import Optional

from app.models.lesson import Lesson, LessonChunk
from app.models.session import ValidationResult


class MockAgentService:
    """Deterministic stand-in for the real Agent."""

    def opening_message(self, lesson: Lesson) -> str:
        return (
            f"Welcome — you will teach me '{lesson.title}'. "
            f"I have broken it into {len(lesson.chunks)} parts. "
            "Let's start with the first one."
        )

    def chunk_prompt(self, chunk: LessonChunk) -> str:
        return (
            f"Please teach me about: **{chunk.title}**.\n\n"
            f"{chunk.description}"
        )

    def reply_to_explanation(
        self,
        chunk: Optional[LessonChunk],
        validation: ValidationResult,
    ) -> str:
        if validation.passed:
            return validation.feedback + " We can move on to the next part."
        return validation.feedback

    def ask_follow_up(self, missing_point: str) -> str:
        return f"Could you tell me more about: {missing_point}?"
