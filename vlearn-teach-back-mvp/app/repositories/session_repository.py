"""Session repository — in-memory store for teaching sessions.

The next phase will replace this with a real persistent store.
"""

from __future__ import annotations

import threading
from typing import Dict, Optional

from app.models.session import TeachingSession


class SessionRepository:
    """Thread-safe in-memory teaching-session store."""

    def __init__(self) -> None:
        self._sessions: Dict[str, TeachingSession] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def save(self, session: TeachingSession) -> TeachingSession:
        with self._lock:
            self._sessions[session.id] = session
        return session

    def get(self, session_id: str) -> Optional[TeachingSession]:
        with self._lock:
            return self._sessions.get(session_id)

    def list(self):
        with self._lock:
            return list(self._sessions.values())

    def clear(self) -> None:
        """Test helper — wipe all sessions."""
        with self._lock:
            self._sessions.clear()
