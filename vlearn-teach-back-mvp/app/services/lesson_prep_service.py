"""LessonPrepService — derive teach-back criteria for a chunk.

A chunk arrives from the transcript parser as raw lecture text. Before
the agent can judge whether a student understood it, the chunk needs
*criteria*: the handful of points an explanation must contain, and a
one-line quality bar.

Those criteria are produced once per chunk by the chat model and cached
on disk (``data/cache/<lesson_id>.json``), because:

* they do not change unless the transcript changes;
* re-deriving them on every turn would make the loop slow and expensive;
* a cached file can be reviewed — and edited — by the instructor, which
  is the "kiểm soát của giảng viên" part of the track D rubric.

If the model is unavailable the service falls back to a heuristic that
picks the most substantive sentences. The result is weaker, but the demo
keeps working, which matters more than a perfect key-point list.
"""

from __future__ import annotations

import json
import logging
import re
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.models.lesson import Lesson, LessonChunk
from app.services.ai.chat_provider import (
    ChatMessage,
    ChatProvider,
    ChatProviderError,
)
from app.services.ai.teach_prompts import (
    ANALYZE_CHUNK_SYSTEM,
    build_analyze_chunk_prompt,
)

logger = logging.getLogger(__name__)

# Citation markers are useful to the validator but noise inside a key point.
_CITATION_RE = re.compile(r"\[T\d{2}-\d{3}\]\s*")
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")

# Only send this much of a chunk to the analyser. Chunks run to ~13k
# characters; the opening of a section carries the claim, the tail is
# usually examples and classroom back-and-forth.
_ANALYZE_CHAR_BUDGET = 6000


class ChunkCriteria:
    """Key points + quality bar for one chunk."""

    def __init__(
        self,
        key_points: List[str],
        quality_bar: str = "",
        key_concepts: Optional[List[str]] = None,
        source: str = "heuristic",
    ) -> None:
        self.key_points = key_points
        self.quality_bar = quality_bar
        self.key_concepts = key_concepts or []
        self.source = source  # "ai" | "heuristic" | "cache"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key_points": self.key_points,
            "quality_bar": self.quality_bar,
            "key_concepts": self.key_concepts,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "ChunkCriteria":
        return cls(
            key_points=[str(k) for k in payload.get("key_points", []) if str(k).strip()],
            quality_bar=str(payload.get("quality_bar", "")),
            key_concepts=[str(k) for k in payload.get("key_concepts", [])],
            source=str(payload.get("source", "cache")),
        )


