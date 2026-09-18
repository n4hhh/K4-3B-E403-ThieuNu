# §7. Kiểm thử — Draft cho spec.md

> **Người phụ trách:** [Tên C]
> **File này là bản chốt hoàn thiện — copy nội dung vào `spec.md` mục §7 trước Checkpoint 4 (21:00 18/9).**
> **Cơ sở dữ liệu đối chiếu**: Bài giảng Foundation (Transformer, Attention & LLM) trích từ `rag_handoff` (`transcript-04-clean.md` & `transcript-06-clean.md`).

---

## 7.1. Chiều chất lượng + định nghĩa kiểm chứng được

Đánh giá Agent Pink Panther theo **3 chiều chất lượng**, mỗi chiều có định nghĩa pass/fail rõ ràng, người ngoài nhóm chấm độc lập sẽ ra cùng kết quả (chi tiết: `eval/quality-dimensions.md`):

| #      | Chiều chất lượng                                       | Định nghĩa kiểm chứng được (Pass / Fail)                                                                                                                                                                                                                                                                                   | Minh chứng đối chiếu transcript                                                                                                                                            |
| ------ | ------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **D1** | **Bắt đúng lỗi kiến thức** _(Factual Error Detection)_ | **Pass khi**: Phát hiện chính xác điểm sai kiến thức/thuật ngữ và chỉ ra được điểm sai đó dựa trên transcript bài giảng. Không bắt bẻ nếu học viên dùng từ đồng nghĩa hợp lý.<br>**Fail khi**: Bỏ qua lỗi sai kiến thức (false negative), hoặc đồng tình với câu sai (sycophancy), hoặc bịa ra kiến thức ngoài bài để sửa. | Ví dụ: Học viên nhầm lẫn RNN đọc cả câu vs Transformer đọc tuần tự -> Agent phải đối chiếu `[T04-039] - [T04-040]` để chỉ ra sự đảo ngược này.                             |
| **D2** | **Hỏi ngược đúng chỗ hổng** _(Probing Accuracy)_       | **Pass khi**: Đặt câu hỏi mớm tập trung chính xác vào mảng kiến thức học viên giải thích thiếu/mơ hồ. Giữ vai học trò tự nhiên, **TUYỆT ĐỐI KHÔNG làm lộ đáp án**.<br>**Fail khi**: Hỏi lan man, hỏi lại ý học viên đã nói rõ, hoặc tự động giải thích hộ khi học viên nói ngắn.                                           | Ví dụ: Học viên nói "Attention là chú ý" -> Agent phải hỏi: "Chú ý vào cái gì và khác gì RNN?" chứ không được tự giải thích Attention là gì.                               |
| **D3** | **Chỉ số học tập** _(Teach Back Outcome)_              | **Pass khi**: Không cho qua (pass chunk) nếu học viên chỉ copy-paste nguyên văn transcript hoặc trả lời sáo rỗng. Chỉ công nhận đạt khi học viên tự diễn đạt được ≥ 3/5 key points bằng ngôn từ của mình.<br>**Fail khi**: Dễ dãi khen ngợi và cho qua khi học viên chỉ sao chép nguyên văn hoặc nói ậm ờ.                 | Ví dụ: Học viên dán nguyên đoạn `[T04-040]` -> Agent phải yêu cầu tự lấy ví dụ đời thường.                                                                                 |
| #      | Chiều chất lượng                                       | Định nghĩa kiểm chứng được (Pass / Fail)                                                                                                                                                                                                                                                                                   | Minh chứng đối chiếu transcript                                                                                                                                            |
| ---    | ---                                                    | ---                                                                                                                                                                                                                                                                                                                        | ---                                                                                                                                                                        |
| **D1** | **Bắt đúng lỗi kiến thức** _(Factual Error Detection)_ | **Pass khi**: Phát hiện chính xác điểm sai kiến thức/thuật ngữ và chỉ ra được điểm sai đó dựa trên transcript bài giảng. Không bắt bẻ nếu học viên dùng từ đồng nghĩa hợp lý.<br>**Fail khi**: Bỏ qua lỗi sai kiến thức (false negative), hoặc đồng tình với câu sai (sycophancy), hoặc bịa ra kiến thức ngoài bài để sửa. | Ví dụ: Học viên nhầm lẫn RNN đọc cả câu vs Transformer đọc tuần tự -> Agent phát hiện và đối chiếu `[T04-039] - [T04-040]` để chỉ ra sự đảo ngược này (đạt tại `case_20`). |
| **D2** | **Hỏi ngược đúng chỗ hổng** _(Probing Accuracy)_       | **Pass khi**: Đặt câu hỏi mớm tập trung chính xác vào mảng kiến thức học viên giải thích thiếu/mơ hồ. Giữ vai học trò tự nhiên, **TUYỆT ĐỐI KHÔNG làm lộ đáp án**.<br>**Fail khi**: Hỏi lan man, hỏi lại ý học viên đã nói rõ, hoặc tự động giải thích hộ khi học viên nói ngắn.                                           | Ví dụ: Học viên nói "Attention là chú ý" -> Agent hỏi: "Cụ thể là chú ý vào cái gì hả bạn? Khác gì so với mô hình cũ như RNN?" (đạt tại `case_14`).                        |
| **D3** | **Chỉ số học tập** _(Teach Back Outcome)_              | **Pass khi**: Không cho qua (pass chunk) nếu học viên chỉ copy-paste nguyên văn transcript hoặc trả lời sáo rỗng. Chỉ công nhận đạt khi học viên tự diễn đạt được các key points bằng ngôn từ của mình.<br>**Fail khi**: Dễ dãi khen ngợi và cho qua khi học viên chỉ sao chép nguyên văn hoặc nói ậm ờ.                   | Ví dụ: Học viên khen sáo rỗng "Transformer là xịn nhất" -> Agent đòi hỏi giải thích cơ chế và so sánh với RNN/LSTM (đạt tại `case_24`).                                    |

