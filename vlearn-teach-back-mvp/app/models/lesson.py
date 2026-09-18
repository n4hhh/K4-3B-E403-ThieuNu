"""Lesson-related models.

A *Lesson* is the unit the student is studying. It is broken into
several *LessonChunk*s (discrete knowledge units), each with its own
key points. Optionally the lesson has a *Quiz* attached.
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class ChunkStatus(str, Enum):
    """Per-chunk status inside a teaching session."""

    LOCKED = "locked"
    CURRENT = "current"
    COMPLETED = "completed"


class LessonChunk(BaseModel):
    """One knowledge chunk inside a lesson.

    For the MVP scaffold, each chunk carries:
        * id            — stable identifier within the lesson
        * title         — short label (e.g. "HTTP Methods")
        * description   — one-paragraph summary of what the chunk covers
        * key_points    — the bullets the validator will look for
        * quality_bar   — optional description of what "good enough" means
        * content       — full text of the chunk (used by the validator)
        * page_start    — 1-based PDF page where the chunk starts
        * page_end      — 1-based PDF page where the chunk ends
        * key_concepts  — extracted salient noun phrases
    """

    id: str = Field(..., description="Stable chunk identifier within the lesson")
    title: str = Field(..., description="Short label for the chunk")
    description: str = Field("", description="One-paragraph summary")
    key_points: List[str] = Field(
        default_factory=list,
        description="Bullets the student's explanation must cover",
    )
    quality_bar: Optional[str] = Field(
        default=None,
        description="Optional quality criteria / 'good enough' description",
    )
    content: str = Field(
        default="",
        description="Full text content of the chunk (from the PDF)",
    )
    page_start: Optional[int] = Field(
        default=None,
        description="1-based page number where the chunk begins",
    )
    page_end: Optional[int] = Field(
        default=None,
        description="1-based page number where the chunk ends",
    )
    key_concepts: List[str] = Field(
        default_factory=list,
        description="Extracted salient noun phrases / concepts",
    )


class QuizQuestion(BaseModel):
    """A single quiz question."""

    id: str
    prompt: str
    options: List[str] = Field(default_factory=list)
    correct_index: Optional[int] = Field(
        default=None,
        description="Index into `options` of the correct answer; null for MVP stub",
    )
    explanation: Optional[str] = None


class Quiz(BaseModel):
    """Quiz attached to a lesson."""

    id: str
    lesson_id: str
    title: str = "Quiz"
    questions: List[QuizQuestion] = Field(default_factory=list)


class Lesson(BaseModel):
    """A VLearn lesson.

    Lessons are loaded from PDF files in ``../data/lesson/`` by
    ``PDFLessonService`` (with a JSON fallback at ``data/lessons.json``).
    """

    id: str
    title: str
    summary: str = Field(
        default="",
        description="Short summary shown on the lesson detail page",
    )
    description: str = Field(
        default="",
        description="Long-form description / learning objectives",
    )
    transcript: str = Field(
        default="",
        description="Source transcript the validator compares against",
    )
    duration_minutes: int = Field(default=0, ge=0)
    chunks: List[LessonChunk] = Field(default_factory=list)

    # PDF provenance
    source_file: Optional[str] = Field(
        default=None,
        description="Filename of the source PDF (if loaded from PDF)",
    )
    total_pages: Optional[int] = Field(
        default=None,
        description="Total page count of the source PDF",
    )
