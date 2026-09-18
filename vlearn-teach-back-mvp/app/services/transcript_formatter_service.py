"""TranscriptFormatterService — turn plain-text transcripts into structured blocks.

Two complementary paths:

1. **Fast path (no AI call).**
   When a lesson already has a published ``StructuredLesson``, we render
   its ``sections[].blocks[]`` directly. Each typed block (heading,
   bullet, definition, example, table, …) is rendered with a dedicated
   HTML structure — much clearer to read than a wall of text.

2. **Fallback path (heuristic formatter).**
   When no published lesson is available, we run a deterministic
   regex-based heuristic over the raw ``Lesson.transcript`` to split it
   into typed blocks. This is what most lessons look like in practice:
   * An ALL-CAPS short line is treated as a heading.
   * A line starting with ``•``, ``-``, ``*``, or a number followed by
     a dot is treated as a bullet.
   * A pattern of ``Term: definition`` is treated as a definition.
   * Everything else falls through as ``note``.

3. **Optional AI-assisted path (opt-in).**
   If an AI provider is configured and the user enables "AI-enhanced
   transcript formatting", the fallback path's output can be promoted
   to higher quality by feeding the raw transcript + heuristic blocks
   to the AI provider with a focused prompt. Results are cached on disk
   keyed by lesson id + source SHA so re-renders are free.

The service returns a normalized ``FormattedTranscript`` object — a
list of plain-dict blocks suitable for Jinja2 rendering. The template
caller can iterate over ``blocks`` and pick a sub-template per type.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

from app.config import PROCESSED_DIR, PROJECT_ROOT
from app.models.clean_document import BlockType, CleanSection

if TYPE_CHECKING:  # pragma: no cover
    from app.models.lesson import Lesson
    from app.models.structured_lesson import StructuredLesson

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public data model
# ---------------------------------------------------------------------------


# A "rendered block" is a small dict the template can consume without
# needing to know about Pydantic. Templates depend on ``type`` and a
# handful of well-known keys.
@dataclass
class RenderedBlock:
    type: str
    text: str = ""
    level: int = 2
    marker: str = "disc"
    term: str = ""
    definition: str = ""
    caption: str = ""
    # Optional structured-data payloads (subset of CleanBlock extras).
    items: List[str] = field(default_factory=list)  # for "list" type
    headers: List[str] = field(default_factory=list)  # for "table"
    rows: List[List[str]] = field(default_factory=list)  # for "table"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FormattedTranscript:
    """The output of :class:`TranscriptFormatterService.format_transcript`."""

    blocks: List[RenderedBlock] = field(default_factory=list)
    source: str = "unknown"  # "structured" | "heuristic" | "ai" | "cache"
    cached: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "blocks": [b.to_dict() for b in self.blocks],
            "source": self.source,
            "cached": self.cached,
        }


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


# Cache root for AI-enhanced transcripts (separate from raw/published).
TRANSCRIPT_CACHE_DIR: Path = PROJECT_ROOT / "data" / "transcript_cache"


# Detect ALL-CAPS-ish headings: short, mostly uppercase, no terminal punctuation.
_HEADING_RE = re.compile(r"^[A-Z0-9][A-Z0-9 \-–—:_/&]{2,80}$")

# Detect "Term : definition" or "Term — definition" patterns on one line.
_DEFINITION_RE = re.compile(r"^([A-ZÀ-ỹ][\w \-–—]{1,40})\s*[:\-–—]\s+(.{3,})$")

# Bullet markers we recognize in raw transcript text.
_BULLET_PREFIX_RE = re.compile(
    r"^\s*(?:[-•·*]|[\u2022\u2023\u2043\u204C\u204D]"
    r"|\d{1,2}[.)])\s+"
)


class TranscriptFormatterService:
    """Render a lesson transcript as a structured block list."""

    def __init__(
        self,
        # Where to cache AI-enhanced transcripts.
        cache_dir: Optional[Path] = None,
        # Optional: AI provider to use for opt-in reformatting.
        # Resolved lazily to keep imports light for the common path.
        ai_provider_name: Optional[str] = None,
    ) -> None:
        self._cache_dir = Path(cache_dir) if cache_dir else TRANSCRIPT_CACHE_DIR
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._ai_provider_name = ai_provider_name

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def format_transcript(
        self,
        lesson: "Lesson",
        structured: Optional["StructuredLesson"] = None,
    ) -> FormattedTranscript:
        """Return a structured rendering of ``lesson.transcript``.

        Args:
            lesson: The Lesson instance the page is rendering.
            structured: If the underlying StructuredLesson is available
                (preferred — usually loaded from ``published.json``), pass
                it here. If not given, the service falls back to the
                heuristic formatter.

        Order of precedence:
            1. Structured lesson (sections.blocks) — if provided.
            2. Cache file (if it exists for this lesson).
            3. Heuristic formatter over ``lesson.transcript``.
        """
        # 1) Fast path: structured
        if structured is not None and structured.sections:
            blocks = [
                _block_from_clean_block(b)
                for sec in structured.sections
                for b in sec.blocks
            ]
            if blocks:
                return FormattedTranscript(
                    blocks=blocks,
                    source="structured",
                    cached=False,
                )

        # 2) Cache fallback
        cached = self._load_cache(lesson)
        if cached is not None:
            return FormattedTranscript(
                blocks=[RenderedBlock(**b) for b in cached["blocks"]],
                source="cache",
                cached=True,
            )

        # 3) Heuristic formatter on raw transcript
        raw = (lesson.transcript or "").strip()
        if not raw:
            # Last resort: collapse description into one note so the
            # page still has something meaningful.
            raw = (lesson.description or "").strip()

        blocks = _heuristic_format(raw) if raw else []
        return FormattedTranscript(
            blocks=blocks,
            source="heuristic",
            cached=False,
        )

    # ------------------------------------------------------------------
    # Optional AI-enhanced path
    # ------------------------------------------------------------------

    def format_with_ai(self, lesson: "Lesson") -> FormattedTranscript:
        """Run the AI over the raw transcript and cache the result.

        Returns the heuristic result unchanged if the AI provider is
        not configured or the call fails (fail-safe).

        Caching:
            - First, looks up a cached payload keyed by SHA-256 of the
              raw transcript + lesson id (file name =
              ``{cache_key}.json``).
            - On miss, calls the configured AI provider with a focused
              "reformat transcript" prompt and persists the response.
        """
        heuristic = self.format_transcript(lesson)
        # Reject if we already have good structure from a published lesson.
        if heuristic.source in ("structured",):
            return heuristic

        raw = (lesson.transcript or "").strip()
        if not raw:
            return heuristic

        # Cache-key: include a SHA of the raw transcript so a re-process
        # of the same content hits the cache instead of re-calling the AI.
        cache_key = hashlib.sha256(
            f"{lesson.id}:{raw}".encode("utf-8")
        ).hexdigest()[:16]
        cache_path = self._cache_dir / f"{cache_key}.json"

        if cache_path.exists():
            try:
                with cache_path.open("r", encoding="utf-8") as fh:
                    payload = json.load(fh)
                return FormattedTranscript(
                    blocks=[RenderedBlock(**b) for b in payload["blocks"]],
                    source=payload.get("source", "cache"),
                    cached=True,
                )
            except (OSError, json.JSONDecodeError) as exc:
                logger.warning(
                    "Failed to read transcript cache %s: %s — regenerating",
                    cache_path,
                    exc,
                )

        # Decide whether the heuristic output is already "good enough".
        # If yes, persist it under the cache key so future re-renders are
        # instant. If no, fall through to (future) AI-assisted pass.
        blocks = heuristic.blocks
        source = heuristic.source

        heuristic_good = _heuristic_is_good_enough(blocks)
        if heuristic_good:
            try:
                with cache_path.open("w", encoding="utf-8") as fh:
                    json.dump(
                        {
                            "blocks": [b.to_dict() for b in blocks],
                            "source": source,
                            "lesson_id": lesson.id,
                            "key": cache_key,
                        },
                        fh,
                        indent=2,
                        ensure_ascii=False,
                    )
                logger.info(
                    "Cached heuristic transcript for lesson=%s → %s",
                    lesson.id,
                    cache_path,
                )
            except OSError as exc:
                logger.warning("Failed to cache transcript: %s", exc)

            return FormattedTranscript(
                blocks=blocks,
                source=source,
                cached=False,
            )

        # Heuristic is not ideal — try an AI pass if a provider is
        # configured. Falls back gracefully on any error.
        ai_blocks = _try_ai_reformat(raw, self._ai_provider_name)
        if ai_blocks:
            blocks = ai_blocks
            source = "ai"
            logger.info(
                "AI reformat succeeded for lesson=%s (%d blocks)",
                lesson.id,
                len(blocks),
            )
        else:
            logger.info(
                "AI reformat unavailable for lesson=%s — keeping heuristic",
                lesson.id,
            )

        try:
            with cache_path.open("w", encoding="utf-8") as fh:
                json.dump(
                    {
                        "blocks": [b.to_dict() for b in blocks],
                        "source": source,
                        "lesson_id": lesson.id,
                        "key": cache_key,
                    },
                    fh,
                    indent=2,
                    ensure_ascii=False,
                )
        except OSError as exc:
            logger.warning("Failed to cache transcript: %s", exc)

        return FormattedTranscript(
            blocks=blocks,
            source=source,
            cached=False,
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _load_cache(
        self, lesson: "Lesson"
    ) -> Optional[Dict[str, Any]]:
        """Return the cached payload for ``lesson.id`` if present."""
        # Two cache paths:
        # 1. Dedicated cache under TRANSCRIPT_CACHE_DIR/{lesson_id}.json
        # 2. The cached AI-output above is keyed by content hash; we
        #    intentionally do NOT match by lesson_id alone because the
        #    underlying transcript can change between lessons.
        direct = self._cache_dir / f"{lesson.id}.json"
        if direct.exists():
            try:
                with direct.open("r", encoding="utf-8") as fh:
                    payload = json.load(fh)
                return payload
            except (OSError, json.JSONDecodeError) as exc:
                logger.warning(
                    "Failed to read transcript cache %s: %s",
                    direct,
                    exc,
                )
        return None


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _block_from_clean_block(blk) -> RenderedBlock:  # type: ignore[no-untyped-def]
    """Map a ``CleanBlock`` to a :class:`RenderedBlock`."""
    marker = (
        blk.marker.value
        if hasattr(blk.marker, "value")
        else (blk.marker or "disc")
    )
    extras: Dict[str, Any] = {}
    if blk.type == BlockType.TABLE and blk.table is not None:
        extras["headers"] = list(blk.table.headers or [])
        extras["rows"] = [list(r) for r in (blk.table.rows or [])]
    return RenderedBlock(
        type=blk.type.value,
        text=blk.text or "",
        level=blk.level or 2,
        marker=marker,
        term=blk.term or "",
        definition=blk.definition or "",
        caption=blk.caption or "",
        **extras,
    )


def _heuristic_format(raw: str) -> List[RenderedBlock]:
    """Best-effort regex-based transcript formatter.

    Strategy:
        * Split on blank lines into "paragraphs".
        * For each paragraph, iterate over its lines.
        * Short ALL-CAPS line → heading (level 1 for top-level, level 2
          if it follows another heading).
        * ``Term: definition`` line → definition.
        * ``- foo`` / ``• foo`` / ``1. foo`` lines → bullets (kept
          grouped under the parent heading when possible).
        * Anything else → note.
    """
    if not raw.strip():
        return []

    blocks: List[RenderedBlock] = []
    current_heading_level = 2
    in_list = False
    last_heading_was_top = False

    paragraphs = re.split(r"\n\s*\n", raw)
    for paragraph in paragraphs:
        lines = [ln for ln in paragraph.splitlines() if ln.strip()]
        if not lines:
            continue

        first = lines[0].strip()
        # Heading heuristic: short & all uppercase & no bullet
        if (
            len(first) <= 80
            and _HEADING_RE.match(first)
            and not _BULLET_PREFIX_RE.match(first)
        ):
            level = 1 if last_heading_was_top is False else 2
            blocks.append(
                RenderedBlock(type="heading", text=first, level=level)
            )
            current_heading_level = level
            last_heading_was_top = (level == 1)
            in_list = False
            # Remaining lines of the paragraph become bullets.
            bullet_lines = lines[1:]
            if bullet_lines:
                for bl in bullet_lines:
                    marker, text = _strip_bullet(bl)
                    if text:
                        blocks.append(
                            RenderedBlock(
                                type="bullet",
                                text=text,
                                marker=marker,
                                level=current_heading_level + 1,
                            )
                        )
                in_list = True
            continue

        # Definition heuristic on the first line of the paragraph.
        m = _DEFINITION_RE.match(first)
        if m and len(first) <= 200:
            blocks.append(
                RenderedBlock(
                    type="definition",
                    term=m.group(1).strip(),
                    definition=m.group(2).strip(),
                    text=f"{m.group(1).strip()}: {m.group(2).strip()}",
                )
            )
            in_list = False
            # Remaining lines → bullets.
            for bl in lines[1:]:
                marker, text = _strip_bullet(bl)
                if text:
                    blocks.append(
                        RenderedBlock(
                            type="bullet",
                            text=text,
                            marker=marker,
                        )
                    )
            continue

        # Otherwise treat the paragraph as bullet list (or note).
        all_bullets = all(
            _BULLET_PREFIX_RE.match(ln) or _DEFINITION_RE.match(ln.strip())
            for ln in lines
        )
        if all_bullets and lines:
            for ln in lines:
                # Definition inside the list
                m2 = _DEFINITION_RE.match(ln.strip())
                if m2:
                    blocks.append(
                        RenderedBlock(
                            type="definition",
                            term=m2.group(1).strip(),
                            definition=m2.group(2).strip(),
                            text=ln.strip(),
                        )
                    )
                    continue
                marker, text = _strip_bullet(ln)
                if text:
                    blocks.append(
                        RenderedBlock(
                            type="bullet",
                            text=text,
                            marker=marker,
                        )
                    )
                    in_list = True
            continue

        # Fallback: full paragraph as a note.
        text = " ".join(lines).strip()
        blocks.append(RenderedBlock(type="note", text=text))
        in_list = False
        last_heading_was_top = False

    return blocks


def _strip_bullet(line: str) -> Tuple[str, str]:
    """Strip a leading bullet marker from ``line``.

    Returns ``(marker, text)`` where ``marker`` is one of
    ``dash / disc / numbered / check``.
    """
    s = line.lstrip()
    # Numbered: "1." or "1)"
    m = re.match(r"^(\d{1,2})[.)]\s+(.*)$", s)
    if m:
        return "numbered", m.group(2).strip()
    # Dash / asterisk bullet
    if s.startswith(("-", "*")):
        return "dash", s[1:].strip()
    # Unicode bullets
    if s[:1] in ("•", "·", "‣", "⁃"):
        return "disc", s[1:].strip()
    # Default: treat the line as a "disc" bullet (kept verbatim).
    return "disc", s


def _heuristic_is_good_enough(blocks: List[RenderedBlock]) -> bool:
    """Decide whether the heuristic output is already structured well.

    A naive transcript that came straight from a PDF often becomes a
    long wall of ``note`` blocks, one per raw paragraph, with no
    headings, no bullets, and no definitions. That kind of output is
    *not* "good enough" — a reformat (ideally AI-assisted) would help.

    Heuristic:
        * At least 3 blocks total.
        * At least one heading OR
          the proportion of structured blocks (heading, bullet,
          definition, example, table) is ≥ 30% of all blocks.
    """
    if len(blocks) < 3:
        return False
    structured_count = sum(
        1
        for b in blocks
        if b.type in ("heading", "bullet", "definition", "example", "table")
    )
    if any(b.type == "heading" for b in blocks):
        return True
    return structured_count / max(1, len(blocks)) >= 0.3


# ---------------------------------------------------------------------------
# Optional AI-assisted reformat
# ---------------------------------------------------------------------------


def _try_ai_reformat(
    raw: str,
    provider_name: Optional[str],
) -> Optional[List[RenderedBlock]]:
    """Call the AI provider to reformat a raw transcript.

    Returns ``None`` on any failure so the caller can fall back to the
    heuristic output. The provider is constructed via
    :func:`build_provider` so it picks up ``AI_PROVIDER`` /
    ``GEMINI_API_KEY`` automatically.
    """
    if not raw.strip() or not _ai_sdk_available():
        return None
    try:
        from app.services.ai.provider_factory import build_provider  # lazy
        from app.services.ai.ai_provider import (
            AIProviderError,
            DocumentizerInput,
            DocumentizerOptions,
            PageImage,
        )
    except ImportError:  # pragma: no cover
        logger.warning("AI provider unavailable — skipping AI reformat.")
        return None

    try:
        provider = build_provider(provider_name)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not build AI provider: %s", exc)
        return None

    # We use Gemini's free-form text completion, not the full
    # STRUCTURED_LESSON_SCHEMA — too heavy for a transcript reformat.
    # Instead we craft a focused prompt and parse JSON from the response.
    system = (
        "You are a meticulous technical editor. Reformat a raw slide-deck "
        "transcript into a clean JSON array of blocks. Preserve every fact, "
        "do not invent content, and do not translate. Output JSON only."
    )
    user = (
        "Reformat the transcript below as a JSON array under "
        "`blocks`. Each block has a `type` ∈ "
        "{heading, bullet, definition, example, table, note}. "
        "Use:\n"
        "- `heading` (with `level` 1..3) for section titles, ALL-CAPS labels, "
        "or numbered section names like \"Agenda | Day 01\".\n"
        "- `bullet` (with `marker` ∈ {disc, dash, numbered, check}) "
        "for each separately-listed item; keep the bullet prefix or list "
        "numbering (e.g. `1.`, `-`, `•`).\n"
        "- `definition` (`term`, `definition`) for `Term: explanation` "
        "patterns.\n"
        "- `example` for illustrative snippets, including code samples; "
        "include `caption` if useful.\n"
        "- `table` (`headers` array + `rows` array of arrays) when a slide "
        "shows tabular data.\n"
        "- `note` for plain prose paragraphs that don't fit the above.\n"
        "Always include `text`; populate the per-type fields too. "
        "Output strictly the JSON object "
        "`{\"blocks\": [...]}`. Do not include any commentary or "
        "code fences.\n\n"
        "Raw transcript:\n"
        "```\n"
        f"{raw[:24000]}\n"  # 24k char safety cap; Gemini flash handles this.
        "```"
    )

    try:
        client = getattr(provider, "_client", None)
        genai_types = getattr(provider, "_genai_types", None)
        if client is None or genai_types is None:
            # Provider doesn't expose client/types — skip AI.
            return None
        cfg = genai_types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.2,
            max_output_tokens=8192,
        )
        response = client.models.generate_content(
            model=provider.model,
            contents=[
                genai_types.Content(
                    role="user",
                    parts=[genai_types.Part(text=system + "\n\n" + user)],
                )
            ],
            config=cfg,
        )
    except AIProviderError as exc:
        logger.warning("AI reformat failed: %s — falling back to heuristic.", exc)
        return None
    except Exception as exc:  # noqa: BLE001
        logger.warning("AI reformat unexpected error: %s", exc)
        return None

    raw_text = getattr(response, "text", None) or ""
    if not raw_text:
        return None

    payload: Any
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError:
        # Try stripping a code fence.
        stripped = re.sub(r"^```[a-zA-Z0-9]*\s*", "", raw_text.strip())
        stripped = re.sub(r"\s*```$", "", stripped)
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError:
            logger.warning("AI returned unparseable JSON. Falling back.")
            return None

    blocks_payload = payload.get("blocks") if isinstance(payload, dict) else None
    if not isinstance(blocks_payload, list):
        return None

    out: List[RenderedBlock] = []
    for item in blocks_payload:
        if not isinstance(item, dict):
            continue
        btype = str(item.get("type") or "note").lower()
        if btype not in ("heading", "bullet", "definition", "example", "table", "note"):
            btype = "note"
        try:
            out.append(
                RenderedBlock(
                    type=btype,
                    text=str(item.get("text") or ""),
                    level=int(item.get("level") or 2) if btype == "heading" else 2,
                    marker=str(item.get("marker") or "disc") if btype == "bullet" else "disc",
                    term=str(item.get("term") or ""),
                    definition=str(item.get("definition") or ""),
                    caption=str(item.get("caption") or ""),
                    headers=[str(h) for h in (item.get("headers") or [])]
                    if btype == "table"
                    else [],
                    rows=[
                        [str(c) for c in row]
                        for row in (item.get("rows") or [])
                    ]
                    if btype == "table"
                    else [],
                )
            )
        except Exception:  # noqa: BLE001
            # Skip one bad block — never break the whole render.
            continue

    return out or None


def _ai_sdk_available() -> bool:
    """Return ``True`` if the google-genai SDK can be imported."""
    try:
        import google.genai  # noqa: F401

        return True
    except ImportError:
        return False


__all__ = [
    "FormattedTranscript",
    "RenderedBlock",
    "TranscriptFormatterService",
    "TRANSCRIPT_CACHE_DIR",
]
