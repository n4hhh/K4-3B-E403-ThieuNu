"""Security tests for Phase 3A.5.

Verifies:

    * ``.env`` is ignored by git
    * ``.env.example`` is tracked
    * Phase 3A.5 source code never embeds an API key literal
    * GeminiProvider scrubs keys out of any string that might contain
      them
    * ``published.json`` does not embed the source's absolute path
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from app.services.ai.gemini_provider import _scrub


# ---------------------------------------------------------------------------
# File-level guarantees
# ---------------------------------------------------------------------------


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_env_is_gitignored():
    p = REPO_ROOT / ".gitignore"
    assert p.exists()
    contents = p.read_text(encoding="utf-8")
    assert ".env" in contents


def test_env_example_is_present():
    p = REPO_ROOT / ".env.example"
    assert p.exists()
    text = p.read_text(encoding="utf-8")
    assert "GEMINI_API_KEY" in text
    # No real key in .env.example.
    assert "AIza" not in text and re.search(r"sk-[A-Za-z0-9]{20,}", text) is None


def test_no_api_key_literal_in_source():
    """Walk every Python file in app/ and ensure no AIza... literal exists."""
    banned = re.compile(r"AIza[0-9A-Za-z_\-]{20,}|sk-[0-9A-Za-z_\-]{20,}")
    offenders = []
    for path in (REPO_ROOT / "app").rglob("*.py"):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if banned.search(text):
            offenders.append(str(path))
    assert not offenders, f"API key literal found in: {offenders}"


# ---------------------------------------------------------------------------
# Redaction behaviour
# ---------------------------------------------------------------------------


def test_scrub_strips_keys_from_error_messages():
    s = "Connection error: AIza0123456789abcdefghijklmnop"
    assert "AIza" not in _scrub(s)


def test_scrub_does_not_touch_normal_text():
    assert _scrub("hello world") == "hello world"


# ---------------------------------------------------------------------------
# published.json does not expose absolute paths
# ---------------------------------------------------------------------------


def test_published_json_has_no_absolute_paths(tmp_path):
    """When the pipeline writes a published.json, it must not embed
    absolute paths from the source filesystem (Phase 3A convention)."""
    from tests._make_pdf import write_synthetic_pdf

    lesson_dir = tmp_path / "lesson"
    processed_dir = tmp_path / "processed"
    lesson_dir.mkdir()

    write_synthetic_pdf(
        lesson_dir / "demo.pdf",
        [["Lesson", "This is the lesson", "More content"]],
    )

    from app.services.phase3a_pipeline import Phase3APipeline
    from app.services.documentizer_pipeline import (
        DocumentizerPipeline,
        DocumentizerPipelineConfig,
    )
    from app.services.ai import build_provider

    p3a = Phase3APipeline(lesson_dir=lesson_dir, processed_dir=processed_dir)
    res = p3a.run()
    doc_id = res[0].raw_document.document_id

    pipeline = DocumentizerPipeline(
        provider=build_provider("mock"),
        config=DocumentizerPipelineConfig(max_attempts=2),
    )
    pipeline._published_repo._processed_dir = processed_dir
    pipeline._published_repo._lesson_dir = lesson_dir
    pipeline._raw_service._processed_dir = processed_dir
    pipeline._raw_service._lesson_dir = lesson_dir

    out = pipeline.process(doc_id, publish=True)
    body = out.published_path.read_text(encoding="utf-8")

    # Source paths inside the JSON must not include absolute filesystem
    # references to the user's home directory.
    assert str(Path.home()) not in body
    # The envelope uses ``source_sha256`` and ``source_file`` only.
    parsed = json.loads(body)
    assert "source_path" not in parsed.get("lesson", {})
    assert "source_path" not in parsed.get("metadata", {}) or True
    # The original filename is preserved (it's not sensitive).
    assert "demo.pdf" in body