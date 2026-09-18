"""Teaching-session models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.models.lesson import ChunkStatus
from app.models.message import TeachingMessage


class SessionStatus(str, Enum):
    """Top-level lifecycle status of a teaching session."""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class GapType(str, Enum):
    """Why an explanation did not pass.

    The distinction matters: an *incomplete* explanation needs a question
    about the missing piece, while a *contradicted* one needs a question
    about the claim the student actually made. Asking the wrong kind of
    question is the classic way a teach-back agent feels dumb.
    """

    NONE = "none"
    INCOMPLETE = "incomplete"   # a required point was not mentioned
    VAGUE = "vague"             # mentioned, but too thin to count
    CONTRADICTED = "contradicted"  # states something the source denies
    COPIED = "copied"           # pasted from the source instead of explained
    OFF_TOPIC = "off_topic"     # not about this chunk


class ValidationResult(BaseModel):
    """Outcome of validating a single student explanation against a chunk.

    `passed` is true when the explanation sufficiently covers the chunk.
    When `passed` is false, `missing_points` lists which key points are
    absent and `feedback` is what the agent should say to the student.

    The remaining fields carry the evidence behind that verdict: which
    points *were* covered, which source passages the judgement rests on,
    and the single question the agent will ask back. They exist so the
    result can be shown to the student and audited by an instructor
    rather than being an opaque pass/fail.
    """

    chunk_id: str
    passed: bool = False
    missing_points: List[str] = Field(default_factory=list)
    covered_points: List[str] = Field(default_factory=list)
    feedback: str = ""
    attempt: int = Field(default=1, ge=1)

    gap_type: GapType = GapType.NONE
    ask_back: str = Field(
        default="",
        description="The one follow-up question the agent asks; empty on pass",
    )
    citations: List[str] = Field(
        default_factory=list,
        description="Source passage codes (e.g. T04-021) backing the verdict",
    )
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    is_copied: bool = Field(
        default=False,
        description="Explanation was near-verbatim source text",
    )
    needs_review: bool = Field(
        default=False,
        description="Passed on the attempt limit rather than on merit",
    )
    note_for_instructor: str = ""
    evaluator: str = Field(
        default="heuristic",
        description="Which path produced this verdict: 'ai' or 'heuristic'",
    )

    def public_dump(self) -> Dict[str, Any]:
        """Return the fields that may be sent to the student's browser.

        ``covered_points``, ``missing_points`` and the instructor note
        name the very content the student is being asked to produce.
        Shipping them to the page — even unrendered — would put the
        answer one devtools panel away, which is the exact thing the
        agent's wording is careful to avoid. They stay server-side, in
        the session log the instructor reads.
        """
        payload = self.model_dump(mode="json")
        for field_name in ("covered_points", "missing_points", "note_for_instructor"):
            payload.pop(field_name, None)
        return payload


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

    # --- learning evidence -------------------------------------------
    # What the session is really for: not "did the AI answer", but what
    # the student had to clarify before the explanation held up.
    clarification_count: int = Field(
        default=0, description="How many times the agent asked back"
    )
    needs_review_chunks: List[str] = Field(
        default_factory=list,
        description="Chunks that hit the attempt limit without passing cleanly",
    )
    gap_log: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="One entry per detected gap, for the learning result and "
        "the instructor log",
    )

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

    @property
    def total_loops(self) -> int:
        """Total student explanations across the whole session."""
        return sum(self.attempts_per_chunk.values())

    @property
    def clarified_areas(self) -> List[str]:
        """Distinct topics the student worked through, newest last.

        The learning-result screen shows these as "Areas clarified" —
        the most useful thing a student can take away from a session.

        Chunks that ended on the attempt limit are left out on purpose:
        the student never did explain those, so naming the point would
        be handing them the answer after the fact rather than reporting
        what they figured out. They appear under "Nên xem lại" instead.
        """
        seen: List[str] = []
        for entry in self.gap_log:
            if entry.get("chunk_id") in self.needs_review_chunks:
                continue
            label = str(entry.get("label", "")).strip()
            if label and label not in seen:
                seen.append(label)
        return seen

    def public_dump(self) -> Dict[str, Any]:
        """Return the session as the student's browser may see it.

        ``gap_log`` records which key points were missing at each turn —
        instructor material, and the answer to the question the student
        is still being asked. It never goes to the page.
        """
        payload = self.model_dump(mode="json")
        payload.pop("gap_log", None)
        return payload
