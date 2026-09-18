"""TeachingService — orchestrates a teaching session.

Responsibilities:
    * create / fetch sessions
    * track which chunk is current
    * accept student messages
    * make sure the current chunk has teach-back criteria before grading
    * delegate grading to the validator and wording to the agent
    * record the learning evidence (loops, clarifications, gaps)
    * advance / complete chunks and the session itself

This class deliberately holds **no I/O logic** — repositories and
sub-services handle that. Routes call into this class only.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Protocol

from app.models.lesson import ChunkStatus, LessonChunk
from app.models.message import MessageAuthor, MessageKind, TeachingMessage
from app.models.session import SessionStatus, TeachingSession, ValidationResult
from app.repositories.session_repository import SessionRepository
from app.services.lesson_service import LessonService

logger = logging.getLogger(__name__)

# How many previous turns of the current chunk the grader sees. Enough
# to avoid repeating a question, short enough to keep the prompt cheap.
_HISTORY_TURNS = 6


class _Preparer(Protocol):
    """Anything that can fill a chunk's key points (LessonPrepService)."""

    def ensure_chunk(self, lesson: Any, chunk: LessonChunk) -> Any: ...


class TeachingService:
    """Owns the lifecycle of a `TeachingSession`."""

    def __init__(
        self,
        lesson_service: LessonService,
        session_repo: Optional[SessionRepository] = None,
        validator: Optional[Any] = None,
        agent: Optional[Any] = None,
        preparer: Optional[_Preparer] = None,
        session_log: Optional[Any] = None,
    ) -> None:
        self._lesson_service = lesson_service
        self._session_repo = session_repo or SessionRepository()
        if validator is None:
            from app.services.validator_service import ValidatorService

            validator = ValidatorService()
        if agent is None:
            from app.services.mock_agent_service import MockAgentService

            agent = MockAgentService()
        self._validator = validator
        self._agent = agent
        self._preparer = preparer
        self._session_log = session_log

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    def create_session(self, lesson_id: str) -> Optional[TeachingSession]:
        """Create a new teaching session for the given lesson."""
        lesson = self._lesson_service.get_lesson(lesson_id)
        if lesson is None:
            return None

        chunk_order = [c.id for c in lesson.chunks]
        chunk_states: Dict[str, ChunkStatus] = {
            cid: (ChunkStatus.LOCKED if i > 0 else ChunkStatus.CURRENT)
            for i, cid in enumerate(chunk_order)
        }

        session = TeachingSession(
            id=str(uuid.uuid4()),
            lesson_id=lesson_id,
            status=SessionStatus.IN_PROGRESS,
            chunk_order=chunk_order,
            chunk_states=chunk_states,
            current_chunk_index=0,
        )

        # Derive criteria for the first chunk now, so the very first
        # explanation is graded against real key points rather than an
        # empty list.
        if lesson.chunks:
            self._prepare(lesson, lesson.chunks[0])

        opening = self._agent.opening_message(lesson)
        session.messages.append(
            TeachingMessage(
                id=str(uuid.uuid4()),
                session_id=session.id,
                chunk_id=session.current_chunk_id,
                author=MessageAuthor.AGENT,
                content=opening,
                kind=MessageKind.PROMPT,
            )
        )

        return self._session_repo.save(session)

    def get_session(self, session_id: str) -> Optional[TeachingSession]:
        return self._session_repo.get(session_id)

    # ------------------------------------------------------------------
    # Teaching loop
    # ------------------------------------------------------------------

    def handle_student_message(
        self, session_id: str, content: str
    ) -> Optional[Dict[str, Any]]:
        """Accept a student explanation; return agent reply + validation."""
        session = self._session_repo.get(session_id)
        if session is None:
            return None

        lesson = self._lesson_service.get_lesson(session.lesson_id)
        chunk_id = session.current_chunk_id
        chunk = (
            self._lesson_service.get_chunk(session.lesson_id, chunk_id)
            if chunk_id is not None
            else None
        )
        if chunk is not None and lesson is not None:
            self._prepare(lesson, chunk)

        # Conversation so far *inside this chunk* — the grader needs it
        # to avoid asking the same question twice.
        history = self._chunk_history(session, chunk_id)

        session.messages.append(
            TeachingMessage(
                id=str(uuid.uuid4()),
                session_id=session.id,
                chunk_id=chunk_id,
                author=MessageAuthor.STUDENT,
                content=content,
                kind=MessageKind.EXPLANATION,
            )
        )

        attempt = session.attempts_per_chunk.get(chunk_id or "", 0) + 1
        validation = self._validate(
            chunk=chunk,
            explanation=content,
            attempt=attempt,
            lesson_title=lesson.title if lesson else "",
            history=history,
        )

        agent_reply_text = self._agent.reply_to_explanation(
            chunk=chunk, validation=validation
        )

        if chunk_id:
            session.attempts_per_chunk[chunk_id] = attempt

        self._record_evidence(session, chunk, validation)

        if validation.passed and chunk_id:
            session.chunk_states[chunk_id] = ChunkStatus.COMPLETED
            if validation.needs_review and chunk_id not in session.needs_review_chunks:
                session.needs_review_chunks.append(chunk_id)

        agent_msg = TeachingMessage(
            id=str(uuid.uuid4()),
            session_id=session.id,
            chunk_id=chunk_id,
            author=MessageAuthor.AGENT,
            content=agent_reply_text,
            kind=MessageKind.VALIDATION if validation.passed else MessageKind.GAP,
            badge=None if validation.passed else self._badge(validation),
            citations=list(validation.citations),
            meta={
                "attempt": attempt,
                "needs_review": validation.needs_review,
                "evaluator": validation.evaluator,
            },
        )
        session.messages.append(agent_msg)

        # Completing the last chunk completes the session, so the UI can
        # go straight to the result screen.
        if (
            validation.passed
            and session.current_chunk_index >= len(session.chunk_order) - 1
        ):
            session.status = SessionStatus.COMPLETED

        session.updated_at = datetime.utcnow()
        self._session_repo.save(session)
        self._write_log(session)

        return {
            "session": session.public_dump(),
            "validation": validation.public_dump(),
            "agent_message": agent_msg.model_dump(),
        }

    def advance_chunk(self, session_id: str) -> Optional[TeachingSession]:
        """Move the session to the next chunk.

        The current chunk must be COMPLETED for this to succeed; if it
        isn't, we no-op so the UI can show a hint.
        """
        session = self._session_repo.get(session_id)
        if session is None:
            return None

        current = session.current_chunk_id
        if current and session.chunk_states.get(current) != ChunkStatus.COMPLETED:
            return session

        next_index = session.current_chunk_index + 1
        if next_index >= len(session.chunk_order):
            session.status = SessionStatus.COMPLETED
            session.updated_at = datetime.utcnow()
            saved = self._session_repo.save(session)
            self._write_log(session)
            return saved

        session.current_chunk_index = next_index
        for cid in session.chunk_order:
            cs = session.chunk_states[cid]
            if cs == ChunkStatus.COMPLETED:
                continue
            if cid == session.current_chunk_id:
                session.chunk_states[cid] = ChunkStatus.CURRENT
            else:
                session.chunk_states[cid] = ChunkStatus.LOCKED

        next_chunk_id = session.current_chunk_id
        next_chunk = (
            self._lesson_service.get_chunk(session.lesson_id, next_chunk_id)
            if next_chunk_id
            else None
        )
        if next_chunk is not None:
            lesson = self._lesson_service.get_lesson(session.lesson_id)
            if lesson is not None:
                self._prepare(lesson, next_chunk)
            session.messages.append(
                TeachingMessage(
                    id=str(uuid.uuid4()),
                    session_id=session.id,
                    chunk_id=next_chunk_id,
                    author=MessageAuthor.AGENT,
                    content=self._agent.chunk_prompt(next_chunk),
                    kind=MessageKind.PROMPT,
                )
            )

        session.updated_at = datetime.utcnow()
        return self._session_repo.save(session)

    # ------------------------------------------------------------------
    # Learning result
    # ------------------------------------------------------------------

    def build_result(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Return the learning result for a session.

        Reports learning behaviour — how many explanations it took, what
        had to be clarified — rather than a score. Track D is explicit
        that this must not feel like secret grading.
        """
        session = self._session_repo.get(session_id)
        if session is None:
            return None
        lesson = self._lesson_service.get_lesson(session.lesson_id)
        titles = {c.id: c.title for c in (lesson.chunks if lesson else [])}

        return {
            "session_id": session.id,
            "lesson_id": session.lesson_id,
            "lesson_title": lesson.title if lesson else session.lesson_id,
            "status": session.status.value,
            "completed_chunks": [
                cid
                for cid, cs in session.chunk_states.items()
                if cs == ChunkStatus.COMPLETED
            ],
            "total_chunks": session.total_chunk_count,
            "teaching_loops": session.total_loops,
            "clarifications": session.clarification_count,
            "clarified_areas": session.clarified_areas,
            "needs_review": [
                titles.get(cid, cid) for cid in session.needs_review_chunks
            ],
            "per_chunk": [
                {
                    "chunk_id": cid,
                    "title": titles.get(cid, cid),
                    "loops": session.attempts_per_chunk.get(cid, 0),
                    "status": session.chunk_states.get(
                        cid, ChunkStatus.LOCKED
                    ).value,
                    "needs_review": cid in session.needs_review_chunks,
                }
                for cid in session.chunk_order
            ],
            "gap_log": session.gap_log,
        }

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _prepare(self, lesson: Any, chunk: LessonChunk) -> None:
        """Make sure ``chunk`` has key points before it is graded."""
        if self._preparer is None or chunk.key_points:
            return
        try:
            self._preparer.ensure_chunk(lesson, chunk)
        except Exception as exc:  # noqa: BLE001 - never block the loop
            logger.warning("Could not prepare chunk %s: %s", chunk.id, exc)

    def _validate(
        self,
        *,
        chunk: Optional[LessonChunk],
        explanation: str,
        attempt: int,
        lesson_title: str,
        history: List[Dict[str, str]],
    ) -> ValidationResult:
        """Call the validator, tolerating the simpler legacy signature."""
        try:
            return self._validator.validate(
                chunk=chunk,
                explanation=explanation,
                attempt=attempt,
                lesson_title=lesson_title,
                history=history,
            )
        except TypeError:
            # The scaffold's ValidatorService takes three arguments only.
            return self._validator.validate(
                chunk=chunk, explanation=explanation, attempt=attempt
            )

    @staticmethod
    def _chunk_history(
        session: TeachingSession, chunk_id: Optional[str]
    ) -> List[Dict[str, str]]:
        if chunk_id is None:
            return []
        turns = [
            {
                "role": "student" if m.author == MessageAuthor.STUDENT else "agent",
                "content": m.content,
            }
            for m in session.messages
            if m.chunk_id == chunk_id
        ]
        return turns[-_HISTORY_TURNS:]

    def _record_evidence(
        self,
        session: TeachingSession,
        chunk: Optional[LessonChunk],
        validation: ValidationResult,
    ) -> None:
        """Append one gap entry when the agent had to ask back."""
        if validation.passed and not validation.needs_review:
            return
        session.clarification_count += 1
        session.gap_log.append(
            {
                "chunk_id": chunk.id if chunk else "",
                "chunk_title": chunk.title if chunk else "",
                "attempt": validation.attempt,
                "gap_type": validation.gap_type.value,
                "label": self._gap_label(chunk, validation),
                "citations": list(validation.citations),
                "note": validation.note_for_instructor,
                "evaluator": validation.evaluator,
                "at": datetime.utcnow().isoformat(timespec="seconds"),
            }
        )

    def _gap_label(
        self, chunk: Optional[LessonChunk], validation: ValidationResult
    ) -> str:
        labeler = getattr(self._agent, "gap_label", None)
        if callable(labeler):
            return labeler(chunk, validation)
        if validation.missing_points:
            return validation.missing_points[0]
        return chunk.title if chunk else ""

    def _badge(self, validation: ValidationResult) -> str:
        badger = getattr(self._agent, "gap_badge", None)
        if callable(badger):
            return badger(validation)
        return "Cần làm rõ"

    def _write_log(self, session: TeachingSession) -> None:
        if self._session_log is None:
            return
        try:
            self._session_log.write(session, self.build_result(session.id))
        except Exception as exc:  # noqa: BLE001 - logging must never break the loop
            logger.warning("Could not write session log %s: %s", session.id, exc)
