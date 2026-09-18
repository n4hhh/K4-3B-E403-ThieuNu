"""TeachingService — orchestrates a teaching session.

Responsibilities:
    * create / fetch sessions
    * track which chunk is current
    * accept student messages
    * delegate validation to `ValidatorService`
    * delegate agent reply generation to `MockAgentService`
    * advance / complete chunks and the session itself

This class deliberately holds **no I/O logic** — repositories and
sub-services handle that. Routes call into this class only.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from app.models.lesson import ChunkStatus
from app.models.message import MessageAuthor, TeachingMessage
from app.models.session import SessionStatus, TeachingSession
from app.repositories.session_repository import SessionRepository
from app.services.lesson_service import LessonService
from app.services.mock_agent_service import MockAgentService
from app.services.validator_service import ValidatorService


class TeachingService:
    """Owns the lifecycle of a `TeachingSession`."""

    def __init__(
        self,
        lesson_service: LessonService,
        session_repo: Optional[SessionRepository] = None,
        validator: Optional[ValidatorService] = None,
        agent: Optional[MockAgentService] = None,
    ) -> None:
        self._lesson_service = lesson_service
        self._session_repo = session_repo or SessionRepository()
        self._validator = validator or ValidatorService()
        self._agent = agent or MockAgentService()

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

        # Seed with an opening agent message so the UI has something to render.
        opening = self._agent.opening_message(lesson)
        session.messages.append(
            TeachingMessage(
                id=str(uuid.uuid4()),
                session_id=session.id,
                chunk_id=session.current_chunk_id,
                author=MessageAuthor.AGENT,
                content=opening,
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
        """Accept a student explanation; return agent reply + validation.

        The MVP scaffold passes through to the mock validator / agent.
        Subsequent phases will replace these with real AI.
        """
        session = self._session_repo.get(session_id)
        if session is None:
            return None

        # Record the student message
        student_msg = TeachingMessage(
            id=str(uuid.uuid4()),
            session_id=session.id,
            chunk_id=session.current_chunk_id,
            author=MessageAuthor.STUDENT,
            content=content,
        )
        session.messages.append(student_msg)

        # Validate against the current chunk
        chunk_id = session.current_chunk_id
        chunk = (
            self._lesson_service.get_chunk(session.lesson_id, chunk_id)
            if chunk_id is not None
            else None
        )
        validation = self._validator.validate(
            chunk=chunk,
            explanation=content,
            attempt=session.attempts_per_chunk.get(chunk_id, 0) + 1
            if chunk_id
            else 1,
        )

        # Build the agent reply based on the validation outcome
        agent_reply_text = self._agent.reply_to_explanation(
            chunk=chunk, validation=validation
        )

        # Track attempt count per chunk
        if chunk_id:
            session.attempts_per_chunk[chunk_id] = (
                session.attempts_per_chunk.get(chunk_id, 0) + 1
            )

        # If the chunk passed, mark it completed
        if validation.passed and chunk_id:
            session.chunk_states[chunk_id] = ChunkStatus.COMPLETED

        # Record the agent message
        agent_msg = TeachingMessage(
            id=str(uuid.uuid4()),
            session_id=session.id,
            chunk_id=chunk_id,
            author=MessageAuthor.AGENT,
            content=agent_reply_text,
        )
        session.messages.append(agent_msg)

        session.updated_at = datetime.utcnow()
        self._session_repo.save(session)

        return {
            "session": session.model_dump(),
            "validation": validation.model_dump(),
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
            # No more chunks → session complete
            session.status = SessionStatus.COMPLETED
            session.updated_at = datetime.utcnow()
            return self._session_repo.save(session)

        session.current_chunk_index = next_index
        for cid in session.chunk_order:
            cs = session.chunk_states[cid]
            if cs == ChunkStatus.COMPLETED:
                continue
            if cid == session.current_chunk_id:
                session.chunk_states[cid] = ChunkStatus.CURRENT
            else:
                session.chunk_states[cid] = ChunkStatus.LOCKED

        # Seed the next chunk with a fresh agent prompt
        next_chunk_id = session.current_chunk_id
        next_chunk = (
            self._lesson_service.get_chunk(session.lesson_id, next_chunk_id)
            if next_chunk_id
            else None
        )
        if next_chunk is not None:
            prompt = self._agent.chunk_prompt(next_chunk)
            session.messages.append(
                TeachingMessage(
                    id=str(uuid.uuid4()),
                    session_id=session.id,
                    chunk_id=next_chunk_id,
                    author=MessageAuthor.AGENT,
                    content=prompt,
                )
            )

        session.updated_at = datetime.utcnow()
        return self._session_repo.save(session)
