"""TeachBackChunk — Teach-Back unit inside a StructuredLesson.

A TeachBackChunk is one teachable "unit" of a lesson. The student is
expected to explain *this chunk* to the agent; the agent validates
against ``must_understand`` + ``acceptable_explanation`` and reacts to
``common_misconception`` / ``clarification_trigger`` when the student
misses something.

Each chunk has provenance (which pages it came from) and references
``concept_ids`` from the parent document so the validator can check
the student's explanation against the underlying concepts.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field, model_validator


class TeachBackTargets(BaseModel):
    """The four explicit Teach-Back targets.

    All four fields are required for a Teach-Back chunk **except**
    ``common_misconception``, which may be ``None`` when the source
    does not contain enough evidence to identify a likely misconception.

    Rules:

        * ``must_understand`` MUST NOT be empty (otherwise the chunk has
          nothing to validate against).
        * ``acceptable_explanation`` MUST be a single, clear sentence.
        * ``common_misconception`` MAY be ``None`` when unsupported by
          the source — the Documentizer MUST NOT invent one.
        * ``clarification_trigger`` MUST be non-empty when
          ``common_misconception`` is provided; optional otherwise.
    """

    must_understand: List[str] = Field(
        ...,
        min_length=1,
        description=(
            "Bullet list of facts the student must mention to pass the chunk"
        ),
    )
    acceptable_explanation: str = Field(
        ...,
        min_length=1,
        description="One-sentence description of what 'good enough' looks like",
    )
    common_misconception: Optional[str] = Field(
        default=None,
        description=(
            "Most likely wrong answer; None when the source gives no "
            "evidence for any specific misconception"
        ),
    )
    clarification_trigger: Optional[str] = Field(
        default=None,
        description=(
            "Natural-language rule for when the agent should ask back. "
            "Required when common_misconception is provided."
        ),
    )

    @model_validator(mode="after")
    def _validate_triggers(self) -> "TeachBackTargets":
        if (
            self.common_misconception is not None
            and self.common_misconception.strip()
            and not (self.clarification_trigger and self.clarification_trigger.strip())
        ):
            raise ValueError(
                "clarification_trigger is required when common_misconception "
                "is provided"
            )
        return self


class KeyPoint(BaseModel):
    """One bullet the student's explanation must cover."""

    id: str = Field(..., description="Stable key-point id within the chunk")
    text: str = Field(..., min_length=1)
    concept_id: Optional[str] = Field(
        default=None,
        description="Reference to the parent concept (optional)",
    )
    source_pages: List[int] = Field(..., min_length=1)


class ChunkExample(BaseModel):
    """One concrete example attached to a chunk."""

    id: str = Field(..., description="Stable example id within the chunk")
    text: str = Field(..., min_length=1)
    source_pages: List[int] = Field(..., min_length=1)


class TeachBackChunk(BaseModel):
    """One Teach-Back unit — the contract the validator enforces."""

    id: str = Field(..., description="Stable chunk id within the lesson")
    title: str = Field(..., min_length=1)
    summary: str = Field("", description="Short summary shown above the chunk")

    page_start: int = Field(..., ge=1)
    page_end: int = Field(..., ge=1)

    concept_ids: List[str] = Field(default_factory=list)
    key_points: List[KeyPoint] = Field(default_factory=list)
    examples: List[ChunkExample] = Field(default_factory=list)

    teach_back: TeachBackTargets = Field(..., description="Teach-Back contract")

    confidence: float = Field(0.5, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def _validate_page_range(self) -> "TeachBackChunk":
        if self.page_end < self.page_start:
            raise ValueError("page_end must be >= page_start")
        return self


__all__ = ["ChunkExample", "KeyPoint", "TeachBackChunk", "TeachBackTargets"]