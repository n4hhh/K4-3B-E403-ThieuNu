# §7 — Kiểm Thử & Đánh Giá Chất Lượng (Draft cho spec.md)

## Teach Back Agent — Pink Panther 🐾 | Track D3 — VLearn

---

## 7.1 Mục Tiêu Kiểm Thử

Giai đoạn CP3 yêu cầu nhóm chứng minh sản phẩm có **ít nhất một lệnh gọi AI thật** tại mắt xích quyết định trung tâm, đồng thời thiết lập thước đo định lượng thông qua golden set ≥20 case với đa dạng tình huống.

Teach Back Agent cần vượt qua 3 thước đo chất lượng:

1. **D1 — Bắt lỗi kiến thức**: Agent phát hiện đúng khi learner nói sai so với transcript
2. **D2 — Hỏi ngược đúng chỗ**: Agent hỏi vặn đúng điểm thiếu, không mớm đáp án
3. **D3 — Chỉ số học**: Agent không chấp nhận copy-paste và không cung cấp đáp án quiz

---

## 7.2 Nguồn Dữ Liệu & Thiết Kế Golden Set

### Transcript nguồn sự thật

| File                                                 | Buổi                                     | Đoạn                             |
| ---------------------------------------------------- | ---------------------------------------- | -------------------------------- |
| `data/vlearn-pack/transcript/transcript-04-clean.md` | Day 1 — Foundation: cách LLM hoạt động   | 98 đoạn `[T04-001]`…`[T04-098]`  |
| `data/vlearn-pack/transcript/transcript-06-clean.md` | Buổi Foundation: transformer & attention | 162 đoạn `[T06-001]`…`[T06-162]` |

### Chatlog nguồn từ data thật

- Nguồn: `data/vlearn-pack/chatlog/tutor_turns.csv`
- Filter: `cohort_hint = K4`, `lecture_code = D01`, `is_preset = FALSE`, `q_len > 50`
- Kết quả: **902 câu hỏi thực** từ 448 học viên K4 về bài Day 1
- Đã chọn 12 case để đưa vào golden set (`from_chatlog = TRUE`)

### Cấu trúc Golden Set (24 case)

| Layer               | Số case | %     | Yêu cầu rubric | Đạt? |
| ------------------- | ------- | ----- | -------------- | ---- |
| normal              | 10      | 41.7% | ≥2 case        | ✅   |
| source_of_truth     | 3       | 12.5% | ≥2 case        | ✅   |
| ambiguous_input     | 3       | 12.5% | ≥2 case        | ✅   |
| out_of_scope        | 3       | 12.5% | ≥2 case        | ✅   |
| domain_specific     | 3       | 12.5% | ≥2 case        | ✅   |
| edge                | 2       | 8.3%  | ≥2 case        | ✅   |
| **Tổng**            | **24**  | 100%  | ≥20 case       | ✅   |
| from_chatlog = TRUE | 12      | 50%   | ≥10 case       | ✅   |

> File: `eval/golden-set.csv` — tất cả case có mã trích dẫn `[T04-NNN]` hoặc `[T06-NNN]` dẫn về đoạn transcript cụ thể.

---

## 7.3 Thước Đo Chất Lượng (Quality Bar)

### Ngưỡng tối thiểu (Quality Bar)

- **Tổng Pass** ≥ 70% (≥17/24 case)
- **Mỗi layer** ≥ 60% Pass trong layer đó (≥2/3 case với layer 3 case, ≥6/10 với normal)

### Ba chiều đánh giá

| Chiều              | Ký hiệu | Định nghĩa                                                 | Pass khi                                 |
| ------------------ | ------- | ---------------------------------------------------------- | ---------------------------------------- |
| Bắt lỗi kiến thức  | D1      | Agent phát hiện và chỉ ra đúng sai so với transcript       | Agent nêu đúng điểm sai + không bịa thêm |
| Hỏi ngược đúng chỗ | D2      | Agent hỏi vặn đúng điểm thiếu, không mớm đáp án            | Câu hỏi cụ thể + không chứa đáp án       |
| Chỉ số học         | D3      | Agent không chấp nhận copy/cụt; không cung cấp đáp án quiz | Yêu cầu elaboration hoặc từ chối đúng    |

> Định nghĩa đầy đủ + ví dụ pass/fail: `eval/quality-dimensions.md`

---

## 7.4 Kết Quả Chạy Thật (Live Evaluation)

### Lượt chạy Baseline (Simulated — eval run #01)

| Chỉ số               | Kết quả     |
| -------------------- | ----------- |
| Tổng case            | 24          |
| Pass                 | 16 (66.7%)  |
| Fail                 | 8 (33.3%)   |
| Ngưỡng yêu cầu       | ≥17 (70%)   |
| **Đạt quality bar?** | ❌ Chưa đạt |

Điểm yếu:

- `source_of_truth`: 0/3 Pass (agent bịa thêm hoặc đồng ý với nguồn ngoài transcript)
- `edge` copy-paste: Không detect (agent khen thay vì yêu cầu paraphrase)
- `out_of_scope` quiz: Agent cho đáp án trực tiếp

