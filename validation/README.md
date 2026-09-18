
## Tình trạng file này

> **Tất cả log trong folder `validation/` được TẠO MÔ PHỎNG bởi nhóm E403** do hết thời gian 39h hackathon không kịp mời user thật.
>
> - Không có user thật nào ngồi dùng thử trong 10 phút.
> - Không có observation ghi tay theo Mom Test.
> - 2 file log bên dưới là **nhóm tự đóng vai** 2 persona (Tuấn + Hà) để mô tả cách họ *sẽ* phản ứng dựa trên persona đã khai trong `spec.md` §8.

## Vì sao vẫn để file ở đây?

1. **Không giấu** — Rubric CP5 ghi rõ: *"Nhóm được phép tự khai chưa hoàn thiện mà không bị trừ; giấu mới bị trừ."* Nhóm chọn trung thực hơn là để trống.
2. **Tài liệu thiết kế nghiên cứu** — Mô tả cho thấy nhóm *đã nghĩ tới* cách phỏng vấn user (Mom Test / Sean Ellis Disappointment Test) và biết phải đo gì, dù chưa có điều kiện chạy.
3. **Có thể thay bằng log thật** — Format bảng, cột và câu hỏi đã chuẩn hóa; nếu sau hackathon có điều kiện mời user, có thể điền vào cùng khung.

## Cách phân biệt file mô phỏng vs file thật

| Đặc điểm | File MÔ PHỎNG (hiện tại) | File THẬT (kỳ vọng sau này) |
|---|---|---|
| Tiêu đề file | Có prefix `[SIMULATED]` | Bỏ prefix |
| Cột timestamp | Format kiểu `T+3:24` | Có ngày giờ thật (`2026-09-XX HH:MM`) |
| Quote nguyên văn | "Đại diện cho persona" | Lời user thật nói |
| Observation | Nhóm dự đoán dựa trên persona | Người quan sát thật ghi |

## Bài học rút ra sau khi mô phỏng

- Khung phỏng vấn Mom Test (câu hỏi mở, không leading) đã sẵn sàng để dùng lại.
- 2 persona được chọn đủ đối lập (Tuấn = mới học AI, Hà = có nền lập trình) — phù hợp để test persona của Pink Panther ở 2 thái cực.
- Khi có điều kiện, cần **2 người quan sát độc lập** (1 ghi log + 1 quay video màn hình) để bắt cả micro-expression.

## Nếu giám khảo đặt câu hỏi về validation

Trả lời thẳng thắn:
> *"Nhóm chưa kịp mời user thật chạy trong 10 phút vì còn ưu tiên sửa 2 edge case C23/C24 và đóng băng Quality Bar trước hạn 21:00 ngày 18/9. File log trong `validation/` là mô phỏng, có ghi rõ `[SIMULATED]` ở tiêu đề và README ở đầu folder. Theo rubric 'giấu mới bị trừ', nhóm chọn minh bạch."*
