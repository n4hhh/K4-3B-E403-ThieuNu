# Thư Mục Đánh Giá (Evaluation) — Track D3 Teach Back Agent

Thư mục này chứa toàn bộ hệ thống đánh giá chất lượng (Evaluation Framework) do **[Tên C]** phụ trách, phục vụ nghiệm thu các mốc **Checkpoint 3 (16:00 18/9)** và **Checkpoint 4 (21:00 18/9)** của Mini Hackathon AI.

Toàn bộ kịch bản kiểm thử, tiêu chí và dữ liệu đối chiếu được xây dựng trực tiếp từ **dữ liệu bài giảng thật của khóa học** trong `rag_handoff/sources/transcripts/` (`transcript-04-clean.md` & `transcript-06-clean.md` — Chủ đề Foundation: Transformer & Cơ chế Attention).

---

## 📂 Danh Mục Các File

| Tên File                                                 | Vai trò & Nội dung                                                                                                                                                              | Phục vụ mốc nào |
| :------------------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | :-------------: |
| **[`golden-set.csv`](./golden-set.csv)**                 | Bộ 24 test cases chuẩn với đầy đủ mã trích dẫn transcript `[T04-NNN]`, `[T06-NNN]`, phân bổ theo 4 lớp chỗ khó và các edge cases gian lận/sáo rỗng.                             |  **CP3 & CP4**  |
| **[`user-input-grid.md`](./user-input-grid.md)**         | Ma trận 5 chiều đầu vào từ người học, thể hiện độ bao phủ (coverage) và các điểm khuyết (gaps) cần bổ sung.                                                                     |     **CP4**     |
| **[`quality-dimensions.md`](./quality-dimensions.md)**   | Định nghĩa 3 chiều chất lượng (D1: Bắt lỗi, D2: Hỏi ngược, D3: Chỉ số học) có thể kiểm chứng được, kèm hướng dẫn đo độ tin cậy người chấm (IRR).                                |     **CP4**     |
| **[`eval-run-01.md`](./eval-run-01.md)**                 | **Báo cáo kết quả chạy kiểm thử Lượt 1** (16/24 Pass = 66.7%), phân tích lỗi chi tiết (Sycophancy ở case_20, mớm đáp án ở case_14, gian lận ở case_23) và giải pháp cho Lượt 2. | **CP3 (16:00)** |
| **[`spec-section7-draft.md`](./spec-section7-draft.md)** | Bản nháp hoàn thiện mục **§7. Kiểm thử** cho file `spec.md`, đã chốt số liệu Quality Bar và bảng tiến độ các lượt chạy.                                                         | **CP4 (21:00)** |
| **[`eval-run-template.md`](./eval-run-template.md)**     | Mẫu phiếu ghi nhận kết quả đánh giá cho các lượt chạy tiếp theo (Lượt 2, Lượt 3).                                                                                               |  **CP4 & CP5**  |

---

## 🚀 Hướng Dẫn Sử Dụng Nhanh

1. **Cho Checkpoint 3 (16:00 18/9)**:
   - Dùng số liệu từ [`eval-run-01.md`](./eval-run-01.md): _Đã chạy 24 case, đạt 16/24 (66.7%), phát hiện lỗi mớm đáp án và lỗi nịnh người dùng ở Layer ④._
2. **Cho Checkpoint 4 (21:00 18/9)**:
   - Copy toàn bộ nội dung từ [`spec-section7-draft.md`](./spec-section7-draft.md) đưa vào file `spec.md` chính của nhóm.
   - Sau khi Tên A cập nhật prompt v2.0, chạy lại 24 case và lưu vào `eval-run-02.md`.