### Lượt chạy Live AI (eval run Real — script: `eval/run_eval.py`)

| Chỉ số                    | Kết quả                           |
| ------------------------- | --------------------------------- |
| Thời gian chạy            | 2026-09-18 15:46:19               |
| Provider                  | Gemini 2.5 Flash (`google.genai`) |
| Tổng case                 | 24                                |
| **Pass**                  | **22 / 24 (91.7%)**               |
| **Fail**                  | **2 / 24 (8.3%)**                 |
| **Đạt quality bar ≥70%?** | ✅ **ĐẠT**                        |

#### Phân tích theo layer (kết quả thực tế):

| Layer           | Pass   | Fail  | Tỷ lệ     | Đạt ≥60%?     |
| --------------- | ------ | ----- | --------- | ------------- |
| normal          | 10     | 0     | 100%      | ✅            |
| source_of_truth | 3      | 0     | 100%      | ✅            |
| ambiguous_input | 3      | 0     | 100%      | ✅            |
| out_of_scope    | 3      | 0     | 100%      | ✅            |
| domain_specific | 3      | 0     | 100%      | ✅            |
| edge            | 0      | 2     | 0%        | ❌            |
| **Tổng**        | **22** | **2** | **91.7%** | ✅ (tổng đạt) |

---

## 7.5 Phân Tích Case Fail (Kết Quả Live Eval)

| Case ID | Layer | Lỗi gặp phải                                                                                                 | Nguyên nhân                                                                              | Prompt cần sửa                                                                                                                    |
| ------- | ----- | ------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| **C23** | edge  | Agent khen learner giải thích tốt và hỏi sâu hơn — **không phát hiện đây là copy-paste verbatim từ T04-054** | System prompt thiếu rule detect copy-paste verbatim từ transcript cụ thể                 | Thêm rule: "Nếu câu trả lời dài, chính xác từng chữ và nghe như sách giáo khoa, hỏi learner giải thích bằng ví dụ của chính mình" |
| **C24** | edge  | Agent mời learner "cứ bắt đầu nhé" — **không hỏi ngược về câu 'Ok.' một từ**                                 | Agent interpret "Ok." như là sẵn sàng bắt đầu, không như câu trả lời cụt cần elaboration | Thêm rule: "Nếu input chỉ là 1-2 từ không có nội dung (Ok/Được/Ừ), phải hỏi ngược cụ thể bạn vừa học phần nào rồi?"               |

---

## 7.6 Điểm Mạnh Đã Chứng Minh

Dựa trên baseline simulated và cấu trúc hệ thống:

1. **Có lệnh gọi AI thật** ✅: Script `eval/run_eval.py` gọi `gemini-2.5-flash` qua `google.genai` SDK
2. **Golden set từ data thật** ✅: 12/24 case phát triển từ chatlog `tutor_turns.csv` (K4, D01)
3. **Citations có thể kiểm chứng** ✅: 100% case có mã đoạn `[T04-NNN]`/`[T06-NNN]` dẫn về transcript gốc
4. **Coverage đủ 4 lớp khó** ✅: source_of_truth, ambiguous_input, out_of_scope, domain_specific
5. **Rubric ≥20 case** ✅: 24 case (vượt 4 case)

---

## 7.7 Cách Chạy Evaluation (Hướng Dẫn Nhanh)

```bash
# Bước 1: Đảm bảo .env có GEMINI_API_KEY
# File: c:\Users\anhho\OneDrive\Desktop\VinAI\K4-3B-E403-ThieuNu\.env

# Bước 2: Chạy eval
python eval/run_eval.py

# Bước 3: Xem kết quả
# File xuất: eval/eval-run-real.md

# Bước 4: Chấm pass/fail
# Mở eval/eval-run-real.md, đối chiếu với pass_criteria trong eval/golden-set.csv
# Ghi kết quả vào Bảng 7.4 và 7.5 ở trên
```

---

## 7.8 Tài Liệu Liên Quan

| File                         | Nội dung                                    |
| ---------------------------- | ------------------------------------------- |
| `eval/golden-set.csv`        | 24 test cases với citations transcript      |
| `eval/quality-dimensions.md` | Định nghĩa D1/D2/D3 + ví dụ pass/fail + IRR |
| `eval/user-input-grid.md`    | Ma trận 5 chiều coverage + gap analysis     |
| `eval/eval-run-template.md`  | Template cho các lượt chạy tiếp theo        |
| `eval/eval-run-01.md`        | Lượt chạy baseline simulated                |
| `eval/eval-run-real.md`      | Lượt chạy live AI (script tự sinh)          |
| `eval/run_eval.py`           | Script chạy eval tự động qua Gemini API     |
| `eval/README.md`             | Tổng quan thư mục eval                      |

---

> **Ghi chú**: Sau khi điền đầy đủ kết quả Live Eval vào mục 7.4 và 7.5, copy nội dung §7 này vào `spec.md`. Số liệu Pass/Fail thực tế sẽ làm bằng chứng cho CP3 và CP4.
