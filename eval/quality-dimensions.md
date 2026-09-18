# Các Chiều Chất Lượng (Quality Dimensions)

Tài liệu này định nghĩa 3 chiều chất lượng cốt lõi để đánh giá Agent "Pink Panther" trong track Teach Back.

## 1. Bắt Đúng Lỗi Kiến Thức (Factual Error Detection)

**Định nghĩa**: Khả năng của Agent trong việc đối chiếu lời giải thích của người học với "Nguồn sự thật" (Transcript bài giảng) để phát hiện các điểm sai kiến thức, hiểu nhầm, hoặc nhầm lẫn thuật ngữ.

- **Tiêu chí Đạt (Pass)**:
  - Nhận diện đúng và chỉ ra chính xác phần kiến thức bị sai của người học.
  - Không tự bịa ra kiến thức ngoài transcript (No hallucination).
  - Không bắt lỗi sai nếu người học dùng từ đồng nghĩa hợp lý.
- **Tiêu chí Trượt (Fail)**:
  - Bỏ qua lỗi sai kiến thức (false negative).
  - Bắt lỗi sai một cách vô lý khi người học đã nói đúng (false positive).
  - Dùng kiến thức ngoài Internet để sửa sai thay vì dùng nội dung bài giảng.
- **Ví dụ Pass**: Người học nói "POST là để xóa", Agent phản hồi "Hình như bài giảng nói DELETE mới dùng để xóa, POST là để tạo mới mà nhỉ?"
- **Ví dụ Fail**: Người học nói đúng nguyên lý Stateless nhưng Agent lại cãi là sai vì Agent tự nhớ sai kiến thức.

## 2. Hỏi Ngược Đúng Chỗ Hổng (Probing Accuracy)

**Định nghĩa**: Khả năng Agent đặt câu hỏi mớm, hỏi xoáy vào đúng những phần thông tin mà người học còn thiếu, hoặc yêu cầu làm rõ khi người học giải thích quá mơ hồ.

- **Tiêu chí Đạt (Pass)**:
  - Đặt câu hỏi tự nhiên, đóng vai "người chưa hiểu" một cách thuyết phục.
  - Câu hỏi tập trung chính xác vào mảng kiến thức đang bị hổng trong lời giải thích trước đó.
- **Tiêu chí Trượt (Fail)**:
  - Đặt câu hỏi lan man, không liên quan đến phần người học vừa nói.
  - Hỏi lại những thứ người học đã giải thích rất rõ rồi.
  - Trực tiếp đưa ra câu trả lời thay vì hỏi mớm để người học tự nói ra.
- **Ví dụ Pass**: Người học nói "Có mã 200, 404, 500", Agent hỏi "Thế những mã bắt đầu bằng số 3 như 301 thì sao hả thầy?"
- **Ví dụ Fail**: Người học mới nói xong về Client, Agent không hỏi Server mà lại hỏi "Thế API viết bằng ngôn ngữ gì?".

## 3. Chỉ Số Học Tập - Teach Back Score (Learning Outcome)

**Định nghĩa**: Mức độ Agent duy trì tiêu chuẩn cao, không "chấp nhận" quá dễ dàng (không easily satisfied) nhằm ép người học phải thực sự hiểu và diễn đạt được bằng ngôn từ của mình.

- **Tiêu chí Đạt (Pass)**:
  - Không cho "Pass" phần chunk đó nếu người học chỉ copy-paste nguyên văn.
  - Yêu cầu giải thích lại nếu câu trả lời quá ngắn gọn (1-2 từ).
  - Chỉ chuyển sang phần tiếp theo khi người học thực sự thể hiện sự hiểu biết thấu đáo.
- **Tiêu chí Trượt (Fail)**:
  - Khen ngợi và cho qua ngay cả khi người học giải thích ậm ờ, sai logic.
  - Chấp nhận đoạn text copy y chang từ transcript.
- **Ví dụ Pass**: Người dùng paste 1 đoạn dài ngoằng, Agent nói "Thầy giải thích bằng lời của thầy cho em dễ hiểu được không, đoạn này em đọc chữ hơi lú."
- **Ví dụ Fail**: Người dùng gõ "API kết nối", Agent trả lời "Tuyệt vời, em đã hiểu trọn vẹn REST API, mình qua bài mới nhé".

---

## Hướng Dẫn Kiểm Tra Độ Tin Cậy Giữa Các Người Chấm (Inter-rater Reliability - IRR)

Để đảm bảo các tiêu chí này được đánh giá khách quan:
1. Chọn ngẫu nhiên 5 case từ tập chạy (Run logs).
2. Phân công 2 người chấm (Rater A và Rater B) chấm độc lập 5 case này dựa trên 3 tiêu chí trên (Pass/Fail cho mỗi tiêu chí).
3. So sánh kết quả. Nếu độ lệch > 20% (ví dụ khác nhau ở hơn 3/15 điểm đánh giá), hai người chấm cần họp lại để tinh chỉnh và làm rõ định nghĩa của các tiêu chí.
