"""ValidationReport — Phase 3A.5 validation result.

Three independent gates contribute to the final report:

    * Gate A — Schema Validation (Pydantic + structural checks)
    * Gate B — Source Grounding (citation/page/excerpt alignment)
    * Gate C — Confidence + hallucination guard

A document is **published** only when the combined status is ``PASS`` or
``WARN``. Any ``FAIL`` short-circuits the publication gate.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class GateName(str, Enum):
    SCHEMA = "schema"
    GROUNDING = "grounding"
    CONFIDENCE = "confidence"


class GateOutcome(str, Enum):
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


class IssueSeverity(str, Enum):
    INFO = "info"
    WARN = "warn"
    ERROR = "error"


class ValidationIssue(BaseModel):
    """One concrete finding from a gate."""

    severity: IssueSeverity = IssueSeverity.WARN
    code: str = Field(..., description="Closed-list code, e.g. 'SG-6', 'low_confidence'")
    gate: GateName
    target: Optional[str] = Field(
        default=None,
        description="Path or id of the offending element (e.g. 'chunk-x', 'concept-y')",
    )
    detail: str = ""


class GateResult(BaseModel):
    """One gate's verdict."""

    gate: GateName
    outcome: GateOutcome
    score: Optional[float] = Field(
        default=None,
        description="Numeric score in [0, 1] where applicable (grounding)",
    )
    issues: List[ValidationIssue] = Field(default_factory=list)
    duration_ms: int = 0


class ValidationPolicy(BaseModel):
    """Thresholds used to decide PASS / WARN / FAIL.

    All values are read from configuration at documentizer time and
    frozen into the report for reproducibility.
    """

    grounding_threshold: float = Field(0.80, ge=0.0, le=1.0)
    page_coverage_floor: float = Field(0.60, ge=0.0, le=1.0)
    min_confidence: float = Field(0.65, ge=0.0, le=1.0)


class ProvenanceStats(BaseModel):
    """Aggregate provenance of a StructuredLesson.

    These are *aggregate* numbers, not per-field evidence.
    """

    total_blocks: int = 0
    grounded_blocks: int = 0
    ungrounded_block_ids: List[str] = Field(default_factory=list)
    page_coverage: Dict[str, float] = Field(
        default_factory=dict,
        description="1-based page number (as string) → coverage ratio in [0, 1]",
    )


class ValidationReport(BaseModel):
    """The full validation report for one DocumentizerPipeline run.

    The ``status`` is the **combined** verdict; ``publish`` is allowed
    only when ``status ∈ {PASS, WARN}``.
    """

    schema_version: str = "3a5.validation.v1"

    status: GateOutcome = Field(..., description="Combined verdict")
    schema_ok: bool
    grounding_score: float = Field(..., ge=0.0, le=1.0)
    low_confidence_chunk_ids: List[str] = Field(default_factory=list)

    gates: List[GateResult] = Field(default_factory=list)
    issues: List[ValidationIssue] = Field(default_factory=list)
    policy: ValidationPolicy = Field(default_factory=ValidationPolicy)
    provenance: ProvenanceStats = Field(default_factory=ProvenanceStats)

    performed_at: datetime = Field(default_factory=datetime.utcnow)

    def can_publish(self) -> bool:
        """Whether this report allows ``published.json`` to be written."""
        return self.status in (GateOutcome.PASS, GateOutcome.WARN)


__all__ = [
    "GateName",
    "GateOutcome",
    "GateResult",
    "IssueSeverity",
    "ProvenanceStats",
    "ValidationIssue",
    "ValidationPolicy",
    "ValidationReport",
]