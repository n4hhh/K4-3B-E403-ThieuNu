"""Teaching-session models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from app.models.lesson import ChunkStatus
from app.models.message import TeachingMessage


class SessionStatus(str, Enum):
    """Top-level lifecycle status of a teaching session."""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class ValidationResult(BaseModel):
    """Outcome of validating a single student explanation against a chunk.

    `passed` is true when the explanation sufficiently covers the chunk.
    When `passed` is false, `missing_points` lists which key points are
    absent and `feedback` is what the agent should say to the student.
    """

    chunk_id: str
    passed: bool = False
    missing_points: List[str] = Field(default_factory=list)
    feedback: str = ""
    attempt: int = Field(default=1, ge=1)


class TeachingSession(BaseModel):
    """A student's attempt to teach back one lesson.

    The session owns:
        * a reference to the lesson id
        * a per-chunk status map (`chunk_states`)
        * the ordered list of chunk ids
        * the index of the chunk currently being taught
        * the message history
    """

    id: str
    lesson_id: str
    status: SessionStatus = SessionStatus.NOT_STARTED
    chunk_states: Dict[str, ChunkStatus] = Field(default_factory=dict)
    chunk_order: List[str] = Field(default_factory=list)
    current_chunk_index: int = 0
    messages: List[TeachingMessage] = Field(default_factory=list)
    attempts_per_chunk: Dict[str, int] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @property
    def current_chunk_id(self) -> Optional[str]:
        """Return the chunk currently being taught, or None if finished."""
        if 0 <= self.current_chunk_index < len(self.chunk_order):
            return self.chunk_order[self.current_chunk_index]
        return None

    @property
    def completed_chunk_count(self) -> int:
        return sum(1 for s in self.chunk_states.values() if s == ChunkStatus.COMPLETED)

    @property
    def total_chunk_count(self) -> int:
        return len(self.chunk_order)

    @property
    def progress_ratio(self) -> float:
        if not self.chunk_order:
            return 0.0
        return self.completed_chunk_count / self.total_chunk_count
