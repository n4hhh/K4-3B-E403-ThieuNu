"""SessionLogService — persists a teaching session for the instructor.

Track D asks for teacher control and visibility: an instructor should be
able to see what students got stuck on, without the class seeing any
individual's mistakes. This writes one JSON file per session under
``data/session-logs/``.

What goes in:
    * the lesson and chunk structure of the attempt
    * how many explanations each chunk took
    * every gap the agent found, with its source citations
    * the full conversation

What stays out:
    * anything identifying the student beyond the session id — the MVP
      has no accounts, and the log must not become one.

Writes are best-effort. A failed log write is logged and swallowed: a
disk problem must never break a student's session.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.models.session import TeachingSession

logger = logging.getLogger(__name__)

_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


class SessionLogService:
    """Writes and reads teaching-session logs."""

    def __init__(self, log_dir: Path) -> None:
        self._dir = Path(log_dir)

    # ------------------------------------------------------------------

    def _path(self, session_id: str) -> Path:
        return self._dir / f"{_SAFE_NAME_RE.sub('_', session_id)}.json"

    def write(
        self, session: TeachingSession, result: Optional[Dict[str, Any]] = None
    ) -> Optional[Path]:
        """Persist ``session``; return the file path, or None on failure."""
        payload = {
            "session_id": session.id,
            "lesson_id": session.lesson_id,
            "status": session.status.value,
            "created_at": session.created_at.isoformat(timespec="seconds"),
            "updated_at": session.updated_at.isoformat(timespec="seconds"),
            "written_at": datetime.utcnow().isoformat(timespec="seconds"),
            "result": result or {},
            "gaps": session.gap_log,
            "transcript": [
                {
                    "author": m.author.value,
                    "kind": m.kind.value,
                    "chunk_id": m.chunk_id,
                    "content": m.content,
                    "citations": m.citations,
                    "at": m.created_at.isoformat(timespec="seconds"),
                }
                for m in session.messages
            ],
        }

        try:
            self._dir.mkdir(parents=True, exist_ok=True)
            path = self._path(session.id)
            path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            return path
        except OSError as exc:
            logger.warning("Could not write session log for %s: %s", session.id, exc)
            return None

    def read(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Return a stored log, or None when it does not exist."""
        path = self._path(session_id)
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Could not read session log %s: %s", path, exc)
            return None

    def list_recent(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Return summaries of the most recently updated sessions."""
        if not self._dir.is_dir():
            return []

        files = sorted(
            self._dir.glob("*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )[:limit]

        summaries: List[Dict[str, Any]] = []
        for path in files:
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            result = payload.get("result") or {}
            summaries.append(
                {
                    "session_id": payload.get("session_id", path.stem),
                    "lesson_id": payload.get("lesson_id", ""),
                    "lesson_title": result.get("lesson_title", ""),
                    "status": payload.get("status", ""),
                    "updated_at": payload.get("updated_at", ""),
                    "completed": len(result.get("completed_chunks", [])),
                    "total": result.get("total_chunks", 0),
                    "loops": result.get("teaching_loops", 0),
                    "clarifications": result.get("clarifications", 0),
                    "clarified_areas": result.get("clarified_areas", []),
                    "needs_review": result.get("needs_review", []),
                }
            )
        return summaries


__all__ = ["SessionLogService"]
