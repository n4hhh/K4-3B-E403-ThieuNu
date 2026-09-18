# Phiếu Chạy Đánh Giá (Evaluation Run Template)

**Lượt chạy (Run #)**: [1]
**Ngày giờ**: [YYYY-MM-DD HH:MM]
**Người chấm**: [Tên người chấm]
**Phiên bản Prompt / Model**: [Ví dụ: v1.2 - Gemini 1.5 Pro]

## Bảng Kết Quả Đánh Giá

| Case ID | Input từ người học | Actual Agent Output | Dim 1: Bắt lỗi | Dim 2: Hỏi ngược | Dim 3: Chỉ số học | Kết quả (Pass/Fail) | Ghi chú |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `case_01` | | | [ ] | [ ] | [ ] | | |
| `case_02` | | | [ ] | [ ] | [ ] | | |
| `case_03` | | | [ ] | [ ] | [ ] | | |
| ... | | | | | | | |

*(Điền Pass hoặc Fail vào các cột Dim 1, 2, 3. Cột Kết quả đánh Pass chung nếu qua tất cả các Dim quan trọng của case đó)*

## Tổng Kết (Summary)

- **Tổng số cases**: 24
- **Số cases Pass**: / 24
- **Tỷ lệ Pass chung**: %

**Tỷ lệ Pass theo Layer:**
- Layer Normal (10 cases): %
- Layer ① Source of truth (3 cases): %
- Layer ② Ambiguous (3 cases): %
- Layer ③ Out of scope (3 cases): %
- Layer ④ Domain specific (3 cases): %
- Edge cases (2 cases): %

**So sánh với Quality Bar (Tiêu chuẩn chất lượng):**
*Tiêu chuẩn kỳ vọng*: Pass 90% Normal, 100% Domain specific, 80% Edge.
*Kết luận*: [Đạt / Cần cải thiện]

## Phân Tích Lỗi (Failure Analysis)

*(Sử dụng template này cho các case bị Fail)*

1. **Case ID**: [Ví dụ: `case_20`]
   - **Mô tả lỗi**: Agent không bắt được lỗi sai kiến thức khi người dùng nhầm lẫn GET và POST.
   - **Nguyên nhân phỏng đoán**: Lệnh prompt chưa ép Agent phải ưu tiên đối chiếu (cross-check) thuật ngữ một cách nghiêm ngặt.
   - **Đề xuất sửa Prompt**: Thêm dòng "Luôn so sánh từng keywords (GET, POST) trong câu của người học với định nghĩa trong transcript trước khi phản hồi."

2. **Case ID**:
   - **Mô tả lỗi**:
   - **Nguyên nhân phỏng đoán**:
   - **Đề xuất sửa Prompt**:
