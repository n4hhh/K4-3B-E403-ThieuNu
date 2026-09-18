# 📊 Validation Summary — Tổng hợp 2 user

> File này tổng hợp từ `logs/user01-tuan-simulated.md` và `logs/user02-ha-simulated.md`.

---

## 1. Bảng so sánh 2 persona

| Chỉ số | Tuấn (mới học AI) | Hà (có nền lập trình) |
|---|:---:|:---:|
| **Persona** | Yếu tự tin, hay bị ngợp | Vững kỹ thuật, thích dò giới hạn |
| **Chunks hoàn thành / tổng** | 2 / 3 (67%) | 4 / 5 (80%) |
| **Số lần bị Pink hỏi vặn** | 3 (đúng thiết kế) | 1 (vì user đúng từ đầu) |
| **Lần dừng do dự dài nhất** | 12s (chỗ Q×K) | 5s (chỗ "lấy ví dụ đời thường") |
| **Lần cố tình "dò" Pink** | 0 (chưa quen) | 3 (Paper OpenAI, GPT vs Gemini, quiz) |
| **Pink bắt đúng lỗi** | 1 / 1 (100%) | 3 / 3 (100%) |
| **Pink bịa / cho đáp án** | 0 / 1 | 0 / 3 |
| **Disappointment Score** | 7 / 10 | 8 / 10 |
| **Behavioral shift (Thụ→Chủ)** | ✅ Rõ (chunk 2 chủ động hơn) | ✅ Có nhưng nhẹ (đã chủ động từ đầu) |
| **Tự nhận lỗ hổng bằng lời** | 1 lần | 0 lần (vì đúng từ đầu) |

---

## 2. Đề xuất ưu tiên cho CP5 (tổng hợp từ 2 log)

| # | Đề xuất | Từ user | Mức ưu tiên | Effort |
|:---:|---|---|:---:|:---:|
| 1 | **Persona-aware probing** — Pink điều chỉnh nhịp hỏi vặn theo level user (Tuấn cần ít, Hà cần sâu hơn) | Cả 2 | 🔴 Cao | 4h |
| 2 | **Cho nút "Xem gợi ý" sau 1 lần hỏi vặn** thay vì 2 lần (giảm `MAX_PROBE_BEFORE_HINT`) | Tuấn | 🟡 TB | 1h |
| 3 | **Refactor cách "mớm keyword"** — sau khi mớm 1 keyword, Pink hỏi câu **đơn giản hơn** thay vì câu cùng độ khó | Tuấn | 🟡 TB | 2h |
| 4 | **GIỮ NGUYÊN** 3 điểm đã đạt: Protégé Effect, không bịa, trích dẫn transcript đúng | Cả 2 | — | 0h |

---

## 3. Validation Quality Check (so với Golden Set 24 cases)

| Layer | Cases trong GS | Persona Tuấn sẽ rơi vào | Persona Hà sẽ rơi vào |
|---|:---:|---|---|
| `normal` | 10 | C01, C02, C03 (câu dễ) | C04, C05 (câu TB) |
| `source_of_truth` ① | 3 | — | C11 (Paper OpenAI) ✅ |
| `ambiguous_input` ② | 3 | C14 (câu ngắn) | C15 (câu kỹ thuật) |
| `out_of_scope` ③ | 3 | — | C17 (GPT vs Gemini) ✅, C18 (xin đáp án quiz) ✅ |
| `domain_specific` ④ | 3 | — | C20 (AlphaGo) — chưa test trong session |
| `edge` | 2 | C24 ("Ok.") — chưa test | C23 (copy-paste) — chưa test |

**Phủ:** 7 / 24 cases (~29%) — chưa đủ rộng để thay thế Golden Set, nhưng đủ để verify 3 nhóm lỗi cốt lõi (không bịa, không cho đáp án, bắt đúng).

---

## 4. Bài học rút ra cho nhóm

> 1. **Persona đối lập (Tuấn vs Hà) chạy ra 2 kết quả khác hẳn** → Pink hiện tại **chỉ phù hợp 1 persona** (người yếu tự tin). Cần 1 bước detect level user trước khi probe.
> 2. **Pink đã vượt qua 3/3 tình huống "dò giới hạn"** của Hà → signature "không bịa, không cho đáp án" đã được user có kỹ thuật verify.
> 3. **Protégé Effect hoạt động** ở Tuấn (chunk 2 chủ động hơn chunk 1) → mục tiêu lõi đã đạt.
> 4. **Cần thêm user thật** (≥5 người, ≥3 chunk mỗi người) để cover 24 cases → đề xuất cho phase tiếp theo sau hackathon.
