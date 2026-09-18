"""Warm the Teach-Back caches before a demo.

Deriving a chunk's key points costs one model call and a few seconds.
That is fine in the background but painful in front of an audience, so
run this once after the lesson source changes::

    python -m app.cli_prepare                      # every lesson
    python -m app.cli_prepare transcript-04-clean  # one lesson
    python -m app.cli_prepare --quiz               # also build quizzes
    python -m app.cli_prepare --list               # just show the catalogue

Results land in ``data/cache/`` and are reused on every later run. The
files are plain JSON on purpose: an instructor can open one and correct
a key point before class.
"""

from __future__ import annotations

import argparse
import logging
import sys
from typing import List, Optional

from app.config import settings
from app.repositories.lesson_repository import LessonRepository
from app.repositories.published_lesson_repository import PublishedLessonRepository
from app.services.ai.chat_provider import build_chat_provider_safe
from app.services.lesson_prep_service import LessonPrepService
from app.services.pdf_lesson_service import PDFLessonService
from app.services.quiz_service import QuizService
from app.services.transcript_lesson_service import TranscriptLessonService

logger = logging.getLogger("vlearn.prepare")


def build_repository() -> LessonRepository:
    """Return a repository wired exactly like the running app's."""
    return LessonRepository(
        pdf_service=PDFLessonService(lesson_dir=settings.lesson_dir),
        json_fallback=settings.json_fallback_file,
        published_repo=PublishedLessonRepository(),
        transcript_service=TranscriptLessonService(
            transcript_dir=settings.transcript_dir,
            max_chunks=settings.teach_back_max_chunks,
        ),
    )


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m app.cli_prepare",
        description="Pre-compute teach-back criteria (and optionally quizzes).",
    )
    parser.add_argument(
        "lesson_ids",
        nargs="*",
        help="Lesson ids to prepare. Default: every lesson in the catalogue.",
    )
    parser.add_argument(
        "--quiz", action="store_true", help="Also generate and cache the quiz."
    )
    parser.add_argument(
        "--list", action="store_true", help="List the catalogue and exit."
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    repository = build_repository()
    lessons = repository.list_lessons()
    if not lessons:
        print("Không tìm thấy bài học nào. Kiểm tra lại VLEARN_PACK_DIR.")
        return 1

    if args.list:
        for lesson in lessons:
            print(f"{lesson.id}\t{len(lesson.chunks)} phần\t{lesson.title}")
        return 0

    if args.lesson_ids:
        wanted = set(args.lesson_ids)
        selected = [lesson for lesson in lessons if lesson.id in wanted]
        missing = wanted - {lesson.id for lesson in selected}
        for lesson_id in sorted(missing):
            print(f"Bỏ qua: không có bài học '{lesson_id}'.")
        if not selected:
            return 1
    else:
        selected = lessons

    provider = build_chat_provider_safe(settings.teach_back_provider)
    ai_enabled = getattr(provider, "name", "mock") != "mock"
    if not ai_enabled:
        print(
            "CẢNH BÁO: không gọi được model — sẽ chỉ sinh key point bằng "
            "heuristic. Kiểm tra TEACH_BACK_* trong .env."
        )

    prep = LessonPrepService(
        provider=provider, cache_dir=settings.cache_dir, enabled=ai_enabled
    )
    quiz_service = QuizService(
        provider=provider, cache_dir=settings.cache_dir, enabled=ai_enabled
    )

    for lesson in selected:
        print(f"\n▶ {lesson.title}  ({lesson.id})")
        for index, chunk in enumerate(lesson.chunks, start=1):
            criteria = prep.ensure_chunk(lesson, chunk)
            print(
                f"  {index}. {chunk.title} — "
                f"{len(criteria.key_points)} key point "
                f"[{criteria.source}]"
            )
        if args.quiz:
            quiz = quiz_service.get_quiz(lesson)
            count = len(quiz.questions) if quiz else 0
            print(f"  quiz: {count} câu")

    print(f"\nĐã ghi cache vào {settings.cache_dir}")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry
    sys.exit(main())