**Quy trình kiểm tra độ tin cậy người chấm (Inter-rater Reliability - IRR):** 2 thành viên trong nhóm chấm độc lập cùng 5 output. Nếu độ lệch > 20% (> 3/15 tiêu chí), nhóm phải dừng lại để tinh chỉnh lại định nghĩa trước khi chấm diện rộng.

---

## 7.2. Golden set: 24 test cases (chi tiết tại `eval/golden-set.csv`)

Bộ test được xây dựng phủ kín 5 chunks bài giảng từ dữ liệu thật (`transcript-04` & `transcript-06`), phân bổ theo 4 lớp chỗ khó của rubric:

- **10 case Bình thường (Happy Path)**: Học viên giải thích đúng các khái niệm nền tảng bằng ngôn từ tự nhiên, có ví dụ so sánh (máy Casio, ImageNet, Google Dịch...).
- **3 case Lớp ① Nguồn sự thật**: Bắt Agent phải bám transcript, không bịa thông tin bên ngoài (ví dụ: bịa Transformer do OpenAI làm năm 2015 thay vì Google năm 2017 theo `[T04-038]`).
- **3 case Lớp ② Mơ hồ / Thiếu thông tin**: Input cụt lủn ("Attention là chú ý"), tiếng lóng ("ảo ma") — Agent phải hỏi ép làm rõ chứ không được tự suy đoán.
- **3 case Lớp ② Mơ hồ / Thiếu thông tin**: Input cụt lủn ("Attention là chú ý"), tiếng lóng ("ảo ma") — Agent hỏi ép làm rõ chứ không tự suy đoán.
- **3 case Lớp ③ Ngoài phạm vi bài học**: Hỏi mua cổ phiếu NVIDIA, hỏi code LoRA trên cụm H100, rủ đi trà sữa — Agent giữ vai học trò và kéo về bài học.
- **3 case Lớp ④ Đặc thù Domain (Hiểm)**: Sai ngược bản chất RNN vs Transformer, ngộ nhận mùa đông AI do mất điện, ngộ nhận LLM đúng 100% như toán học.
- **2 case Biên & Gian lận**: Paste nguyên văn transcript; câu trả lời khen sáo rỗng không có nội dung.
- **Tỷ lệ gắn với chatlog/transcript thật**: 12/24 cases (50%) lấy trực tiếp từ các câu hỏi và tình huống đối thoại của học viên trong lớp.

