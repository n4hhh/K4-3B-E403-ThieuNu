"""Smoke tests for the lesson repository and the mock lesson data."""

from pathlib import Path

import pytest

from app.repositories.lesson_repository import LessonRepository


DATA_FILE = (
    Path(__file__).resolve().parent.parent / "data" / "lessons.json"
)


def test_repository_loads_lessons_json():
    repo = LessonRepository(lessons_file=DATA_FILE)
    lessons = repo.list_lessons()
    assert len(lessons) >= 1


def test_repository_returns_expected_lesson():
    repo = LessonRepository(lessons_file=DATA_FILE)
    lesson = repo.get_lesson("rest-api-http-methods")
    assert lesson is not None
    assert lesson.title == "REST API & HTTP Methods"


def test_lesson_has_five_chunks():
    repo = LessonRepository(lessons_file=DATA_FILE)
    lesson = repo.get_lesson("rest-api-http-methods")
    assert lesson is not None
    assert len(lesson.chunks) == 5


def test_chunk_titles_match_specification():
    repo = LessonRepository(lessons_file=DATA_FILE)
    lesson = repo.get_lesson("rest-api-http-methods")
    assert lesson is not None
    expected_titles = [
        "REST API",
        "Client \u2013 Server",
        "HTTP Methods",
        "HTTP Status Codes",
        "Stateless",
    ]
    actual_titles = [c.title for c in lesson.chunks]
    assert actual_titles == expected_titles


def test_quiz_has_at_least_three_questions():
    repo = LessonRepository(lessons_file=DATA_FILE)
    quiz = repo.get_quiz("rest-api-http-methods")
    assert quiz is not None
    assert len(quiz.questions) >= 3


@pytest.mark.parametrize(
    "missing_lesson_id",
    ["does-not-exist", ""],
)
def test_repository_returns_none_for_missing_lesson(missing_lesson_id):
    repo = LessonRepository(lessons_file=DATA_FILE)
    assert repo.get_lesson(missing_lesson_id) is None
