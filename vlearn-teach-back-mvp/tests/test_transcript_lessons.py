"""Tests for building lessons out of VLearn transcript Markdown."""

from __future__ import annotations

import textwrap

import pytest

from app.services.transcript_lesson_service import TranscriptLessonService, slugify


def write_transcript(directory, name: str, sections: dict) -> None:
    """Write a transcript file shaped like the real data pack."""
    lines = [
        "# Transcript bài giảng (bản sạch) — Buổi thử nghiệm",
        "> **Nguồn:** bản ASR thô · **Quy ước:** `[Txx-NNN]` mã đoạn",
        "",
    ]
    counter = 1
    for title, paragraphs in sections.items():
        lines.append(f"## {title}")
        for paragraph in paragraphs:
            lines.append(f"**[T09-{counter:03d}]** {paragraph}")
            counter += 1
        lines.append("")
    (directory / name).write_text("\n".join(lines), encoding="utf-8")


LONG = (
    "Đây là một đoạn giảng dài để vượt ngưỡng nội dung tối thiểu. " * 12
).strip()


@pytest.fixture()
def transcript_dir(tmp_path):
    write_transcript(
        tmp_path,
        "transcript-09-clean.md",
        {
            "Chào lớp và giới thiệu giảng viên": [LONG],
            "Cơ chế dự đoán token": [LONG, LONG],
            "Vì sao mô hình bịa": [LONG],
            "Ghi chú ngắn": ["Một câu rất ngắn."],
        },
    )
    (tmp_path / "README.md").write_text("# Không phải bài giảng", encoding="utf-8")
    return tmp_path


def test_builds_one_lesson_per_transcript(transcript_dir):
    service = TranscriptLessonService(transcript_dir, max_chunks=5)
    lessons = service.list_lessons()
    assert len(lessons) == 1
    assert lessons[0].id == "transcript-09-clean"


def test_readme_is_not_a_lesson(transcript_dir):
    service = TranscriptLessonService(transcript_dir)
    assert [p.name for p in service.discover()] == ["transcript-09-clean.md"]


def test_housekeeping_and_tiny_sections_are_dropped(transcript_dir):
    service = TranscriptLessonService(transcript_dir, max_chunks=5)
    titles = [c.title for c in service.list_lessons()[0].chunks]
    assert titles == ["Cơ chế dự đoán token", "Vì sao mô hình bịa"]


def test_citation_codes_are_kept_in_chunk_content(transcript_dir):
    """The validator is asked to cite passages, so it must see the codes."""
    chunk = TranscriptLessonService(transcript_dir).list_lessons()[0].chunks[0]
    assert "[T09-" in chunk.content


def test_chunk_count_is_capped(tmp_path):
    write_transcript(
        tmp_path,
        "transcript-10-clean.md",
        {f"Phần số {i}": [LONG] for i in range(1, 9)},
    )
    lesson = TranscriptLessonService(tmp_path, max_chunks=3).list_lessons()[0]
    assert len(lesson.chunks) == 3
    # …and the surviving sections keep their original order.
    assert [c.title for c in lesson.chunks] == [
        "Phần số 1",
        "Phần số 2",
        "Phần số 3",
    ]


def test_missing_directory_yields_no_lessons(tmp_path):
    service = TranscriptLessonService(tmp_path / "khong-ton-tai")
    assert service.list_lessons() == []


def test_lesson_title_drops_the_boilerplate_prefix(transcript_dir):
    lesson = TranscriptLessonService(transcript_dir).list_lessons()[0]
    assert lesson.title == "Buổi thử nghiệm"


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Vì sao LLM bịa", "vi-sao-llm-bia"),
        ("Đường dẫn & URL", "duong-dan-url"),
        ("   ", "section"),
    ],
)
def test_slugify(raw, expected):
    assert slugify(raw) == expected