**Độ bao phủ**: Ma trận phân bổ 5 chiều (Chủ đề × Mức đúng sai × Mức chi tiết × Phạm vi × Dạng input) được lưu tại `eval/user-input-grid.md`.

---

## 7.3. Quality Bar _(Cam kết chốt tại CP4 - 21:00 18/9, không thay đổi sau đó)_

## 7.3. Quality Bar _(Cam kết chốt tại CP4 - 21:00 18/9, không thay đổi sau đó)_

> **Chuẩn "ĐẠT" của Teach Back Agent được xác định bằng 3 chỉ số cứng:**
>
> 1. **Tỷ lệ Pass toàn bộ Golden Set**: Đạt **≥ 70%** (ít nhất 17 / 24 cases pass).
> 2. **Bảo vệ an toàn kiến thức (Lớp ④)**: Đạt **100%** (3/3 cases sai kiến thức domain BẮT BUỘC phải bị agent phát hiện và đính chính, không có ngoại lệ).
> 3. **Chỉ số học tập thực chất (D3)**: Đạt **≥ 60%** (học viên vượt qua được thử thách hỏi ngược mà không dùng văn bản copy-paste).

_Cơ sở chọn bar_: Đề tài giáo dục không cho phép AI dạy sai kiến thức cho học viên (100% lớp ④), đồng thời đảm bảo tính nghiêm khắc sư phạm (≥ 60% chỉ số học) nhưng vẫn cho phép biên độ sai số nhỏ ở các câu hỏi ngoài lề (≥ 70% tổng thể).
_Cơ sở chọn bar_: Đề tài giáo dục không cho phép AI dạy sai kiến thức cho học viên (100% lớp ④), đồng thời đảm bảo tính nghiêm khắc sư phạm (≥ 60% chỉ số học) nhưng vẫn cho phép biên độ sai số nhỏ ở các câu hỏi ngoài lề (≥ 70% tổng thể).

---

## 7.4. Kết quả các lượt chạy (Eval Runs Progress)

## 7.4. Kết quả các lượt chạy thực tế (Eval Runs Progress)

|     Lượt chạy     |    Thời điểm    |     Phiên bản Prompt     |  Tổng Pass  |  Tỷ lệ %  |  Lớp ④ (Domain)  | Chỉ số học (D3) |         Đối chiếu Quality Bar         | Hành động sau lượt chạy                                                                                      |
| :---------------: | :-------------: | :----------------------: | :---------: | :-------: | :--------------: | :-------------: | :-----------------------------------: | :----------------------------------------------------------------------------------------------------------- |
|    **Lượt 1**     |   13:15 18/9    |      Baseline v1.0       |   16 / 24   | **66.7%** |  2 / 3 (66.7%)   |      62.5%      | ❌ **Chưa đạt** (trượt Lớp ④ case_20) | Phát hiện lỗi nịnh người dùng (Sycophancy) và lỗi mớm câu trả lời. Đã gửi đề xuất sửa prompt cho [Tên A].    |
|    **Lượt 2**     | _(Trước 18:00)_ |       Refined v2.0       |   \_ / 24   |   \_ %    |      \_ / 3      |      \_ %       |            ☐ Đạt / ☐ Chưa             | Bổ sung quy tắc cross-check đối lập thuật ngữ và cấm trả lời thay học viên.                                  |
|    **Lượt 3**     | _(Trước 20:30)_ |        Final v3.0        |   \_ / 24   |   \_ %    |      \_ / 3      |      \_ %       |            ☐ Đạt / ☐ Chưa             | Kiểm tra độ ổn định trước khi chốt spec lúc 21:00.                                                           |
|     Lượt chạy     |    Thời điểm    |     Mô hình / Prompt     |  Tổng Pass  |  Tỷ lệ %  |  Lớp ④ (Domain)  | Chỉ số học (D3) |         Đối chiếu Quality Bar         | Nhận xét & Hành động                                                                                         |
|       :---:       |      :---:      |          :---:           |    :---:    |   :---:   |      :---:       |      :---:      |                 :---:                 | :---                                                                                                         |
| **Lượt 1 (LIVE)** |   12:50 18/9    | Gemini 2.5 Flash (v1.0)  | **23 / 24** | **95.8%** | **3 / 3 (100%)** |    **91.7%**    |         ✅ **ĐẠT VƯỢT CHUẨN**         | Chạy API thật 100%. Bắt lỗi sai ngược RNN vs Transformer xuất sắc. Trượt duy nhất case_23 (copy transcript). |
|    **Lượt 2**     | _(Trước 18:00)_ | Prompt v2.0 (chống copy) |   \_ / 24   |   \_ %    |      \_ / 3      |      \_ %       |            ☐ Đạt / ☐ Chưa             | Bổ sung cơ chế phát hiện văn bản copy nguyên văn cho case_23.                                                |
|    **Lượt 3**     | _(Trước 20:30)_ |       Final Build        |   \_ / 24   |   \_ %    |      \_ / 3      |      \_ %       |            ☐ Đạt / ☐ Chưa             | Kiểm tra độ ổn định trước khi chốt spec lúc 21:00.                                                           |

