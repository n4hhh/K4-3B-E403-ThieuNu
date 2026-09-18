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


settings = Settings()


# Ensure processed directory exists
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


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
]
