"""AIValidatorService — decides whether a student really taught the chunk.

This is the component the whole D3 idea stands on. Everything else is
plumbing around this question:

    Given the source material, did this explanation demonstrate
    understanding — and if not, exactly where is the hole?

The pipeline per student turn::

    explanation
        │
        ├─ 1. copy check      (deterministic, pre-LLM)
        ├─ 2. substance check (deterministic, pre-LLM)
        ├─ 3. LLM grading     (grounded in the chunk's source text)
        ├─ 4. leak guard      (never let the reply contain the answer)
        └─ 5. pass policy     (coverage, attempt limit, needs-review)

Steps 1, 2, 4 and 5 are deliberately *not* delegated to the model. They
encode product rules that must hold on every turn, including the turn
where the model returns something odd, and they are the four cases the
track brief calls out as hard tests:

* "học viên dán nguyên đoạn tài liệu" → step 1
* "agent hiểu quá dễ"                 → steps 2 and 5
* "không lộ đáp án"                   → step 4
* "đúng nhưng diễn đạt khác"          → left to the model (step 3), which
  judges meaning; no keyword matching happens anywhere in this file.

When the model is unreachable the service degrades to a heuristic
verdict rather than failing the request. A degraded verdict is marked
``evaluator="heuristic"`` so the UI and the instructor log can say so
instead of pretending the AI ruled on it.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from typing import Dict, List, Optional, Sequence, Set, Tuple

from app.models.lesson import LessonChunk
from app.models.session import GapType, ValidationResult
from app.services.ai.chat_provider import (
    ChatMessage,
    ChatProvider,
    ChatProviderError,
)
from app.services.ai.teach_prompts import VALIDATE_SYSTEM, build_validate_prompt

logger = logging.getLogger(__name__)


_CITATION_RE = re.compile(r"\[T\d{2}-\d{3}\]\s*")
_CITATION_CODE_RE = re.compile(r"T\d{2}-\d{3}")
_WORD_RE = re.compile(r"\w+", re.UNICODE)

# How much source text the grader sees. The whole chunk would blow the
# latency budget for a live demo; the opening carries the claims.
_SOURCE_CHAR_BUDGET = 4000

# Copy detection: share of the student's 8-word windows that also appear
# verbatim in the source. Pasting scores ~1.0; genuine paraphrase of a
# Vietnamese lecture rarely clears 0.3.
_COPY_NGRAM = 8
_COPY_THRESHOLD = 0.45
_COPY_MIN_WORDS = 40

# Substance floor. Below this an explanation cannot cover anything, and
# asking the model to grade "ừ đúng rồi" wastes a call.
_MIN_WORDS = 12

# Leak guard: if this share of a missing key point's distinctive words
# shows up in the agent's question, the question gave the answer away.
#
# Short key points ("5xx là lỗi phía server" — four content words) are
# topic labels: any honest question about them echoes most of their
# vocabulary, so scoring them produces false positives and throws away
# good questions. Only points with real substance are checked.
_LEAK_THRESHOLD = 0.7
_LEAK_MIN_WORDS = 5

# Vietnamese function words carry no topical information, so they must
# not count towards either overlap measure.
_STOPWORDS: Set[str] = {
    "là", "và", "của", "có", "được", "trong", "cho", "với", "một", "các",
    "những", "này", "đó", "khi", "thì", "mà", "để", "không", "người", "ta",
    "mình", "bạn", "tôi", "nó", "cái", "rất", "cũng", "nếu", "như", "về",
    "ở", "đã", "sẽ", "đang", "phải", "nên", "hay", "hoặc", "nhưng", "vì",
    "nhiều", "ít", "ra", "vào", "lên", "xuống", "từ", "đến", "theo", "trên",
    "dưới", "sau", "trước", "rồi", "còn", "chỉ", "thế", "vậy", "làm", "gì",
    "the", "a", "an", "of", "to", "is", "are", "and", "or", "in", "on",
    "for", "it", "that", "this", "we", "you",
}


def _normalize(text: str) -> str:
    """Lowercase, strip accents-insensitive noise, collapse whitespace."""
    cleaned = _CITATION_RE.sub("", text)
    cleaned = unicodedata.normalize("NFC", cleaned).lower()
    return " ".join(cleaned.split())


def _words(text: str) -> List[str]:
    return _WORD_RE.findall(_normalize(text))


def _content_words(text: str) -> Set[str]:
    return {w for w in _words(text) if w not in _STOPWORDS and len(w) > 1}


def _ngrams(words: Sequence[str], n: int) -> Set[str]:
    if len(words) < n:
        return set()
    return {" ".join(words[i : i + n]) for i in range(len(words) - n + 1)}


def copied_ratio(explanation: str, source: str) -> float:
    """Return the share of the explanation copied verbatim from ``source``.

    0.0 means nothing matched; 1.0 means every window of the explanation
    appears in the source.
    """
    exp_words = _words(explanation)
    if len(exp_words) < _COPY_MIN_WORDS:
        return 0.0
    exp_grams = _ngrams(exp_words, _COPY_NGRAM)
    if not exp_grams:
        return 0.0
    src_grams = _ngrams(_words(source), _COPY_NGRAM)
    if not src_grams:
        return 0.0
    return len(exp_grams & src_grams) / len(exp_grams)


def leaks_answer(question: str, missing_points: Sequence[str]) -> bool:
    """Return True when ``question`` states a point it should be asking about.

    We compare distinctive (non-stopword) vocabulary. A question that
    reuses most of a missing point's content words has, in practice,
    told the student the answer and merely appended a question mark.
    """
    q_words = _content_words(question)
    if not q_words:
        return False
    for point in missing_points:
        p_words = _content_words(point)
        if len(p_words) < _LEAK_MIN_WORDS:
            continue
        overlap = len(p_words & q_words) / len(p_words)
        if overlap >= _LEAK_THRESHOLD:
            return True
    return False


class AIValidatorService:
    """Grades a student explanation against a chunk's source material."""

    def __init__(
        self,
        provider: ChatProvider,
        max_attempts: int = 4,
        enabled: bool = True,
    ) -> None:
        self._provider = provider
        self._max_attempts = max(1, max_attempts)
        self._enabled = enabled

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------

    def validate(
        self,
        chunk: Optional[LessonChunk],
        explanation: str,
        attempt: int = 1,
        *,
        lesson_title: str = "",
        history: Optional[Sequence[Dict[str, str]]] = None,
    ) -> ValidationResult:
        """Return the verdict for one student turn."""
        if chunk is None:
            return ValidationResult(
                chunk_id="",
                passed=False,
                feedback="Hiện chưa có phần nào đang mở.",
                attempt=attempt,
                gap_type=GapType.OFF_TOPIC,
            )

        last_attempt = attempt >= self._max_attempts

        # --- 1. pasted source is not teaching --------------------------
        # The rule-based verdicts below still go through ``_apply_policy``
        # so the attempt limit applies to them too — otherwise a student
        # who keeps answering in five words would be stuck forever.
        ratio = copied_ratio(explanation, chunk.content)
        if ratio >= _COPY_THRESHOLD:
            return self._apply_policy(ValidationResult(
                chunk_id=chunk.id,
                passed=False,
                missing_points=list(chunk.key_points),
                feedback=(
                    "Đoạn này nghe giống hệt tài liệu. Tôi đọc tài liệu rồi mà "
                    "vẫn chưa hiểu — bạn nói lại bằng lời của bạn giúp tôi nhé."
                ),
                ask_back=(
                    f"Nếu phải giải thích '{chunk.title}' cho một người bạn "
                    "chưa đọc tài liệu, bạn sẽ nói thế nào?"
                ),
                attempt=attempt,
                gap_type=GapType.COPIED,
                is_copied=True,
                confidence=min(1.0, ratio),
                note_for_instructor=(
                    f"Học viên dán lại nguồn ({ratio:.0%} trùng nguyên văn)."
                ),
                evaluator="rule",
            ), chunk, last_attempt)

        # --- 2. too thin to be an explanation --------------------------
        if len(_words(explanation)) < _MIN_WORDS:
            return self._apply_policy(ValidationResult(
                chunk_id=chunk.id,
                passed=False,
                missing_points=list(chunk.key_points),
                feedback=(
                    "Tôi vẫn chưa hình dung được. Bạn giải thích kỹ hơn một "
                    "chút giúp tôi nhé."
                ),
                ask_back=(
                    f"Với '{chunk.title}', ý quan trọng nhất mà bạn muốn tôi "
                    "nhớ là gì, và vì sao nó quan trọng?"
                ),
                attempt=attempt,
                gap_type=GapType.VAGUE,
                note_for_instructor="Lời giải thích quá ngắn để đánh giá.",
                evaluator="rule",
            ), chunk, last_attempt)

        # --- 3. model grading ------------------------------------------
        result = self._grade(
            chunk=chunk,
            explanation=explanation,
            attempt=attempt,
            lesson_title=lesson_title,
            history=history,
        )

        # --- 4 & 5. product rules on top of the model's verdict --------
        return self._apply_policy(result, chunk, last_attempt)

    # ------------------------------------------------------------------
    # Model call
    # ------------------------------------------------------------------

    def _grade(
        self,
        *,
        chunk: LessonChunk,
        explanation: str,
        attempt: int,
        lesson_title: str,
        history: Optional[Sequence[Dict[str, str]]],
    ) -> ValidationResult:
        if not self._enabled or not chunk.key_points:
            return self._heuristic(chunk, explanation, attempt)

        messages = [
            ChatMessage(role="system", content=VALIDATE_SYSTEM),
            ChatMessage(
                role="user",
                content=build_validate_prompt(
                    lesson_title=lesson_title or chunk.title,
                    chunk_title=chunk.title,
                    key_points=chunk.key_points,
                    quality_bar=chunk.quality_bar,
                    source_text=chunk.content[:_SOURCE_CHAR_BUDGET],
                    explanation=explanation,
                    history=history,
                    attempt=attempt,
                    max_attempts=self._max_attempts,
                ),
            ),
        ]

        # One retry: the usual failure is a truncated or malformed JSON
        # reply, which a second sample normally fixes. Falling straight
        # through to the heuristic would visibly dumb down the agent
        # mid-conversation.
        completion = None
        last_error: Optional[ChatProviderError] = None
        for attempt_index in range(2):
            try:
                completion = self._provider.complete_json(
                    messages,
                    temperature=0.3 if attempt_index == 0 else 0.1,
                )
                break
            except ChatProviderError as exc:
                last_error = exc
                logger.warning(
                    "Validation call %d/2 failed for chunk %s: %s",
                    attempt_index + 1,
                    chunk.id,
                    exc,
                )

        if completion is None:
            logger.warning(
                "Validation fell back to the heuristic for chunk %s (%s).",
                chunk.id,
                last_error,
            )
            return self._heuristic(chunk, explanation, attempt)

        data = completion.data
        verdict = str(data.get("verdict", "")).strip().lower()
        gap_type = self._coerce_gap_type(data.get("gap_type"))

        reply = str(data.get("reply") or "").strip()
        ask_back = str(data.get("ask_back") or "").strip()
        if not reply:
            reply = ask_back or "Tôi vẫn còn một chỗ chưa rõ."

        return ValidationResult(
            chunk_id=chunk.id,
            passed=verdict == "pass",
            covered_points=self._string_list(data.get("covered_points")),
            missing_points=self._string_list(data.get("missing_points")),
            feedback=reply,
            ask_back=ask_back,
            attempt=attempt,
            gap_type=gap_type,
            citations=self._citation_list(data.get("citations"), chunk.content),
            confidence=self._coerce_confidence(data.get("confidence")),
            is_copied=bool(data.get("is_copied")),
            note_for_instructor=str(data.get("note_for_instructor") or "").strip(),
            evaluator="ai",
        )

    # ------------------------------------------------------------------
    # Policy
    # ------------------------------------------------------------------

    def _apply_policy(
        self,
        result: ValidationResult,
        chunk: LessonChunk,
        last_attempt: bool,
    ) -> ValidationResult:
        """Apply the rules the model is not allowed to decide on its own."""

        # Do not let a "pass" through while required points are still
        # missing — this is the "agent hiểu quá dễ" failure mode.
        if result.passed and result.missing_points:
            result.passed = False
            if result.gap_type == GapType.NONE:
                result.gap_type = GapType.INCOMPLETE

        # Leak guard: a question that contains its own answer is worse
        # than no question, so replace it with a neutral probe.
        if not result.passed and result.ask_back:
            if leaks_answer(result.ask_back, result.missing_points):
                logger.info(
                    "Ask-back for chunk %s leaked the answer — replaced.", chunk.id
                )
                result.ask_back = self._neutral_probe(chunk, result.gap_type)
                result.feedback = (
                    "Tôi nghĩ mình vẫn còn thiếu một mảnh ở đây."
                )
        if not result.passed and not result.ask_back:
            result.ask_back = self._neutral_probe(chunk, result.gap_type)

        # A student who keeps missing the same point should not be stuck
        # in the loop forever. Let them move on, flagged for review, and
        # point them at the passage to re-read. Practice, not an exam.
        if not result.passed and last_attempt:
            result.passed = True
            result.needs_review = True
            result.ask_back = ""
            result.feedback = (
                "Cảm ơn bạn đã kiên nhẫn giải thích. Phần này tôi vẫn còn một "
                "chỗ chưa nắm chắc, nên mình đánh dấu để bạn xem lại sau — "
                "giờ mình đi tiếp đã nhé."
            )
        return result

    @staticmethod
    def _neutral_probe(chunk: LessonChunk, gap_type: GapType) -> str:
        """Return a question that asks without revealing anything."""
        if gap_type == GapType.CONTRADICTED:
            return (
                "Chỗ bạn vừa nói khác với điều tôi đọc được trong bài. "
                "Bạn dẫn lại giúp tôi vì sao bạn kết luận như vậy?"
            )
        if gap_type == GapType.OFF_TOPIC:
            return (
                f"Tôi đang hỏi về '{chunk.title}'. Phần bạn vừa nói liên quan "
                "tới nó như thế nào?"
            )
        return (
            f"Trong phần '{chunk.title}', còn điều gì nữa mà nếu thiếu thì tôi "
            "sẽ hiểu sai? Bạn cho tôi một ví dụ cụ thể được không?"
        )

    # ------------------------------------------------------------------
    # Offline fallback
    # ------------------------------------------------------------------

    @staticmethod
    def _heuristic(
        chunk: LessonChunk, explanation: str, attempt: int
    ) -> ValidationResult:
        """Verdict without a model: content-word overlap per key point.

        Crude on purpose. It accepts loose paraphrase and rejects empty
        talk, which is enough to keep the loop demonstrable offline, and
        it labels itself so nobody mistakes it for the real grader.
        """
        exp_words = _content_words(explanation)
        covered: List[str] = []
        missing: List[str] = []
        for point in chunk.key_points:
            p_words = _content_words(point)
            if not p_words:
                continue
            overlap = len(p_words & exp_words) / len(p_words)
            (covered if overlap >= 0.34 else missing).append(point)

        passed = not missing and bool(covered)
        return ValidationResult(
            chunk_id=chunk.id,
            passed=passed,
            covered_points=covered,
            missing_points=missing,
            feedback=(
                "Tôi nghĩ mình đã nắm được ý của bạn."
                if passed
                else "Tôi vẫn còn một chỗ chưa rõ trong phần này."
            ),
            attempt=attempt,
            gap_type=GapType.NONE if passed else GapType.INCOMPLETE,
            confidence=0.4,
            note_for_instructor="Chấm bằng heuristic (không gọi được AI).",
            evaluator="heuristic",
        )

    # ------------------------------------------------------------------
    # Coercion helpers — model output is never trusted as-is
    # ------------------------------------------------------------------

    @staticmethod
    def _string_list(value: object) -> List[str]:
        if not isinstance(value, list):
            return []
        return [str(v).strip() for v in value if str(v).strip()]

    @staticmethod
    def _citation_list(value: object, source: str) -> List[str]:
        """Keep only citation codes that actually occur in the source.

        A fabricated citation is worse than none: it looks like evidence.
        """
        available = set(_CITATION_CODE_RE.findall(source))
        found: List[str] = []
        for raw in AIValidatorService._string_list(value):
            for code in _CITATION_CODE_RE.findall(raw):
                if code in available and code not in found:
                    found.append(code)
        return found

    @staticmethod
    def _coerce_confidence(value: object) -> float:
        try:
            number = float(value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return 0.0
        return max(0.0, min(1.0, number))

    @staticmethod
    def _coerce_gap_type(value: object) -> GapType:
        try:
            return GapType(str(value).strip().lower())
        except ValueError:
            return GapType.NONE


__all__ = ["AIValidatorService", "copied_ratio", "leaks_answer"]
