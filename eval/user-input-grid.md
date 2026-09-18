# Lưới Đầu Vào Của Người Dùng (User Input Grid)

Tài liệu thể hiện 5 chiều không gian đầu vào từ học viên khi tham gia phiên học **Teach Back (Chủ đề: Foundation - Transformer & Cơ chế Attention)** dựa trên dữ liệu thật từ `rag_handoff` (`transcript-04-clean.md` & `transcript-06-clean.md`).

---

## 5 Chiều Đánh Giá (Dimensions)

1. **Chunk bài giảng (5 chunks)**:
   - Chunk 1: Phân biệt AI vs Machine Learning vs Deep Learning (`[T04-015]`, `[T06-027]`)
   - Chunk 2: Lịch sử Symbolic AI & Mùa đông AI (`[T04-024]` - `[T04-027]`)
   - Chunk 3: Deep Learning & Sức mạnh dữ liệu ImageNet (`[T04-030]` - `[T04-033]`)
   - Chunk 4: Kiến trúc Transformer & Cơ chế Attention (`[T04-038]` - `[T04-040]`)
   - Chunk 5: Bản chất xác suất & Vì sao LLM bịa (`[T01-019]`, `[T06-045]`)
2. **Mức đúng/sai**: Đúng hoàn toàn / Đúng nhưng thiếu / Sai một phần / Sai nghiêm trọng (sai ngược bản chất).
3. **Mức chi tiết**: Chi tiết có ví dụ (analogy) / Khái quát / Cụt lủn 1-2 từ / Tiếng lóng (slang).
4. **Trong/ngoài bài**: Đúng phạm vi transcript / Liên quan nhưng ngoài bài / Hoàn toàn ngoài lề (tán gẫu, đầu tư).
5. **Dạng input**: Tự giải thích bằng lời riêng / Copy nguyên văn transcript / Hỏi ngược lại agent / Tán gẫu.

---

## Ma Trận Bao Phủ (Coverage Matrix)

### Ma trận 1: Chunk Bài Giảng × Mức Đúng/Sai

| Chunk Chủ Đề                         | Đúng hoàn toàn       | Đúng nhưng thiếu | Sai một phần                      | Sai nghiêm trọng (Crucial)              |
| :----------------------------------- | :------------------- | :--------------- | :-------------------------------- | :-------------------------------------- |
| **Chunk 1: AI vs ML vs DL**          | `case_01`, `case_02` | `case_15`        | [Gap]                             | [Gap]                                   |
| **Chunk 2: Symbolic & Mùa đông**     | `case_03`, `case_04` | [Gap]            | `case_21`                         | [Gap]                                   |
| **Chunk 3: Deep Learning & Data**    | `case_05`, `case_06` | [Gap]            | `case_13`                         | [Gap]                                   |
| **Chunk 4: Transformer & Attention** | `case_07`, `case_08` | `case_14`        | [Gap]                             | `case_20` _(sai ngược RNN/Transformer)_ |
| **Chunk 5: Bản chất LLM & Prompt**   | `case_09`, `case_10` | [Gap]            | `case_22` _(ngộ nhận logic 100%)_ | [Gap]                                   |

---

### Ma trận 2: Mức Chi Tiết × Dạng Input

| Mức chi tiết              | Tự diễn đạt                                     | Copy transcript | Hỏi vặn/Hỏi ngược            | Lạc đề / Tán gẫu                                  |
| :------------------------ | :---------------------------------------------- | :-------------- | :--------------------------- | :------------------------------------------------ |
| **Chi tiết có ví dụ**     | `case_02` _(máy Casio)_, `case_05` _(ImageNet)_ | `case_23`       | `case_11` _(OpenAI 2015)_    | [Gap]                                             |
| **Khái quát chuẩn**       | `case_01`, `case_04`, `case_08`, `case_09`      | [Gap]           | `case_12` _(thay thế coder)_ | `case_18` _(fine-tune LoRA)_                      |
| **Cụt lủn / Vague**       | `case_14` _(1 từ)_, `case_15`, `case_24`        | [Gap]           | [Gap]                        | `case_17` _(mua cổ phiếu)_, `case_19` _(trà sữa)_ |
| **Tiếng lóng / Than thở** | `case_16` _(ảo ma chả hiểu)_                    | [Gap]           | [Gap]                        | [Gap]                                             |

---

### Ma trận 3: Trong / Ngoài Phạm Vi Transcript

- **Đúng phạm vi transcript** (17 cases): `case_01` -> `case_10`, `case_13`, `case_14`, `case_15`, `case_16`, `case_20`, `case_21`, `case_22`.
- **Liên quan AI nhưng ngoài bài giảng** (4 cases): `case_11` _(OpenAI 2015)_, `case_12` _(AI thay thế lập trình)_, `case_18` _(fine-tune H100)_, `case_24` _(khen chung chung)_.
- **Hoàn toàn ngoài lề** (2 cases): `case_17` _(chứng khoán NVIDIA)_, `case_19` _(rủ đi chơi)_.
- **Gian lận học thuật** (1 case): `case_23` _(copy nguyên văn transcript)_.

---

## Các Lỗ Hổng Kiểm Thử Cần Bổ Sung Sau CP4 (Gap Analysis)

1. **[Gap 1]**: Học viên trả lời sai hoàn toàn ở Chunk 1 (ví dụ: Machine Learning là mạng internet).
2. **[Gap 2]**: Học viên giải thích đúng khái niệm nhưng dùng từ ngữ chuyên sâu tiếng Anh học thuật khác xa giọng giảng viên.
3. **[Gap 3]**: Học viên yêu cầu agent đưa ra câu trả lời trực tiếp ("Thôi nói luôn đáp án đi").
