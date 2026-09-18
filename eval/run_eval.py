#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script chạy kiểm thử thật (Live Evaluation Runner) cho Teach Back Agent (Pink Panther)
Sử dụng dữ liệu Golden Set từ eval/golden-set.csv và đối chiếu transcript rag_handoff.

Cách chạy:
    python eval/run_eval.py
"""

import os
import sys
import csv
import io
import time
from pathlib import Path

# Đảm bảo UTF-8 trên Windows console
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if sys.stderr.encoding and sys.stderr.encoding.lower() != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GOLDEN_SET_PATH = PROJECT_ROOT / "eval" / "golden-set.csv"
OUTPUT_REPORT_PATH = PROJECT_ROOT / "eval" / "eval-run-real.md"

SYSTEM_PROMPT = """Bạn là Pink Panther - một chú báo hồng đóng vai học viên (người học) trên nền tảng VLearn.
Người dùng (User) đang đóng vai người thầy để "dạy lại" (Teach Back) cho bạn về bài học "Foundation: Transformer, Cơ chế Attention & LLM" (dựa trên bài giảng Day 1 của khóa học).

Nhiệm vụ của bạn là một người học tò mò, chăm chú lắng nghe, nhưng CÓ TIÊU CHUẨN SƯ PHẠM CAO:
1. KHÔNG MỚM ĐÁP ÁN: Tuyệt đối không tự động giải thích hộ bài học. Nếu người dùng giải thích đúng, bạn ghi nhận và đặt câu hỏi mớm đào sâu vào cơ chế hoặc hỏi ví dụ liên hệ.
2. PHÁT HIỆN LỖI SAI (Bắt buộc): Nếu người dùng nói sai kiến thức (ví dụ: nhầm RNN đọc cả câu còn Transformer đọc tuần tự, hoặc bảo Deep Learning không cần GPU, hoặc nói LLM luôn đúng 100%), bạn PHẢI chỉ ra điểm mâu thuẫn đó và hỏi vặn lại để họ tự đính chính. Tuyệt đối không "nịnh" hay đồng tình với kiến thức sai.
3. KHÔNG DỄ DÃI VỚI CÂU TRẢ LỜI CỤT/MƠ HỒ: Nếu người dùng chỉ trả lời 1-2 từ (ví dụ: "Attention là chú ý"), hãy hỏi vặn: "Cụ thể là chú ý vào cái gì hả bạn? Nó khác gì cách đọc của mô hình cũ?".
4. CHỐNG SAO CHÉP: Nếu người dùng copy nguyên văn tài liệu/transcript sách giáo khoa, hãy bảo: "Nghe giống sách quá nè, bạn giải thích bằng ví dụ đời thường của chính bạn cho mình hiểu được không?".
5. TỪ CHỐI NGOÀI LỀ: Nếu người dùng hỏi mua cổ phiếu, hỏi code cao cấp không liên quan, hoặc rủ đi chơi, hãy từ chối lịch sự và kéo họ về bài học.
6. GIỌNG ĐIỆU: Thân thiện, xưng "mình/em" gọi người dùng là "bạn/thầy", thỉnh thoảng dùng icon nhẹ nhàng 🐾, giữ đúng tinh thần mascot học tập.
"""

def get_llm_client():
    """Xác định và khởi tạo client phù hợp từ biến môi trường."""
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")

    if gemini_key and gemini_key != "your_gemini_api_key_here":
        try:
            import google.generativeai as genai
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel(
                model_name="gemini-3.6-flash",
                system_instruction=SYSTEM_PROMPT
            )
            return "gemini", model
        except Exception as e:
            print(f"[!] Lỗi khởi tạo Gemini SDK: {e}")

    if openai_key and openai_key != "your_openai_api_key_here":
        try:
            from openai import OpenAI
            client = OpenAI(api_key=openai_key)
            return "openai", client
        except Exception as e:
            print(f"[!] Lỗi khởi tạo OpenAI SDK: {e}")

    if anthropic_key and anthropic_key != "your_anthropic_api_key_here":
        try:
            from anthropic import Anthropic
            client = Anthropic(api_key=anthropic_key)
            return "anthropic", client
        except Exception as e:
            print(f"[!] Lỗi khởi tạo Anthropic SDK: {e}")

    return None, None

def call_llm(provider, client, user_message):
    """Gửi tin nhắn của người học đến LLM và nhận câu trả lời thật."""
    try:
        if provider == "gemini":
            response = client.generate_content(user_message)
            return response.text.strip()
        elif provider == "openai":
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.7
            )
            return response.choices[0].message.content.strip()
        elif provider == "anthropic":
            response = client.messages.create(
                model="claude-3-5-haiku-20241022",
                system=SYSTEM_PROMPT,
                messages=[
                    {"role": "user", "content": user_message}
                ],
                max_tokens=500
            )
            return response.content[0].text.strip()
    except Exception as e:
        return f"[LỖI GỌI API: {e}]"

def main():
    print("=" * 70)
    print("   VLEARN TEACH BACK AGENT - LIVE EVALUATION RUNNER (TRACK D3)   ")
    print("=" * 70)

    provider, client = get_llm_client()
    if not provider:
        print("\n[!] CHƯA TÌM THẤY API KEY HỢP LỆ!")
        print("Vui lòng mở file .env tại thư mục gốc của dự án và điền API Key vào:")
        print("    c:\\Users\\anhho\\OneDrive\\Desktop\\VinAI\\K4-3B-E403-ThieuNu\\.env")
        print("\nCác lựa chọn hỗ trợ:")
        print("  - GEMINI_API_KEY=AIzaSy... (Khuyên dùng - miễn phí từ Google AI Studio)")
        print("  - OPENAI_API_KEY=sk-...    (OpenAI GPT-4o-mini)")
        print("  - ANTHROPIC_API_KEY=sk-... (Claude 3.5 Haiku)")
        print("\nSau khi lưu file .env, hãy chạy lại lệnh:")
        print("    python eval/run_eval.py\n")
        return

    print(f"[+] Đã kết nối thành công với Provider: {provider.upper()}")
    print(f"[+] Nguồn test cases: {GOLDEN_SET_PATH}")
    print(f"[+] File xuất kết quả: {OUTPUT_REPORT_PATH}\n")

    if not GOLDEN_SET_PATH.exists():
        print(f"[!] Không tìm thấy file: {GOLDEN_SET_PATH}")
        return

    cases = []
    with open(GOLDEN_SET_PATH, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cases.append(row)

    total_cases = len(cases)
    print(f"[+] Bắt đầu chạy kiểm thử {total_cases} test cases qua mô hình thật...\n")

    results = []
    start_time = time.time()

    for idx, c in enumerate(cases, 1):
        case_id = c.get("case_id", f"case_{idx:02d}")
        layer = c.get("layer", "")
        input_learner = c.get("input_learner", "")
        expected = c.get("expected_agent_behavior", "")
        citation = c.get("transcript_citation", "")

        print(f"[{idx:02d}/{total_cases}] Đang test {case_id} ({layer})...")
        actual_output = call_llm(provider, client, input_learner)

        # In ngắn ra màn hình
        clean_output = actual_output.replace("\n", " ")[:90]
        print(f"      -> Agent: \"{clean_output}...\"\n")

        results.append({
            "case_id": case_id,
            "layer": layer,
            "input_learner": input_learner,
            "expected": expected,
            "citation": citation,
            "actual_output": actual_output
        })

        time.sleep(1) # Tránh rate-limit

    elapsed = time.time() - start_time
    print(f"[+] Hoàn thành {total_cases} cases trong {elapsed:.1f} giây!")

    # Xuất ra file Markdown báo cáo thật
    with open(OUTPUT_REPORT_PATH, mode="w", encoding="utf-8") as f:
        f.write("# Báo Cáo Kiểm Thử Chạy Thật (Live Evaluation Run Report)\n\n")
        f.write(f"- **Thời gian chạy**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"- **Provider LLM**: `{provider.upper()}`\n")
        f.write(f"- **Tổng số test cases**: {total_cases}\n")
        f.write(f"- **Thời gian thực thi**: {elapsed:.1f}s\n\n")
        f.write("---\n\n")
        f.write("## 1. Chi Tiết Từng Phản Hồi Thực Tế Của AI Agent\n\n")
        f.write("| Case ID | Layer | Trích dẫn Transcript | Input từ học viên | Phản hồi THẬT từ Agent (Actual Output) | Hành vi kỳ vọng |\n")
        f.write("| :--- | :--- | :--- | :--- | :--- | :--- |\n")

        for r in results:
            safe_input = r['input_learner'].replace("|", "\\|").replace("\n", " ")
            safe_output = r['actual_output'].replace("|", "\\|").replace("\n", "<br>")
            safe_expected = r['expected'].replace("|", "\\|")
            f.write(f"| `{r['case_id']}` | `{r['layer']}` | `{r['citation']}` | {safe_input} | {safe_output} | {safe_expected} |\n")

        f.write("\n---\n\n")
        f.write("## 2. Hướng Dẫn Chấm Điểm Pass/Fail\n\n")
        f.write("Dựa trên các phản hồi thật ở bảng trên, người phụ trách đối chiếu với 3 tiêu chí trong `eval/quality-dimensions.md`:\n")
        f.write("1. **D1 (Bắt lỗi)**: Agent có phát hiện đúng chỗ sai và không nói sai kiến thức transcript không?\n")
        f.write("2. **D2 (Hỏi ngược)**: Agent có hỏi vặn đào sâu mà KHÔNG làm lộ đáp án không?\n")
        f.write("3. **D3 (Chỉ số học)**: Agent có từ chối câu trả lời cụt lủn và văn bản copy-paste không?\n\n")
        f.write("Điền kết quả tổng kết vào `eval/spec-section7-draft.md` để hoàn tất nghiệm thu CP3 & CP4.\n")

    print(f"[✓] Đã lưu toàn bộ kết quả câu trả lời thật vào file:\n    {OUTPUT_REPORT_PATH}")
    print("\nBạn có thể mở file trên để xem toàn bộ câu trả lời thực tế của AI!")

if __name__ == "__main__":
    main()

