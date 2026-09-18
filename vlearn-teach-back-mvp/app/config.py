"""Application configuration.

All environment-dependent paths and settings live here.

Environment variables are loaded from .env file in the project root.
We use simple dataclass-style settings with python-dotenv for .env support.

Environment variables
---------------------
GEMINI_API_KEY
    API key for Gemini (reserved for Phase 3A.5).
    Default: empty (no Gemini calls in Phase 3A).

GEMINI_MODEL
    Gemini model to use (reserved for Phase 3A.5).
    Default: gemini-2.0-flash.

AI_PROVIDER
    AI provider to use (reserved for Phase 3A.5).
    Default: gemini.

VLEARN_LESSON_DIR
    Directory containing the source PDF lessons.
    Default: ``../data/lesson`` (relative to the project root).
    The path is resolved to an absolute path on import.

IMPORTANT:
    Phase 3A MUST NOT call Gemini or any LLM.
    These variables are prepared for Phase 3A.5.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

# Try to load from .env file (optional, graceful if not available)
try:
    from dotenv import load_dotenv
    # Look for .env in the project root
    _env_path = Path(__file__).resolve().parent.parent / ".env"
    if _env_path.exists():
        load_dotenv(_env_path)
        print(f"[config] Loaded environment from {_env_path}", file=sys.stderr)
    else:
        print(f"[config] No .env file at {_env_path}, using system environment", file=sys.stderr)
except ImportError:
    print("[config] python-dotenv not installed, using system environment only", file=sys.stderr)


# Project root = the directory containing the ``app`` package.
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent

# Processed data directory (where raw.json is stored)
PROCESSED_DIR: Path = PROJECT_ROOT / "data" / "processed"


def _resolve_lesson_dir() -> Path:
    """Return the configured lesson directory, resolved to an absolute path.

    Priority:
        1. ``VLEARN_LESSON_DIR`` environment variable, if set.
        2. ``../data/lesson`` relative to the project root.

    The result is always an absolute path so the app behaves identically on
    Windows and POSIX systems.
    """
    raw = os.environ.get("VLEARN_LESSON_DIR")
    if raw:
        candidate = Path(raw).expanduser()
        if not candidate.is_absolute():
            candidate = (PROJECT_ROOT / candidate).resolve()
        return candidate
    return (PROJECT_ROOT / ".." / "data" / "lesson").resolve()


LESSON_DIR: Path = _resolve_lesson_dir()
JSON_FALLBACK_FILE: Path = PROJECT_ROOT / "data" / "lessons.json"

# AI Configuration (reserved for Phase 3A.5)
GEMINI_API_KEY: Optional[str] = os.environ.get("GEMINI_API_KEY") or None
GEMINI_MODEL: str = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
AI_PROVIDER: str = os.environ.get("AI_PROVIDER", "gemini")


# ---------------------------------------------------------------------------
# Teach-Back (D3) runtime settings
# ---------------------------------------------------------------------------
#
# The teach-back loop talks to a *chat* model, which is a different concern
# from the Documentizer's ``AI_PROVIDER`` (PDF -> StructuredLesson). It has
# its own variables so the two can be pointed at different models.
#
#   TEACH_BACK_PROVIDER   "openai-compatible" (DeepSeek, …) | "gemini" | "mock"
#   TEACH_BACK_BASE_URL   API root for the OpenAI-compatible endpoint
#   TEACH_BACK_MODEL      model name (e.g. deepseek-flash)
#   TEACH_BACK_API_KEY    API key; never logged, never committed

TEACH_BACK_PROVIDER: str = os.environ.get("TEACH_BACK_PROVIDER", "mock").strip().lower()
TEACH_BACK_BASE_URL: str = os.environ.get(
    "TEACH_BACK_BASE_URL", "https://api.deepseek.com"
).strip()
TEACH_BACK_MODEL: str = os.environ.get("TEACH_BACK_MODEL", "deepseek-flash").strip()
TEACH_BACK_API_KEY: Optional[str] = os.environ.get("TEACH_BACK_API_KEY") or None
TEACH_BACK_TIMEOUT: int = int(os.environ.get("TEACH_BACK_TIMEOUT", "90"))
TEACH_BACK_MAX_TOKENS: int = int(os.environ.get("TEACH_BACK_MAX_TOKENS", "5000"))

# How many chunks a single teach-back session covers. Lecture transcripts
# hold 11-21 sections; a session that long is unusable, so we keep the most
# substantial ones and preserve their original order.
TEACH_BACK_MAX_CHUNKS: int = int(os.environ.get("TEACH_BACK_MAX_CHUNKS", "5"))

# After this many failed attempts on one chunk the agent stops asking back
# and lets the student move on with the chunk flagged "needs review". The
# point is practice, not gatekeeping (track D safety note).
TEACH_BACK_MAX_ATTEMPTS: int = int(os.environ.get("TEACH_BACK_MAX_ATTEMPTS", "4"))

# Directory holding the VLearn data pack (transcripts + slides). Read-only:
# the app never writes into it and never copies it into the repo.
def _resolve_pack_dir() -> Path:
    raw = os.environ.get("VLEARN_PACK_DIR")
    if raw:
        candidate = Path(raw).expanduser()
        if not candidate.is_absolute():
            candidate = (PROJECT_ROOT / candidate).resolve()
        return candidate
    return (PROJECT_ROOT / ".." / "data" / "vlearn-pack").resolve()


PACK_DIR: Path = _resolve_pack_dir()
TRANSCRIPT_DIR: Path = PACK_DIR / "transcript"
SLIDE_DIR: Path = PACK_DIR / "slides"

# Cache for LLM-derived lesson metadata (key points, quiz, session logs).
CACHE_DIR: Path = PROJECT_ROOT / "data" / "cache"
SESSION_LOG_DIR: Path = PROJECT_ROOT / "data" / "session-logs"


class Settings:
    """Top-level settings object exposed to the rest of the app."""

    lesson_dir: Path = LESSON_DIR
    json_fallback_file: Path = JSON_FALLBACK_FILE
    project_root: Path = PROJECT_ROOT
    processed_dir: Path = PROCESSED_DIR

    # AI settings (reserved for Phase 3A.5)
    gemini_api_key: Optional[str] = GEMINI_API_KEY
    gemini_model: str = GEMINI_MODEL
    ai_provider: str = AI_PROVIDER

    # Teach-Back (D3)
    teach_back_provider: str = TEACH_BACK_PROVIDER
    teach_back_base_url: str = TEACH_BACK_BASE_URL
    teach_back_model: str = TEACH_BACK_MODEL
    teach_back_api_key: Optional[str] = TEACH_BACK_API_KEY
    teach_back_timeout: int = TEACH_BACK_TIMEOUT
    teach_back_max_tokens: int = TEACH_BACK_MAX_TOKENS
    teach_back_max_chunks: int = TEACH_BACK_MAX_CHUNKS
    teach_back_max_attempts: int = TEACH_BACK_MAX_ATTEMPTS

    pack_dir: Path = PACK_DIR
    transcript_dir: Path = TRANSCRIPT_DIR
    slide_dir: Path = SLIDE_DIR
    cache_dir: Path = CACHE_DIR
    session_log_dir: Path = SESSION_LOG_DIR


settings = Settings()


# Ensure writable directories exist
for _d in (PROCESSED_DIR, CACHE_DIR, SESSION_LOG_DIR):
    _d.mkdir(parents=True, exist_ok=True)


__all__ = [
    "settings",
    "Settings",
    "LESSON_DIR",
    "JSON_FALLBACK_FILE",
    "PROJECT_ROOT",
    "PROCESSED_DIR",
    "GEMINI_API_KEY",
    "GEMINI_MODEL",
    "AI_PROVIDER",
    "TEACH_BACK_PROVIDER",
    "TEACH_BACK_BASE_URL",
    "TEACH_BACK_MODEL",
    "TEACH_BACK_API_KEY",
    "TEACH_BACK_MAX_CHUNKS",
    "TEACH_BACK_MAX_ATTEMPTS",
    "PACK_DIR",
    "TRANSCRIPT_DIR",
    "SLIDE_DIR",
    "CACHE_DIR",
    "SESSION_LOG_DIR",
]
