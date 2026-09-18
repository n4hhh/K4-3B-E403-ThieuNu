"""Unit tests for the Teach-Back (D3) components.

These cover the rules that must hold on every turn regardless of what
the model returns — the four hard tests from the track brief plus the
provider plumbing. Nothing here touches the network.
"""

from __future__ import annotations

import json

import pytest

from app.models.lesson import Lesson, LessonChunk
from app.models.session import GapType
from app.services.ai.chat_provider import (
    ChatMessage,
    ChatProviderMisconfiguredError,
    ChatProviderTransientError,
    MockChatProvider,
    OpenAICompatibleChatProvider,
    build_chat_provider,
    build_chat_provider_safe,
    parse_json_object,
    scrub,
)
from app.services.ai_validator_service import (
    AIValidatorService,
    copied_ratio,
    leaks_answer,
)
from app.services.lesson_prep_service import LessonPrepService
from app.services.quiz_service import QuizService
from app.services.teach_back_agent_service import TeachBackAgentService


SOURCE = (
    "[T04-021] Mô hình ngôn ngữ lớn hoạt động bằng cách dự đoán token tiếp theo "
    "dựa trên toàn bộ ngữ cảnh đã có trước đó. "
    "[T04-022] Vì nó luôn chọn token có xác suất cao nhất theo phân phối đã học, "
    "nên khi không có dữ liệu phù hợp nó vẫn sinh ra câu trôi chảy nhưng sai sự thật. "
    "[T04-023] Đó là lý do mô hình bịa ra thông tin mà nghe vẫn rất thuyết phục."
)


def make_chunk(**overrides) -> LessonChunk:
    data = {
        "id": "c1",
        "title": "Vì sao LLM bịa",
        "description": "Cơ chế dự đoán token và hệ quả của nó.",
        "key_points": [
            "LLM dự đoán token tiếp theo dựa trên ngữ cảnh",
            "Mô hình chọn token có xác suất cao nhất nên có thể sai sự thật",
        ],
        "quality_bar": "Giải thích được cơ chế dự đoán và vì sao dẫn tới bịa.",
        "content": SOURCE,
    }
    data.update(overrides)
    return LessonChunk(**data)


# ---------------------------------------------------------------------------
# Chat provider
# ---------------------------------------------------------------------------


def test_parse_json_object_accepts_fenced_json():
    assert parse_json_object('```json\n{"a": 1}\n```') == {"a": 1}


def test_parse_json_object_accepts_json_inside_prose():
    assert parse_json_object('Kết quả: {"a": 1} — xong.') == {"a": 1}


def test_parse_json_object_rejects_non_object():
    with pytest.raises(ChatProviderTransientError):
        parse_json_object("hoàn toàn không phải JSON")


def test_scrub_removes_api_keys():
    assert "sk-0123456789abcdef0123" not in scrub("key=sk-0123456789abcdef0123 fail")


def test_openai_provider_refuses_missing_key():
    with pytest.raises(ChatProviderMisconfiguredError):
        OpenAICompatibleChatProvider(
            base_url="https://api.deepseek.com", api_key="", model="deepseek-flash"
        )


def test_openai_provider_builds_completions_endpoint():
    provider = OpenAICompatibleChatProvider(
        base_url="https://api.deepseek.com/",
        api_key="sk-test",
        model="deepseek-flash",
    )
    assert provider.endpoint == "https://api.deepseek.com/chat/completions"


def test_build_chat_provider_accepts_deepseek_alias(monkeypatch):
    monkeypatch.setenv("TEACH_BACK_BASE_URL", "https://api.deepseek.com")
    monkeypatch.setenv("TEACH_BACK_API_KEY", "sk-test")
    monkeypatch.setenv("TEACH_BACK_MODEL", "deepseek-flash")
    assert build_chat_provider("deepseek").name == "openai-compatible"


def test_build_chat_provider_rejects_unknown_name():
    with pytest.raises(ChatProviderMisconfiguredError):
        build_chat_provider("llama-on-my-laptop")


def test_build_chat_provider_safe_falls_back_to_mock(monkeypatch):
    """A broken key must cost AI quality, not the whole app."""
    monkeypatch.delenv("TEACH_BACK_API_KEY", raising=False)
    monkeypatch.setenv("TEACH_BACK_BASE_URL", "https://api.deepseek.com")
    assert build_chat_provider_safe("openai-compatible").name == "mock"


# ---------------------------------------------------------------------------
# Hard test 1 — paraphrase must be accepted, wording must not be required
# ---------------------------------------------------------------------------


