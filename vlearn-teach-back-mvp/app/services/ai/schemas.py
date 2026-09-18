"""JSON Schema fragments for the AI provider.

These schemas are exported so the Gemini call can request
``response_schema = structured_lesson_schema`` — Gemini's structured
output mode (used by ``response_schema`` in
``GenerateContentConfig``).

The schema intentionally mirrors the Pydantic models in
``app.models.clean_document`` and ``app.models.teach_back_chunk`` so
that any well-formed response is also a well-formed CleanDocument.

NOTE: this schema is for the **first-phase** AI output
(``CleanDocument``-shaped). The structured-lesson shape adds metadata
(``source_sha256``, ``generated_by``) which is appended by the
Documentizer pipeline, not by Gemini.
"""

from __future__ import annotations

from typing import Any, Dict


# A block is a discriminated union by ``type``.
_BLOCK_SCHEMAS: Dict[str, Any] = {
    "heading": {
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "type": {"type": "string", "enum": ["heading"]},
            "text": {"type": "string"},
            "level": {"type": "integer", "minimum": 1, "maximum": 6},
            "source_pages": {
                "type": "array",
                "items": {"type": "integer", "minimum": 1},
                "minItems": 1,
            },
            "citation": {"type": "string", "minLength": 1},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        },
        "required": ["id", "type", "text", "source_pages", "citation", "confidence"],
    },
    "bullet": {
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "type": {"type": "string", "enum": ["bullet"]},
            "text": {"type": "string"},
            "marker": {
                "type": "string",
                "enum": ["disc", "dash", "numbered", "check"],
            },
            "source_pages": {
                "type": "array",
                "items": {"type": "integer", "minimum": 1},
                "minItems": 1,
            },
            "citation": {"type": "string", "minLength": 1},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        },
        "required": ["id", "type", "text", "source_pages", "citation", "confidence"],
    },
    "definition": {
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "type": {"type": "string", "enum": ["definition"]},
            "text": {"type": "string"},
            "term": {"type": "string"},
            "definition": {"type": "string"},
            "source_pages": {
                "type": "array",
                "items": {"type": "integer", "minimum": 1},
                "minItems": 1,
            },
            "citation": {"type": "string", "minLength": 1},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        },
        "required": [
            "id",
            "type",
            "text",
            "term",
            "definition",
            "source_pages",
            "citation",
            "confidence",
        ],
    },
    "example": {
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "type": {"type": "string", "enum": ["example"]},
            "text": {"type": "string"},
            "caption": {"type": "string"},
            "source_pages": {
                "type": "array",
                "items": {"type": "integer", "minimum": 1},
                "minItems": 1,
            },
            "citation": {"type": "string", "minLength": 1},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        },
        "required": ["id", "type", "text", "source_pages", "citation", "confidence"],
    },
    "table": {
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "type": {"type": "string", "enum": ["table"]},
            "text": {"type": "string"},
            "table": {
                "type": "object",
                "properties": {
                    "headers": {"type": "array", "items": {"type": "string"}},
                    "rows": {
                        "type": "array",
                        "items": {"type": "array", "items": {"type": "string"}},
                    },
                },
                "required": ["headers", "rows"],
            },
            "source_pages": {
                "type": "array",
                "items": {"type": "integer", "minimum": 1},
                "minItems": 1,
            },
            "citation": {"type": "string", "minLength": 1},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        },
        "required": [
            "id",
            "type",
            "text",
            "table",
            "source_pages",
            "citation",
            "confidence",
        ],
    },
    "diagram": {
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "type": {"type": "string", "enum": ["diagram"]},
            "text": {"type": "string"},
            "diagram": {
                "type": "object",
                "properties": {
                    "kind": {
                        "type": "string",
                        "enum": ["flowchart", "sequence", "tree", "free"],
                    },
                    "description": {"type": "string"},
                    "nodes": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "label": {"type": "string"},
                            },
                            "required": ["id", "label"],
                        },
                    },
                    "edges": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "from": {"type": "string"},
                                "to": {"type": "string"},
                                "label": {"type": "string"},
                            },
                            "required": ["from", "to"],
                        },
                    },
                },
                "required": ["kind", "description"],
            },
            "source_pages": {
                "type": "array",
                "items": {"type": "integer", "minimum": 1},
                "minItems": 1,
            },
            "citation": {"type": "string", "minLength": 1},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        },
        "required": [
            "id",
            "type",
            "text",
            "diagram",
            "source_pages",
            "citation",
            "confidence",
        ],
    },
    "relationship": {
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "type": {"type": "string", "enum": ["relationship"]},
            "text": {"type": "string"},
            "subject": {"type": "string"},
            "predicate": {"type": "string"},
            "object": {"type": "string"},
            "relationship_kind": {
                "type": "string",
                "enum": [
                    "is-a",
                    "has-a",
                    "depends-on",
                    "contrasts-with",
                    "causes",
                    "enables",
                ],
            },
            "source_pages": {
                "type": "array",
                "items": {"type": "integer", "minimum": 1},
                "minItems": 1,
            },
            "citation": {"type": "string", "minLength": 1},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        },
        "required": [
            "id",
            "type",
            "text",
            "subject",
            "predicate",
            "object",
            "relationship_kind",
            "source_pages",
            "citation",
            "confidence",
        ],
    },
    "note": {
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "type": {"type": "string", "enum": ["note"]},
            "text": {"type": "string"},
            "source_pages": {
                "type": "array",
                "items": {"type": "integer", "minimum": 1},
                "minItems": 1,
            },
            "citation": {"type": "string"},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        },
        "required": ["id", "type", "text", "source_pages", "confidence"],
    },
}


