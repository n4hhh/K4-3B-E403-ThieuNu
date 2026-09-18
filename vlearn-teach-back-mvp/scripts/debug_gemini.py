"""Capture one raw Gemini response for diagnostics.

Usage:
    python scripts/debug_gemini.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Project root
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.config import PROCESSED_DIR  # noqa: E402
from app.services.ai.gemini_provider import GeminiProvider  # noqa: E402
from app.services.ai.ai_provider import (  # noqa: E402
    DocumentizerInput,
    DocumentizerOptions,
    PageImage,
)
from app.services.ai.prompts import (  # noqa: E402
    SYSTEM_PROMPT,
    build_user_prompt_default,
)
from app.services.raw_document_service import RawDocumentService  # noqa: E402


def main() -> int:
    raw_service = RawDocumentService()
    raw = raw_service.load("day-1")
    if raw is None:
        print("ERROR: no raw.json for day-1. Run Phase 3A first.", file=sys.stderr)
        return 2

    provider = GeminiProvider()
    per_page_text = [(p.page_number, p.text or "") for p in raw.pages]
    user_prompt = build_user_prompt_default(
        document_id="day-1",
        source_file=raw.source_file,
        per_page_text=per_page_text,
        options={
            "language": "auto",
            "target_chunks_min": 3,
            "target_chunks_max": 12,
        },
        has_page_images=False,
    )

    contents = [
        provider._genai_types.Content(
            role="user",
            parts=[
                provider._genai_types.Part(text=SYSTEM_PROMPT + "\n\n" + user_prompt)
            ],
        )
    ]
    from app.services.ai.schemas import STRUCTURED_LESSON_SCHEMA

    config = provider._genai_types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=STRUCTURED_LESSON_SCHEMA,
        temperature=0.2,
        max_output_tokens=65536,
    )

    print("Calling Gemini (model=", provider.model, ")...", file=sys.stderr)
    response = provider._client.models.generate_content(
        model=provider.model,
        contents=contents,
        config=config,
    )

    raw_text = response.text or ""
    print(f"--- RAW RESPONSE (len={len(raw_text)}) ---", file=sys.stderr)
    print(raw_text, file=sys.stderr)
    print("--- END RAW RESPONSE ---", file=sys.stderr)

    # Save to file
    out_path = ROOT / "data" / "processed" / "day-1" / "_debug_raw.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(raw_text, encoding="utf-8")
    print(f"Saved to {out_path}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
