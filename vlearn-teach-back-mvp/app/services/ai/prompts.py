"""Prompt templates for the Phase 3A.5 Documentizer.

The system prompt encodes the non-negotiable rules:

    * Output must be valid JSON matching the structured schema.
    * Every claim-bearing field must carry ``source_pages`` and
      ``citation`` grounded in the provided page text.
    * Do **not** invent knowledge — when the source lacks evidence,
      omit the field (or use ``null`` for ``common_misconception``).
    * Preserve the language of the source (no translation).
    * Slides are noisy: drop page numbers, footers, dates, and other
      layout artifacts.

Two user-prompt variants are exposed:

    * :func:`build_user_prompt_default` — first-attempt prompt.
    * :func:`build_user_prompt_grounding_strict` — re-attempt prompt
      that the retry policy uses when the previous attempt failed Gate B.
"""

from __future__ import annotations

from textwrap import dedent
from typing import List, Optional


SYSTEM_PROMPT = dedent(
    """
    You are a senior curriculum engineer. Your task is to read a set of
    LECTURER SLIDES (raw text + optional page images) and produce a
    structured representation of the lesson.

    Strict rules — every rule below is mandatory and will be enforced
    by an automatic validator:

    1. Output ONLY valid JSON matching the schema provided below. Do
       not include any commentary, code fences, or explanatory text.

    2. The input is a sequence of slides. Slides contain presentation
       noise (page numbers, footers, dates, layout artifacts). Strip
       that noise and record what you removed under
       ``removed_noise``.

    3. NEVER invent knowledge. Every claim-bearing field MUST carry:
         - ``source_pages``: a non-empty list of 1-based page numbers,
         - ``citation``: a short verbatim quote from the source text
           that supports the claim.
       If you cannot ground a claim, omit the field instead of guessing.

    4. Preserve the language of the source. Do NOT translate, even if
       the prompt is in English.

    5. Every slide should become one section. Sections must NOT split a
       single source page.

    6. Concepts are atomic knowledge units (terms, methods, principles,
       processes, entities, properties). Each concept carries its own
       ``source_pages`` and ``citation``.

    7. Teach-Back chunks are what a student will be asked to explain.
       For every chunk you MUST define:
         - ``must_understand``: a non-empty list of facts the student
           must mention,
         - ``acceptable_explanation``: a single sentence describing the
           bar the explanation must clear,
         - ``common_misconception``: a likely wrong answer — set to
           ``null`` when the source does not contain enough evidence,
         - ``clarification_trigger``: a natural-language rule for when
           the agent should ask back — required when
           ``common_misconception`` is non-null.
       NEVER invent a misconception. When in doubt, set it to null.

    8. Aim for roughly 3–12 Teach-Back chunks, but never create
       artificial chunks just to hit a number. A short lesson should
       have fewer chunks; do not pad.

    9. Confidence: emit ``confidence`` in [0, 1] for every block,
       concept, and chunk. Lower confidence means less sure about the
       grounding.

    10. Output JSON with this top-level shape:
        {
          "title": "...",
          "summary": "...",
          "language": "auto" or "en" / "vi" / ...,
          "sections": [ { "id": "...", "title": "...",
                         "page_start": N, "page_end": N,
                         "blocks": [ ... ] } ],
          "concepts": [ ... ],
          "chunks": [ { "id": "...", "title": "...",
                        "page_start": N, "page_end": N,
                        "concept_ids": [...],
                        "key_points": [ ... ],
                        "examples": [ ... ],
                        "teach_back": {
                          "must_understand": [ "..." ],
                          "acceptable_explanation": "...",
                          "common_misconception": "..." or null,
                          "clarification_trigger": "..." or null
                        },
                        "confidence": 0.0..1.0 } ]
        }

    Where a ``block`` is one of:
        heading   { id, type: "heading", text, level, source_pages, citation, confidence }
        bullet    { id, type: "bullet", text, marker, source_pages, citation, confidence }
        definition{ id, type: "definition", text, term, definition, source_pages, citation, confidence }
        example   { id, type: "example", text, caption?, source_pages, citation, confidence }
        table     { id, type: "table", text, table:{headers,rows}, source_pages, citation, confidence }
        diagram   { id, type: "diagram", text, diagram:{kind,description,nodes,edges},
                    source_pages, citation, confidence }
        relationship { id, type: "relationship", text, subject, predicate, object,
                       relationship_kind, source_pages, citation, confidence }
        note      { id, type: "note", text, source_pages, citation, confidence }

    And a ``concept`` is:
        { id, name, summary, source_pages, citation, kind,
          aliases: [ ... ], confidence }

    Valid kinds: term | method | principle | process | entity | property.
    Valid relationship_kinds: is-a | has-a | depends-on | contrasts-with |
                              causes | enables.
    Valid diagram kinds: flowchart | sequence | tree | free.
    Valid bullet markers: disc | dash | numbered | check.
    """
).strip()


def build_user_prompt_default(
    document_id: str,
    source_file: str,
    per_page_text: List[tuple[int, str]],
    options: Optional[dict] = None,
    has_page_images: bool = False,
) -> str:
    """Default user prompt — first attempt."""
    options = options or {}
    language = options.get("language", "auto")
    target_min = options.get("target_chunks_min", 3)
    target_max = options.get("target_chunks_max", 12)

    pages_repr = _format_pages_for_prompt(per_page_text)
    image_note = (
        "\n\nNOTE: Page images are also attached for pages that contain "
        "diagrams, tables, or visual explanations. Use the image as "
        "primary evidence for those elements; use the page text for the "
        "rest."
        if has_page_images
        else ""
    )

    return dedent(
        f"""
        Document id: {document_id}
        Source file: {source_file}
        Target language: {language}
        Target chunks: roughly {target_min}–{target_max} Teach-Back chunks
        {image_note}

        Slides (one section per source page):

        {pages_repr}

        Return the JSON now. Do not include any other text.
        """
    ).strip()


def build_user_prompt_grounding_strict(
    document_id: str,
    source_file: str,
    per_page_text: List[tuple[int, str]],
    options: Optional[dict] = None,
    last_failures: Optional[List[str]] = None,
    has_page_images: bool = False,
) -> str:
    """Re-attempt prompt after a grounding failure.

    ``last_failures`` carries one-line descriptions of the issues the
    validator flagged (e.g. ungrounded citation, hallucinated concept).
    """
    base = build_user_prompt_default(
        document_id=document_id,
        source_file=source_file,
        per_page_text=per_page_text,
        options=options,
        has_page_images=has_page_images,
    )
    failure_note = ""
    if last_failures:
        joined = "\n  - ".join(last_failures[:10])
        failure_note = (
            "\n\nYour previous attempt failed these grounding checks:\n  - "
            + joined
            + "\n\nRemediation:\n"
            "  * Make sure EVERY citation is a VERBATIM quote from the "
            "page text — do not paraphrase.\n"
            "  * Make sure EVERY source_pages list contains only page "
            "numbers whose text actually contains the cited quote.\n"
            "  * Do not add concepts, examples, or misconceptions that "
            "cannot be cited."
        )
    return base + failure_note


def _format_pages_for_prompt(per_page_text: List[tuple[int, str]]) -> str:
    parts: List[str] = []
    for page_num, text in per_page_text:
        parts.append(f"\n--- Page {page_num} ---\n{text or '(blank)'}")
    return "\n".join(parts)


__all__ = [
    "SYSTEM_PROMPT",
    "build_user_prompt_default",
    "build_user_prompt_grounding_strict",
]