def test_paraphrase_passes_when_the_model_says_so():
    """The verdict comes from meaning, not from matching the source text."""

    class PassProvider(MockChatProvider):
        def complete_json(self, messages, *, temperature=0.3, max_tokens=None):
            result = super().complete_json(
                messages, temperature=temperature, max_tokens=max_tokens
            )
            result.data = {
                "covered_points": [
                    "LLM dự đoán token tiếp theo dựa trên ngữ cảnh",
                    "Mô hình chọn token có xác suất cao nhất nên có thể sai sự thật",
                ],
                "missing_points": [],
                "gap_type": "none",
                "verdict": "pass",
                "confidence": 0.9,
                "reply": "Mình hiểu rồi, cảm ơn bạn.",
                "ask_back": "",
                "citations": ["T04-021"],
                "is_copied": False,
            }
            return result

    validator = AIValidatorService(provider=PassProvider(), max_attempts=4)
    result = validator.validate(
        make_chunk(),
        "Nó cứ đoán chữ tiếp theo dựa vào những gì đã nói, chọn chữ nào khả dĩ "
        "nhất, nên nhiều khi nghe xuôi tai mà nội dung lại không có thật.",
    )
    assert result.passed is True
    assert result.citations == ["T04-021"]


# ---------------------------------------------------------------------------
# Hard test 2 — pasted source text is not teaching
# ---------------------------------------------------------------------------


def test_copied_ratio_flags_verbatim_paste():
    assert copied_ratio(SOURCE, SOURCE) > 0.9


def test_copied_ratio_ignores_genuine_paraphrase():
    paraphrase = (
        "Nói đơn giản thì máy chỉ đang đoán chữ kế tiếp thôi, nó chọn cái nào "
        "hay gặp nhất, thành ra có lúc nói sai mà vẫn rất tự tin, mình phải tự "
        "kiểm tra lại nguồn cho chắc chứ đừng tin ngay."
    )
    assert copied_ratio(paraphrase, SOURCE) < 0.45


def test_pasted_explanation_is_rejected_before_any_model_call():
    provider = MockChatProvider()
    validator = AIValidatorService(provider=provider, max_attempts=4)
    result = validator.validate(make_chunk(), SOURCE)

    assert result.passed is False
    assert result.gap_type == GapType.COPIED
    assert result.is_copied is True
    assert provider.calls == []  # no tokens spent on an obvious paste


# ---------------------------------------------------------------------------
# Hard test 3 — the agent must not "understand" too easily
# ---------------------------------------------------------------------------


def test_thin_explanation_is_rejected():
    validator = AIValidatorService(provider=MockChatProvider(), max_attempts=4)
    result = validator.validate(make_chunk(), "Ừ thì nó bịa thôi.")
    assert result.passed is False
    assert result.ask_back


def test_pass_is_downgraded_when_points_are_still_missing():
    """A model that says "pass" while listing gaps does not get its way."""

    class SloppyProvider(MockChatProvider):
        def complete_json(self, messages, *, temperature=0.3, max_tokens=None):
            result = super().complete_json(
                messages, temperature=temperature, max_tokens=max_tokens
            )
            result.data = {
                "verdict": "pass",
                "covered_points": [],
                "missing_points": ["Mô hình chọn token có xác suất cao nhất"],
                "gap_type": "none",
                "reply": "Nghe ổn đấy!",
                "ask_back": "",
                "confidence": 0.9,
            }
            return result

    validator = AIValidatorService(provider=SloppyProvider(), max_attempts=4)
    result = validator.validate(
        make_chunk(),
        "Mình nghĩ mô hình ngôn ngữ đọc câu hỏi rồi trả lời theo dữ liệu nó có "
        "sẵn từ trước đó thôi.",
    )
    assert result.passed is False
    assert result.gap_type == GapType.INCOMPLETE
    assert result.ask_back  # a neutral probe is supplied


# ---------------------------------------------------------------------------
# Hard test 4 — never reveal the answer
# ---------------------------------------------------------------------------


def test_leaks_answer_detects_a_question_that_states_the_point():
    point = "Mô hình chọn token có xác suất cao nhất nên có thể sai sự thật"
    question = (
        "Bạn quên mất rằng mô hình luôn chọn token có xác suất cao nhất nên "
        "nó có thể sai sự thật, đúng không?"
    )
    assert leaks_answer(question, [point]) is True


def test_leaks_answer_allows_a_genuine_probe():
    point = "Mô hình chọn token có xác suất cao nhất nên có thể sai sự thật"
    assert leaks_answer("Vì sao điều đó lại xảy ra?", [point]) is False


def test_leaking_ask_back_is_replaced():
    class LeakyProvider(MockChatProvider):
        def complete_json(self, messages, *, temperature=0.3, max_tokens=None):
            result = super().complete_json(
                messages, temperature=temperature, max_tokens=max_tokens
            )
            result.data = {
                "verdict": "gap",
                "covered_points": [],
                "missing_points": [
                    "Mô hình chọn token có xác suất cao nhất nên có thể sai sự thật"
                ],
                "gap_type": "incomplete",
                "reply": "Mình chưa rõ.",
                "ask_back": (
                    "Ý bạn là mô hình chọn token có xác suất cao nhất nên nó "
                    "có thể sai sự thật phải không?"
                ),
                "confidence": 0.6,
            }
            return result

    validator = AIValidatorService(provider=LeakyProvider(), max_attempts=4)
    result = validator.validate(
        make_chunk(),
        "Mình hiểu là mô hình đọc ngữ cảnh rồi sinh ra chữ tiếp theo, đại khái "
        "giống như đoán từ trong câu vậy đó.",
    )
    assert "xác suất cao nhất" not in result.ask_back


