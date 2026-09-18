"""TeachBackAgentService — the words the "student" agent actually says.

The agent plays a learner who has *not* understood the lesson yet. Its
voice matters as much as its verdict: the track D safety note is that a
student must never feel graded or talked down to, and the D3 rubric
gives 15 points for never revealing the answer.

This service does no grading. It turns a
:class:`~app.models.session.ValidationResult` into a message. Keeping
the two apart means the "does it pass" logic can be tested without
asserting on prose, and the prose can be changed without touching the
logic.

Drop-in compatible with ``MockAgentService`` so the wiring in
``app.main`` can swap one for the other.
"""

from __future__ import annotations

from typing import List, Optional

from app.models.lesson import Lesson, LessonChunk
from app.models.session import GapType, ValidationResult


class TeachBackAgentService:
    """Composes the agent's turns in the teaching conversation."""

    def __init__(self, show_citations: bool = True) -> None:
        self._show_citations = show_citations

    # ------------------------------------------------------------------
    # Session-level messages
    # ------------------------------------------------------------------

    def opening_message(self, lesson: Lesson) -> str:
        """The agent's first turn, framing who plays which role."""
        count = len(lesson.chunks)
        first = lesson.chunks[0].title if lesson.chunks else ""
        return (
            f"Chào bạn! Mình vừa xem qua bài **{lesson.title}** nhưng thú thật "
            f"là chưa hiểu mấy. Bạn dạy lại cho mình nhé?\n\n"
            f"Bài này có {count} phần. Mình sẽ hỏi lại khi chỗ nào còn mơ hồ — "
            f"và mình sẽ không nói trước đáp án đâu, vì mình đang là người học mà.\n\n"
            f"Bắt đầu từ phần đầu tiên: **{first}**. "
            f"Bạn giải thích bằng lời của bạn giúp mình."
        )

    def chunk_prompt(self, chunk: LessonChunk) -> str:
        """The agent's opening question for a new chunk."""
        lines = [f"Giờ tới phần **{chunk.title}**. Bạn dạy mình phần này nhé."]
        if chunk.description:
            lines.append(f"\n> {chunk.description}")
        lines.append("\nBạn cứ nói theo cách bạn hiểu, không cần giống tài liệu.")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Reply to a student explanation
    # ------------------------------------------------------------------

    def reply_to_explanation(
        self,
        chunk: Optional[LessonChunk],
        validation: ValidationResult,
    ) -> str:
        """Render the agent's reply for one graded turn."""
        parts: List[str] = []

        feedback = (validation.feedback or "").strip()
        if feedback:
            parts.append(feedback)

        if validation.passed:
            if validation.needs_review:
                # Flagged-for-review is still a pass; say so kindly and
                # point at the passage instead of at the student.
                citation = self._citation_line(validation)
                if citation:
                    parts.append(citation)
            elif chunk is not None:
                parts.append(
                    f"Mình tóm lại để chắc: mình đã hiểu được phần "
                    f"**{chunk.title}** qua cách bạn giải thích."
                )
            return "\n\n".join(parts)

        if validation.ask_back:
            parts.append(validation.ask_back)

        citation = self._citation_line(validation)
        if citation:
            parts.append(citation)

        return "\n\n".join(parts) if parts else "Bạn nói rõ thêm giúp mình nhé."

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _citation_line(self, validation: ValidationResult) -> str:
        """Return the "review this passage" footer, if we have one.

        Citations point the student back at the lecture rather than
        handing over the content — the agent stays naive while still
        being grounded.
        """
        if not self._show_citations or not validation.citations:
            return ""
        codes = ", ".join(validation.citations[:3])
        return f"📖 Tham chiếu bài giảng: {codes}"

    @staticmethod
    def gap_label(chunk: Optional[LessonChunk], validation: ValidationResult) -> str:
        """Short label for the learning-result "areas clarified" list."""
        if validation.missing_points:
            first = validation.missing_points[0]
            return first if len(first) <= 90 else first[:87] + "…"
        if chunk is not None:
            return chunk.title
        return "Chưa rõ"

    @staticmethod
    def gap_badge(validation: ValidationResult) -> str:
        """Human-readable badge shown next to a gap message in the UI."""
        return {
            GapType.INCOMPLETE: "Còn thiếu ý",
            GapType.VAGUE: "Chưa rõ ý",
            GapType.CONTRADICTED: "Khác với bài giảng",
            GapType.COPIED: "Cần nói bằng lời của bạn",
            GapType.OFF_TOPIC: "Chưa đúng phần đang học",
        }.get(validation.gap_type, "Cần làm rõ")


__all__ = ["TeachBackAgentService"]
