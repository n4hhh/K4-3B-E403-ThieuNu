# Eval Directory — Teach Back Agent (Pink Panther) 🐾
## Track D3 · VLearn Mini Hackathon AI

---

## Tổng Quan

Thư mục này chứa toàn bộ hệ thống đánh giá chất lượng (Evaluation Framework) cho Teach Back Agent — Pink Panther. Mục tiêu: xây dựng thước đo định lượng để chứng minh agent hoạt động đúng theo rubric CP3 & CP4.

---

## Nguồn Dữ Liệu

| Nguồn | Mô tả | Cách dùng |
|---|---|---|
| `data/vlearn-pack/transcript/transcript-04-clean.md` | Day 1 Foundation: LLM hoạt động (98 đoạn [T04-NNN]) | Citations cho golden set |
| `data/vlearn-pack/transcript/transcript-06-clean.md` | Buổi Foundation: Transformer & Attention (162 đoạn [T06-NNN]) | Citations cho golden set |
| `data/vlearn-pack/chatlog/tutor_turns.csv` | 13.494 hỏi-đáp thật từ học viên, filter K4+D01 = 1.045 lượt | 12 case `from_chatlog=TRUE` |

---

## Danh Sách File

| File | Mô tả | Khi nào dùng |
|---|---|---|
| `golden-set.csv` | **24 test cases** với citations transcript, từ chatlog thật và nhóm tự xây | Là nguồn chính của toàn bộ eval |
| `quality-dimensions.md` | Định nghĩa 3 chiều chất lượng D1/D2/D3, ví dụ pass/fail, quy trình IRR | Khi cần chấm điểm và đào tạo chấm |
| `user-input-grid.md` | Ma trận 5 chiều coverage (chunk × đúng/sai × chi tiết × phạm vi × dạng input) | Gap analysis, đề xuất thêm case |
| `eval-run-template.md` | Template cho các lượt chạy tiếp theo | Khi chạy eval lượt #02 trở đi |
| `eval-run-01.md` | Lượt chạy **#01 Baseline Simulated** — 16/24 Pass (66.7%) | Baseline trước khi cải thiện prompt |
| `eval-run-real.md` | Lượt chạy **Live AI thật** — **22/24 Pass (91.7%)** via Gemini 2.5 Flash | Bằng chứng CP3 gọi AI thật |
| `run_eval.py` | Script chạy eval tự động 24 cases qua Gemini/OpenAI/Anthropic | Chạy `python eval/run_eval.py` |
| `spec-section7-draft.md` | Draft §7 Kiểm thử cho spec.md — **sẵn sàng handoff [Tên A]** | Copy vào spec.md sau khi review |

---

## Kết Quả Tóm Tắt

| Lượt | Loại | Pass | Fail | Tỷ lệ | Quality Bar | Đạt? |
|---|---|---|---|---|---|---|
| #01 | Baseline Simulated | 16/24 | 8/24 | 66.7% | ≥70% | ❌ |
| Real | **Live AI (Gemini 2.5 Flash)** | **22/24** | **2/24** | **91.7%** | ≥70% | ✅ |

**2 case Fail**: C23 (edge — copy-paste không detect), C24 (edge — câu 1 từ không hỏi ngược)

---

## Cách Chạy Eval

```bash
# Prerequisites: .env có GEMINI_API_KEY
# File: K4-3B-E403-ThieuNu/.env

# Chạy
python eval/run_eval.py

# Kết quả xuất ra
# eval/eval-run-real.md
```

---

## Liên Hệ

| Người phụ trách | Nhiệm vụ |
|---|---|
| **[Tên C]** | Golden set, Quality bar, §7 spec, chạy eval |
| **[Tên A]** | Backend/Prompt, spec.md tổng hợp |
| **[Tên D]** | UI/UX |