# ---------------------------------------------------------------------------
# Attempt limit, citations, agent voice
# ---------------------------------------------------------------------------


def test_attempt_limit_passes_with_needs_review():
    validator = AIValidatorService(provider=MockChatProvider(), max_attempts=2)
    result = validator.validate(make_chunk(), "Chịu, mình không nhớ.", attempt=2)
    assert result.passed is True
    assert result.needs_review is True
    assert result.ask_back == ""


def test_fabricated_citations_are_dropped():
    class FakeCitationProvider(MockChatProvider):
        def complete_json(self, messages, *, temperature=0.3, max_tokens=None):
            result = super().complete_json(
                messages, temperature=temperature, max_tokens=max_tokens
            )
            result.data = {
                "verdict": "gap",
                "missing_points": ["x"],
                "gap_type": "incomplete",
                "reply": "Chưa rõ.",
                "ask_back": "Bạn nói thêm giúp mình?",
                "citations": ["T04-021", "T99-999"],
            }
            return result

    validator = AIValidatorService(provider=FakeCitationProvider(), max_attempts=4)
    result = validator.validate(
        make_chunk(),
        "Mô hình sinh văn bản bằng cách nối các từ lại với nhau theo thói quen "
        "nó học được từ dữ liệu.",
    )
    assert result.citations == ["T04-021"]


def test_agent_reply_shows_citation_footer():
    from app.models.session import ValidationResult

    agent = TeachBackAgentService()
    reply = agent.reply_to_explanation(
        make_chunk(),
        ValidationResult(
            chunk_id="c1",
            passed=False,
            feedback="Mình chưa rõ chỗ này.",
            ask_back="Bạn cho mình một ví dụ được không?",
            citations=["T04-022"],
        ),
    )
    assert "T04-022" in reply
    assert "ví dụ" in reply


# ---------------------------------------------------------------------------
# Lesson prep + quiz
# ---------------------------------------------------------------------------


def test_lesson_prep_caches_to_disk(tmp_path):
    provider = MockChatProvider()
    prep = LessonPrepService(provider=provider, cache_dir=tmp_path)
    lesson = Lesson(id="L1", title="Bài thử", chunks=[make_chunk(key_points=[])])

    prep.ensure_lesson(lesson)
    assert lesson.chunks[0].key_points
    first_call_count = len(provider.calls)

    # A fresh service must reuse the cache rather than call the model.
    prep2 = LessonPrepService(provider=provider, cache_dir=tmp_path)
    lesson2 = Lesson(id="L1", title="Bài thử", chunks=[make_chunk(key_points=[])])
    prep2.ensure_lesson(lesson2)
    assert len(provider.calls) == first_call_count


def test_lesson_prep_falls_back_to_heuristic_when_disabled(tmp_path):
    prep = LessonPrepService(
        provider=MockChatProvider(), cache_dir=tmp_path, enabled=False
    )
    lesson = Lesson(id="L2", title="Bài thử", chunks=[make_chunk(key_points=[])])
    prep.ensure_lesson(lesson)
    assert lesson.chunks[0].key_points  # never empty


def test_quiz_service_drops_malformed_questions(tmp_path):
    class HalfBrokenProvider(MockChatProvider):
        def complete_json(self, messages, *, temperature=0.3, max_tokens=None):
            result = super().complete_json(
                messages, temperature=temperature, max_tokens=max_tokens
            )
            result.data = {
                "questions": [
                    {
                        "prompt": "Câu hợp lệ?",
                        "options": ["A", "B", "C", "D"],
                        "correct_index": 2,
                    },
                    {"prompt": "Thiếu phương án", "options": [], "correct_index": 0},
                    {
                        "prompt": "Index sai",
                        "options": ["A", "B"],
                        "correct_index": 7,
                    },
                ]
            }
            return result

    service = QuizService(provider=HalfBrokenProvider(), cache_dir=tmp_path)
    lesson = Lesson(id="L3", title="Bài thử", chunks=[make_chunk()])
    # Only one question survives, which is below the 3-question floor, so
    # the service declines rather than shipping a broken quiz.
    assert service.get_quiz(lesson, fallback=None) is None


def test_quiz_service_caches_generated_quiz(tmp_path):
    provider = MockChatProvider()
    service = QuizService(provider=provider, cache_dir=tmp_path)
    lesson = Lesson(id="L4", title="Bài thử", chunks=[make_chunk()])

    first = service.get_quiz(lesson)
    assert first is not None and len(first.questions) >= 3

    calls_after_first = len(provider.calls)
    QuizService(provider=provider, cache_dir=tmp_path).get_quiz(lesson)
    assert len(provider.calls) == calls_after_first