class LessonPrepService:
    """Produces and caches :class:`ChunkCriteria`."""

    def __init__(
        self,
        provider: ChatProvider,
        cache_dir: Path,
        enabled: bool = True,
    ) -> None:
        self._provider = provider
        self._cache_dir = Path(cache_dir)
        self._enabled = enabled
        self._lock = threading.Lock()
        self._memory: Dict[str, ChunkCriteria] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def ensure_chunk(self, lesson: Lesson, chunk: LessonChunk) -> ChunkCriteria:
        """Return criteria for ``chunk``, deriving them if needed.

        The chunk object is updated in place so downstream code (the
        lesson page, the validator) sees the key points without having
        to know this service exists.
        """
        # A chunk that already carries key points was authored by hand
        # (data/lessons.json) or by the Documentizer. Those win over
        # anything this service would derive — an instructor's criteria
        # are the point of having criteria at all.
        if chunk.key_points:
            return ChunkCriteria(
                key_points=list(chunk.key_points),
                quality_bar=chunk.quality_bar or "",
                key_concepts=list(chunk.key_concepts),
                source="authored",
            )

        cache_key = f"{lesson.id}::{chunk.id}"

        with self._lock:
            cached = self._memory.get(cache_key)
            if cached is None:
                cached = self._load_from_disk(lesson.id, chunk.id)
            if cached is None:
                cached = self._derive(lesson, chunk)
                self._save_to_disk(lesson.id, chunk.id, cached)
            self._memory[cache_key] = cached

        chunk.key_points = list(cached.key_points)
        chunk.quality_bar = cached.quality_bar or None
        if cached.key_concepts:
            chunk.key_concepts = list(cached.key_concepts)
        return cached

    def ensure_lesson(self, lesson: Lesson) -> Lesson:
        """Derive criteria for every chunk of ``lesson``."""
        for chunk in lesson.chunks:
            self.ensure_chunk(lesson, chunk)
        return lesson

    def is_prepared(self, lesson: Lesson) -> bool:
        """Return True when every chunk already has cached criteria."""
        return all(
            f"{lesson.id}::{c.id}" in self._memory
            or self._load_from_disk(lesson.id, c.id) is not None
            for c in lesson.chunks
        )

    # ------------------------------------------------------------------
    # Derivation
    # ------------------------------------------------------------------

    def _derive(self, lesson: Lesson, chunk: LessonChunk) -> ChunkCriteria:
        if not self._enabled:
            return self._heuristic(chunk)

        source_text = _CITATION_RE.sub("", chunk.content)[:_ANALYZE_CHAR_BUDGET]
        messages = [
            ChatMessage(role="system", content=ANALYZE_CHUNK_SYSTEM),
            ChatMessage(
                role="user",
                content=build_analyze_chunk_prompt(
                    lesson_title=lesson.title,
                    chunk_title=chunk.title,
                    source_text=source_text,
                ),
            ),
        ]

        try:
            result = self._provider.complete_json(messages, temperature=0.2)
        except ChatProviderError as exc:
            logger.warning(
                "Chunk analysis failed for %s (%s) — using heuristic key points.",
                chunk.id,
                exc,
            )
            return self._heuristic(chunk)

        key_points = [
            str(kp).strip()
            for kp in (result.data.get("key_points") or [])
            if str(kp).strip()
        ]
        if not key_points:
            logger.warning(
                "Chunk analysis for %s returned no key points — using heuristic.",
                chunk.id,
            )
            return self._heuristic(chunk)

        return ChunkCriteria(
            key_points=key_points[:4],
            quality_bar=str(result.data.get("quality_bar") or "").strip(),
            key_concepts=[
                str(c).strip()
                for c in (result.data.get("key_concepts") or [])
                if str(c).strip()
            ][:6],
            source="ai",
        )

    @staticmethod
    def _heuristic(chunk: LessonChunk) -> ChunkCriteria:
        """Offline fallback: the longest opening sentences of the chunk.

        This is deliberately crude. It exists so the app never shows an
        empty criteria list, not to compete with the model.
        """
        body = _CITATION_RE.sub("", chunk.content)
        sentences = [s.strip() for s in _SENTENCE_RE.split(body) if 60 < len(s) < 300]
        picked = sentences[:3] if sentences else [chunk.title]
        return ChunkCriteria(
            key_points=picked,
            quality_bar=(
                f"Giải thích được nội dung chính của phần '{chunk.title}' "
                "bằng lời của bạn."
            ),
            source="heuristic",
        )

    # ------------------------------------------------------------------
    # Disk cache
    # ------------------------------------------------------------------

    def _cache_file(self, lesson_id: str) -> Path:
        safe = re.sub(r"[^A-Za-z0-9._-]+", "_", lesson_id)
        return self._cache_dir / f"{safe}.json"

    def _read_cache_file(self, lesson_id: str) -> Dict[str, Any]:
        path = self._cache_file(lesson_id)
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Could not read criteria cache %s: %s", path, exc)
            return {}

    def _load_from_disk(self, lesson_id: str, chunk_id: str) -> Optional[ChunkCriteria]:
        payload = self._read_cache_file(lesson_id).get(chunk_id)
        if not isinstance(payload, dict):
            return None
        criteria = ChunkCriteria.from_dict(payload)
        return criteria if criteria.key_points else None

    def _save_to_disk(
        self, lesson_id: str, chunk_id: str, criteria: ChunkCriteria
    ) -> None:
        path = self._cache_file(lesson_id)
        payload = self._read_cache_file(lesson_id)
        payload[chunk_id] = criteria.to_dict()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except OSError as exc:
            logger.warning("Could not write criteria cache %s: %s", path, exc)


__all__ = ["ChunkCriteria", "LessonPrepService"]
