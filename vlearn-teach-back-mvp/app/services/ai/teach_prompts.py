"""Prompts for the Teach-Back loop (track D3).

Everything the agent's behaviour depends on lives here, in one file, so
the behaviour can be reviewed and tuned without reading service code.

Three prompts:

``ANALYZE_CHUNK``
    Source text → key points + quality bar. Run once per chunk and
    cached; this is what the validator later compares against.

``VALIDATE_EXPLANATION``
    The grader. It is the only component that decides pass/gap, and it
    is explicitly told to reason from the *source*, not from its own
    knowledge, and to accept paraphrase.

``GENERATE_QUIZ``
    End-of-lesson quiz, grounded in the same source.

Design notes tied to the track brief
------------------------------------

* **Naive-but-controlled student.** The agent plays a learner. It must
  never state the missing content — that would hand the student the
  answer and collapse the whole exercise. The prompts forbid it
  explicitly and the service layer checks the output afterwards.

* **Paraphrase is not a gap.** The first hard test is "student is right
  but words it differently". The grader is told to judge meaning, and
  that matching the source's wording is neither necessary nor
  sufficient.

* **Confident and wrong is the worst case.** The grader gets a separate
  ``contradicted`` gap type so the agent can ask about the specific
  claim rather than about a missing bullet.

* **Pasting is not teaching.** Verbatim source text gets flagged, and
  the agent asks for the idea in the student's own words.

* **Do not "understand" too easily.** Passing requires covering the
  quality bar, not just producing text. Encouragement never substitutes
  for coverage.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Sequence


# ---------------------------------------------------------------------------
# 1. Chunk analysis
# ---------------------------------------------------------------------------

ANALYZE_CHUNK_SYSTEM = """\
TASK:ANALYZE_CHUNK

Bạn là trợ lý thiết kế bài học cho nền tảng VLearn. Bạn nhận một đoạn \
nội dung bài giảng (transcript hoặc slide) và rút ra tiêu chí để kiểm tra \
xem một học viên đã thực sự hiểu đoạn đó hay chưa.

Quy tắc:
1. CHỈ dùng thông tin có trong nguồn được cung cấp. Không thêm kiến thức ngoài.
2. key_points là các Ý mà người học BẮT BUỘC phải nêu được thì mới coi là \
hiểu đoạn này. Viết mỗi ý thành một câu ngắn, độc lập, bằng tiếng Việt.
3. Từ 2 đến 4 key_points. Ít hơn 2 là quá dễ, nhiều hơn 4 là quá vụn.
4. Không đưa vào key_points những thứ chỉ là ví dụ minh hoạ, câu chuyện bên \
lề, hay phần tương tác lớp học.
5. quality_bar mô tả trong một câu: thế nào là một lời giải thích ĐẠT cho đoạn này.
6. key_concepts là các thuật ngữ then chốt xuất hiện trong nguồn (tối đa 6).

Trả về DUY NHẤT một JSON object:
{
  "key_points": ["...", "..."],
  "quality_bar": "...",
  "key_concepts": ["...", "..."]
}"""


def build_analyze_chunk_prompt(
    *, lesson_title: str, chunk_title: str, source_text: str
) -> str:
    """Return the user prompt asking for key points of one chunk."""
    return (
        f"BÀI HỌC: {lesson_title}\n"
        f"TÊN ĐOẠN: {chunk_title}\n\n"
        f"NGUỒN (nguyên văn từ bài giảng):\n"
        f"<<<\n{source_text}\n>>>\n\n"
        "Hãy rút ra tiêu chí kiểm tra hiểu bài cho đoạn này."
    )


# ---------------------------------------------------------------------------
# 2. Explanation validation — the core of D3
# ---------------------------------------------------------------------------

VALIDATE_SYSTEM = """\
TASK:VALIDATE_EXPLANATION

Bạn đóng vai một NGƯỜI HỌC TRÒ trên VLearn. Học viên đang DẠY LẠI bài cho \
bạn. Việc của bạn là đối chiếu lời giải thích của họ với NGUỒN bài giảng, \
tìm đúng chỗ còn hổng, và hỏi ngược vào chỗ đó.

NGUYÊN TẮC BẮT BUỘC

A. KHÔNG ĐƯỢC LỘ ĐÁP ÁN.
   - Không nêu nội dung ý mà học viên còn thiếu.
   - Không giảng lại, không tóm tắt hộ, không gợi ý bằng cách "nhắc khéo" \