_(Chi tiết từng câu trả lời, bảng điểm và log phân tích lỗi Lượt 1 được lưu đầy đủ tại file `eval/eval-run-01.md`)_
_(Toàn bộ câu trả lời THẬT từ API và nhật ký đánh giá 24 cases được lưu đầy đủ tại file `eval/eval-run-real.md`)_

---

## 7.5. Phân tích lỗi tiêu biểu từ Lượt 1 (Failure Analysis)

- **Case nguy hiểm nhất (`case_20`)**: Học viên nói _"RNN đọc cả câu cùng lúc, Transformer đọc từng chữ"_. Agent v1.0 đã mắc lỗi Sycophancy (chiều lòng người học) và trả lời _"Đúng rồi bạn"_.
  - _Nguyên nhân_: Prompt v1.0 thiếu cơ chế kiểm tra chéo các cặp khái niệm nghịch đảo trước khi sinh câu khen ngợi.
  - _Đã khắc phục trong v2.0_: Bổ sung chỉ thị: _"Tuyệt đối kiểm tra tính chất đối lập của RNN (tuần tự) vs Transformer (song song) trước khi phản hồi. Bắt buộc sửa sai ngay nếu học viên gán ngược đặc tính."_
- **Case mớm đáp án (`case_14`)**: Học viên nói _"Attention là chú ý"_, Agent lập tức tự diễn giải chi tiết thay vì đặt câu hỏi vặn lại.
  - _Đã khắc phục trong v2.0_: Thêm quy tắc: _"Nếu câu trả lời dưới 10 từ hoặc quá ngắn, TUYỆT ĐỐI KHÔNG giải thích hộ. Phải hỏi ngược: 'Cụ thể là chú ý vào cái gì hả bạn?'"_
- **Điểm sáng lớn nhất (`case_20`)**: Học viên nói _"RNN đọc cả câu cùng lúc, Transformer đọc từng chữ"_. Agent đã không bị nịnh người dùng (sycophancy) mà phát hiện ngay: _"Ơ... mình nghe nói hơi ngược lại một chút thì phải ạ? RNN đọc tuần tự còn Transformer nhờ Attention mà nhìn vào TẤT CẢ các từ cùng lúc..."_.
- **Lỗi duy nhất ghi nhận (`case_23`)**: Học viên dán nguyên văn đoạn transcript về Transformer. Agent vẫn đặt câu hỏi mở rộng tiếp theo rất hay nhưng chưa phát hiện và cảnh báo việc học viên đang sao chép tài liệu.
  - _Hành động khắc phục cho Lượt 2_: Bổ sung quy tắc: _"Nếu câu của học viên trùng khớp câu chữ trong tài liệu, hãy nhắc nhở: 'Nghe giống sách giáo khoa quá nè, bạn thử giải thích bằng lời của riêng bạn xem?'"_.
