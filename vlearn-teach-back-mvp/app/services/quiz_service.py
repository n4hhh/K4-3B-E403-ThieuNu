"""QuizService — end-of-lesson quiz, generated from the same source.

The quiz is not the AI feature; it is the *contrast*. It shows the pain
point the teach-back loop addresses: a student can pick the right option
without being able to explain why. Keeping it in the flow makes the
before/after visible in a five-minute demo.

Questions are generated once per lesson from the lesson's own chunks and
cached on disk, so a demo run costs nothing and always shows the same
questions. If generation fails, the repository's hand-written quiz (from
``data/lessons.json``) is used, and if there is none, the lesson simply
has no quiz — never a fabricated one.
"""

from __future__ import annotations

import json
import logging
import re
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.models.lesson import Lesson, Quiz, QuizQuestion
from app.services.ai.chat_provider import (
    ChatMessage,
    ChatProvider,
    ChatProviderError,
)
from app.services.ai.teach_prompts import QUIZ_SYSTEM, build_quiz_prompt

logger = logging.getLogger(__name__)

_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")
_CITATION_RE = re.compile(r"\[T\d{2}-\d{3}\]\s*")


class QuizService:
    """Generates and caches a lesson quiz."""

    def __init__(
        self,
        provider: ChatProvider,
        cache_dir: Path,
        question_count: int = 5,
        enabled: bool = True,
    ) -> None:
        self._provider = provider
        self._dir = Path(cache_dir)
        self._count = max(3, question_count)  # the brief requires at least 3
        self._enabled = enabled
        self._lock = threading.Lock()

    # ------------------------------------------------------------------

    def get_quiz(self, lesson: Lesson, fallback: Optional[Quiz] = None) -> Optional[Quiz]:
        """Return the quiz for ``lesson``, generating it if needed."""
        with self._lock:
            cached = self._load(lesson.id)
            if cached is not None:
                return cached

            generated = self._generate(lesson) if self._enabled else None
            if generated is not None:
                self._save(lesson.id, generated)
                return generated

        if fallback is not None:
            logger.info("Using the repository quiz for lesson %s.", lesson.id)
        return fallback

    # ------------------------------------------------------------------

    def _generate(self, lesson: Lesson) -> Optional[Quiz]:
        summaries: List[Dict[str, Any]] = [
            {
                "title": chunk.title,
                "key_points": chunk.key_points,
                "content": _CITATION_RE.sub("", chunk.content),
            }
            for chunk in lesson.chunks
        ]
        if not summaries:
            return None

        messages = [
            ChatMessage(role="system", content=QUIZ_SYSTEM),
            ChatMessage(
                role="user",
                content=build_quiz_prompt(
                    lesson_title=lesson.title,
                    chunk_summaries=summaries,
                    count=self._count,
                ),
            ),
        ]

        try:
            result = self._provider.complete_json(
                messages, temperature=0.4, max_tokens=4000
            )
        except ChatProviderError as exc:
            logger.warning("Quiz generation failed for %s: %s", lesson.id, exc)
            return None

        questions = self._parse_questions(lesson.id, result.data.get("questions"))
        if len(questions) < 3:
            logger.warning(
                "Quiz generation for %s produced only %d usable question(s).",
                lesson.id,
                len(questions),
            )
            return None

        return Quiz(
            id=f"quiz-{lesson.id}",
            lesson_id=lesson.id,
            title=f"Quiz · {lesson.title}",
            questions=questions,
        )

    @staticmethod
    def _parse_questions(lesson_id: str, raw: Any) -> List[QuizQuestion]:
        """Keep only well-formed questions; a malformed one is dropped.

        A question with a wrong ``correct_index`` would mark a correct
        answer wrong, which is worse than having one question fewer.
        """
        if not isinstance(raw, list):
            return []

        questions: List[QuizQuestion] = []
        for index, item in enumerate(raw, start=1):
            if not isinstance(item, dict):
                continue
            prompt = str(item.get("prompt") or "").strip()
            options = [
                str(o).strip() for o in (item.get("options") or []) if str(o).strip()
            ]
            if not prompt or len(options) < 2:
                continue
            try:
                correct = int(item.get("correct_index"))
            except (TypeError, ValueError):
                continue
            if not 0 <= correct < len(options):
                continue
            questions.append(
                QuizQuestion(
                    id=f"{lesson_id}-q{index}",
                    prompt=prompt,
                    options=options,
                    correct_index=correct,
                    explanation=str(item.get("explanation") or "").strip() or None,
                )
            )
        return questions

    # ------------------------------------------------------------------
    # Disk cache
    # ------------------------------------------------------------------

    def _path(self, lesson_id: str) -> Path:
        return self._dir / f"{_SAFE_NAME_RE.sub('_', lesson_id)}.quiz.json"

    def _load(self, lesson_id: str) -> Optional[Quiz]:
        path = self._path(lesson_id)
        if not path.exists():
            return None
        try:
            return Quiz.model_validate(json.loads(path.read_text(encoding="utf-8")))
        except Exception as exc:  # noqa: BLE001 - a bad cache is not fatal
            logger.warning("Ignoring unreadable quiz cache %s: %s", path, exc)
            return None

    def _save(self, lesson_id: str, quiz: Quiz) -> None:
        try:
            self._dir.mkdir(parents=True, exist_ok=True)
            self._path(lesson_id).write_text(
                json.dumps(quiz.model_dump(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as exc:
            logger.warning("Could not cache quiz for %s: %s", lesson_id, exc)


__all__ = ["QuizService"]