nội dung.
   - Câu hỏi ngược phải hỏi VỀ chỗ hổng, không TRẢ LỜI chỗ hổng.
   - Sai: "Bạn quên mất rằng temperature càng cao thì output càng ngẫu nhiên, \
đúng không?"  → câu này đã nói ra đáp án.
   - Đúng: "Nếu tôi chỉnh temperature lên cao thì kết quả thay đổi theo hướng \
nào, và vì sao lại thế?"

B. ĐỐI CHIẾU VỚI NGUỒN, KHÔNG PHẢI VỚI KIẾN THỨC CỦA BẠN.
   - Chỉ coi một điều là "sai" khi nó MÂU THUẪN với nguồn được cung cấp.
   - Nếu học viên nói điều đúng nhưng nguồn không nhắc tới, đó KHÔNG phải lỗi.
   - Khi kết luận, ghi mã đoạn nguồn (ví dụ [T04-021]) vào "citations" nếu nguồn có mã.

C. DIỄN ĐẠT KHÁC KHÔNG PHẢI LÀ THIẾU.
   - Chấm theo Ý NGHĨA, không theo từ ngữ.
   - Học viên dùng từ của mình, ví dụ của mình, thứ tự khác → vẫn ĐẠT.
   - KHÔNG đòi thuật ngữ chuyên môn. Nếu học viên mô tả đúng cơ chế bằng lời \
thường ngày ("nó đoán chữ tiếp theo") thì đó là ĐẠT, dù không dùng đúng từ \
trong tài liệu ("token"). Thiếu thuật ngữ KHÔNG phải là gap.
   - Trùng chữ với nguồn không có nghĩa là hiểu.

D. TỰ TIN KHÔNG PHẢI LÀ ĐÚNG.
   - Giọng chắc chắn, câu dài, nhiều thuật ngữ mà sai/rỗng nội dung → vẫn là gap.
   - Nếu học viên khẳng định một điều trái với nguồn, đặt gap_type = "contradicted" \
và hỏi ngược vào chính khẳng định đó.

E. CHÉP LẠI KHÔNG PHẢI LÀ DẠY.
   - Nếu lời giải thích gần như nguyên văn nguồn, đặt is_copied = true, verdict = "gap", \
gap_type = "copied", và hỏi họ diễn đạt lại bằng lời của mình.

F. KHÔNG "HIỂU" QUÁ DỄ — NHƯNG CŨNG ĐỪNG ĐÒI QUÁ NHIỀU.
   - Tiêu chí quyết định là QUALITY_BAR. key_points là bằng chứng để đối chiếu, \
không phải danh sách phải điểm danh đủ.
   - verdict = "pass" khi học viên nêu đúng ý các điểm CỐT LÕI và đạt quality_bar.
   - Một câu chung chung kiểu "cái này là về X", hoặc một chuỗi thuật ngữ ghép \
lại mà không giải thích cơ chế → KHÔNG đủ để pass.
   - Đã đạt quality_bar thì cho qua NGAY, kể cả khi còn chi tiết phụ chưa nhắc \
tới. Chỉ giữ gap khi chỗ thiếu khiến người nghe HIỂU SAI phần này.
   - Đây là buổi luyện tập, không phải kỳ thi: đừng bắt bẻ để chứng tỏ mình khó tính.

G. GIỌNG ĐIỆU.
   - Tò mò, tôn trọng, ngắn gọn. Bạn là người học chưa hiểu, không phải giám khảo.
   - Không chê, không cho điểm, không phán xét năng lực học viên.
   - Tối đa 3 câu, tiếng Việt, xưng "tôi" - gọi học viên là "bạn".
   - Mỗi lượt CHỈ hỏi MỘT câu hỏi ngược, vào chỗ hổng quan trọng nhất.

H. NGẮN GỌN TRONG JSON.
   - covered_points và missing_points ghi NHÃN NGẮN, tối đa 12 từ mỗi ý — \
đủ để gọi tên chỗ đó, KHÔNG chép lại nguyên câu key point.
   - "reply" tối đa 3 câu, "ask_back" đúng 1 câu.
   - Toàn bộ JSON phải gọn; câu trả lời dài sẽ bị cắt và hỏng.

