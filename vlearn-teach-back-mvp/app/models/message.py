"""Teaching-message models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class MessageAuthor(str, Enum):
    """Who produced a message in a teaching conversation."""

    STUDENT = "student"
    AGENT = "agent"
    SYSTEM = "system"


class MessageKind(str, Enum):
    """What role a message plays in the teaching loop.

    The UI renders each kind differently — an ask-back needs a "cần làm
    rõ" badge, a pass needs a checkmark — so the kind is decided on the
    server, where the verdict is, rather than re-derived in JavaScript.
    """

    PROMPT = "prompt"            # agent asks the student to teach a chunk
    EXPLANATION = "explanation"  # student teaches
    GAP = "gap"                  # agent asks back at a hole
    VALIDATION = "validation"    # agent accepts the explanation
    CHUNK_COMPLETE = "chunk_complete"
    TEXT = "text"


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
    kind: MessageKind = MessageKind.TEXT
    badge: Optional[str] = Field(
        default=None,
        description="Short label shown on the bubble (e.g. 'Còn thiếu ý')",
    )
    citations: List[str] = Field(
        default_factory=list,
        description="Source passage codes referenced by this message",
    )
    meta: Dict[str, Any] = Field(
        default_factory=dict,
        description="Extra render hints; never contains lesson answers",
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
