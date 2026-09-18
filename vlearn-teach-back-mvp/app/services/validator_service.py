"""ValidatorService — compares a student's explanation to a chunk.

For the MVP scaffold this is a **placeholder**. It uses trivial
keyword-overlap heuristics so the full teaching loop can be exercised
end-to-end. The next phase will plug in real LLM-based validation
that compares the explanation against the source transcript.
"""

from __future__ import annotations

from typing import List, Optional

from app.models.lesson import LessonChunk
from app.models.session import ValidationResult


class ValidatorService:
    """Returns a `ValidationResult` for a student explanation."""

    def _normalize(self, text: str) -> str:
        """Lowercase, collapse whitespace, drop parentheticals.

        Used so that e.g. ``"Representations are exchanged (JSON, XML, …)"``
        still matches ``"Representations are exchanged."``.
        """
        import re

        no_parens = re.sub(r"\([^)]*\)", "", text)
        return " ".join(no_parens.lower().split())

    def validate(
        self,
        chunk: Optional[LessonChunk],
        explanation: str,
        attempt: int = 1,
    ) -> ValidationResult:
        if chunk is None:
            return ValidationResult(
                chunk_id="",
                passed=False,
                missing_points=[],
                feedback="No chunk is currently active.",
                attempt=attempt,
            )

        exp_norm = self._normalize(explanation)
        missing: List[str] = [
            kp
            for kp in chunk.key_points
            if self._normalize(kp) not in exp_norm
        ]

        # Trivial rule: pass when no required key point is missing.
        passed = not missing

        if passed:
            feedback = (
                f"Looks good — your explanation covers the key points of "
                f"'{chunk.title}'."
            )
        else:
            feedback = (
                f"Your explanation is a start, but I still need clarification "
                f"on: {', '.join(missing)}."
            )

        return ValidationResult(
            chunk_id=chunk.id,
            passed=passed,
            missing_points=missing,
            feedback=feedback,
            attempt=attempt,
        )
