"""Teaching-message models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class MessageAuthor(str, Enum):
    """Who produced a message in a teaching conversation."""

    STUDENT = "student"
    AGENT = "agent"


class TeachingMessage(BaseModel):
    """One turn in the teaching conversation for a chunk."""

    id: str = Field(..., description="Stable message id")
    session_id: str
    chunk_id: Optional[str] = Field(
        default=None,
        description="Chunk this message belongs to (null for session-level msgs)",
    )
    author: MessageAuthor
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