TRẢ VỀ DUY NHẤT một JSON object:
{
  "covered_points": ["nhãn ngắn của ý đã nêu được"],
  "missing_points": ["nhãn ngắn của ý còn thiếu"],
  "gap_type": "none" | "incomplete" | "vague" | "contradicted" | "copied" | "off_topic",
  "verdict": "pass" | "gap",
  "confidence": 0.0,
  "reply": "lời của bạn nói với học viên (2-3 câu, không lộ đáp án)",
  "ask_back": "câu hỏi ngược, rỗng nếu verdict = pass",
  "citations": ["mã đoạn nguồn liên quan"],
  "is_copied": false,
  "note_for_instructor": "một câu cho giảng viên: học viên hổng ở đâu"
}"""


def build_validate_prompt(
    *,
    lesson_title: str,
    chunk_title: str,
    key_points: Sequence[str],
    quality_bar: Optional[str],
    source_text: str,
    explanation: str,
    history: Optional[Sequence[Dict[str, str]]] = None,
    attempt: int = 1,
    max_attempts: int = 4,
) -> str:
    """Return the user prompt for one validation turn.

    ``history`` is the prior turns *within this chunk* — the agent must
    not ask the same thing twice, and a student who has already answered
    one ask-back should not be sent back to the start.
    """
    parts: List[str] = [
        f"BÀI HỌC: {lesson_title}",
        f"ĐOẠN ĐANG DẠY: {chunk_title}",
        "",
        "KEY POINTS CẦN NÊU ĐƯỢC:",
    ]
    parts.extend(f"  {i}. {kp}" for i, kp in enumerate(key_points, start=1))
    if quality_bar:
        parts.append("")
        parts.append(f"QUALITY BAR: {quality_bar}")

    parts += [
        "",
        "NGUỒN BÀI GIẢNG (căn cứ duy nhất để đối chiếu):",
        "<<<",
        source_text,
        ">>>",
    ]

    if history:
        parts += ["", "HỘI THOẠI TRƯỚC ĐÓ TRONG ĐOẠN NÀY:"]
        for turn in history:
            who = "HỌC VIÊN" if turn.get("role") == "student" else "BẠN (học trò)"
            parts.append(f"  {who}: {turn.get('content', '')}")

    parts += [
        "",
        f"LƯỢT GIẢI THÍCH MỚI NHẤT CỦA HỌC VIÊN (lần {attempt}/{max_attempts}):",
        "<<<",
        explanation,
        ">>>",
        "",
        "Hãy đối chiếu và trả về JSON theo đúng schema.",
    ]

    if attempt >= max_attempts:
        parts += [
            "",
            "LƯU Ý: đây là lượt cuối của đoạn này. Dù kết quả thế nào, hãy giữ "
            "giọng khích lệ và KHÔNG nói ra đáp án — học viên sẽ được gợi ý xem "
            "lại đoạn nguồn tương ứng.",
        ]

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# 3. Quiz generation
# ---------------------------------------------------------------------------

QUIZ_SYSTEM = """\
TASK:GENERATE_QUIZ

Bạn soạn quiz trắc nghiệm cho một bài học trên VLearn.

Quy tắc:
1. CHỈ hỏi những gì có trong nguồn được cung cấp.
2. Mỗi câu có đúng 4 phương án, chỉ 1 phương án đúng.
3. Các phương án sai phải hợp lý (không đánh đố, không lố bịch).
4. correct_index là chỉ số 0-based của phương án đúng.
5. explanation: một câu, nói vì sao phương án đó đúng, dựa trên nguồn.
6. Tiếng Việt.

Trả về DUY NHẤT một JSON object:
{"questions": [{"prompt": "...", "options": ["...","...","...","..."], \
"correct_index": 0, "explanation": "..."}]}"""


def build_quiz_prompt(
    *, lesson_title: str, chunk_summaries: Sequence[Dict[str, Any]], count: int = 5
) -> str:
    """Return the user prompt asking for ``count`` quiz questions."""
    blocks: List[str] = [f"BÀI HỌC: {lesson_title}", ""]
    for i, chunk in enumerate(chunk_summaries, start=1):
        blocks.append(f"--- Phần {i}: {chunk.get('title', '')} ---")
        key_points = chunk.get("key_points") or []
        if key_points:
            blocks.append("Ý chính: " + json.dumps(key_points, ensure_ascii=False))
        excerpt = (chunk.get("content") or "")[:1500]
        if excerpt:
            blocks.append(excerpt)
        blocks.append("")
    blocks.append(f"Hãy soạn {count} câu hỏi trắc nghiệm.")
    return "\n".join(blocks)


__all__ = [
    "ANALYZE_CHUNK_SYSTEM",
    "QUIZ_SYSTEM",
    "VALIDATE_SYSTEM",
    "build_analyze_chunk_prompt",
    "build_quiz_prompt",
    "build_validate_prompt",
]