STRUCTURED_LESSON_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "title": {"type": "string", "minLength": 1},
        "summary": {"type": "string"},
        "language": {"type": "string"},
        "sections": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "title": {"type": "string", "minLength": 1},
                    "page_start": {"type": "integer", "minimum": 1},
                    "page_end": {"type": "integer", "minimum": 1},
                    "blocks": {
                        "type": "array",
                        "items": {"anyOf": list(_BLOCK_SCHEMAS.values())},
                    },
                },
                "required": ["id", "title", "page_start", "page_end", "blocks"],
            },
        },
        "concepts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "name": {"type": "string", "minLength": 1},
                    "summary": {"type": "string"},
                    "source_pages": {
                        "type": "array",
                        "items": {"type": "integer", "minimum": 1},
                        "minItems": 1,
                    },
                    "citation": {"type": "string", "minLength": 1},
                    "kind": {
                        "type": "string",
                        "enum": [
                            "term",
                            "method",
                            "principle",
                            "process",
                            "entity",
                            "property",
                        ],
                    },
                    "aliases": {"type": "array", "items": {"type": "string"}},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                },
                "required": [
                    "id",
                    "name",
                    "source_pages",
                    "citation",
                    "kind",
                    "confidence",
                ],
            },
        },
        "chunks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "title": {"type": "string", "minLength": 1},
                    "summary": {"type": "string"},
                    "page_start": {"type": "integer", "minimum": 1},
                    "page_end": {"type": "integer", "minimum": 1},
                    "concept_ids": {"type": "array", "items": {"type": "string"}},
                    "key_points": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "text": {"type": "string", "minLength": 1},
                                "concept_id": {"type": "string"},
                                "source_pages": {
                                    "type": "array",
                                    "items": {"type": "integer", "minimum": 1},
                                    "minItems": 1,
                                },
                            },
                            "required": ["id", "text", "source_pages"],
                        },
                    },
                    "examples": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "text": {"type": "string", "minLength": 1},
                                "source_pages": {
                                    "type": "array",
                                    "items": {"type": "integer", "minimum": 1},
                                    "minItems": 1,
                                },
                            },
                            "required": ["id", "text", "source_pages"],
                        },
                    },
                    "teach_back": {
                        "type": "object",
                        "properties": {
                            "must_understand": {
                                "type": "array",
                                "items": {"type": "string", "minLength": 1},
                                "minItems": 1,
                            },
                            "acceptable_explanation": {
                                "type": "string",
                                "minLength": 1,
                            },
                            # Gemini's structured-output schema only
                            # accepts a single ``type`` per field, not a
                            # union like ``["string", "null"]``. We
                            # therefore declare these as ``string`` and
                            # coerce empty / "null" responses to None
                            # inside ``Documentizer._parse_teach_back``.
                            "common_misconception": {
                                "type": "string",
                            },
                            "clarification_trigger": {
                                "type": "string",
                            },
                        },
                        "required": [
                            "must_understand",
                            "acceptable_explanation",
                            "common_misconception",
                            "clarification_trigger",
                        ],
                    },
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                },
                "required": [
                    "id",
                    "title",
                    "page_start",
                    "page_end",
                    "teach_back",
                    "confidence",
                ],
            },
        },
    },
    "required": ["title", "sections", "concepts", "chunks"],
}


__all__ = ["STRUCTURED_LESSON_SCHEMA"]