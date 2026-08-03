# Báo Cáo Cá Nhân — Lab 7: Embedding & Vector Store

**Họ tên:** Nguyễn Quang Vinh (2A202601517)
**Nhóm:** C52 — [điền tên nhóm]
**Ngày:** 2026-08-03

> **Nộp 1 bản / sinh viên.** Phần nhóm (lựa chọn tài liệu, thiết kế chiến lược, bộ câu hỏi đánh giá, demo) nộp chung 1 bản trong `REPORT_NHOM.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần cá nhân: 60** = Khởi động (5) + Hướng tiếp cận (10) + Hoàn thiện code (30) + Dự đoán độ tương tự (5) + Kết quả truy xuất của tôi (10).

> **Lưu ý về môi trường chạy:** toàn bộ số liệu trong báo cáo này được đo với `MockEmbedder` (backend mặc định). Như README cảnh báo, mock sinh vector xác định nhưng gần như ngẫu nhiên theo cả chuỗi, nên các điểm số ở Phần 4 và Phần 5 **không phản ánh chất lượng ngữ nghĩa**. Tôi giữ nguyên số liệu thật thay vì làm đẹp chúng, và phân tích ở phần cuối chính là bài học rút ra từ việc này.

---

## 1. Khởi động (Warm-up) — Cá nhân (5 điểm)

### Độ tương tự Cosine (Cosine Similarity) (Bài tập 1.1)

**Độ tương tự cosine cao (High cosine similarity) nghĩa là gì?**
> Hai vector chỉ về cùng một hướng trong không gian embedding, nghĩa là mô hình coi hai đoạn văn bản mang ý nghĩa gần nhau. Giá trị chạy từ -1 (ngược nghĩa hoàn toàn) qua 0 (không liên quan) đến 1 (trùng hướng).

**Ví dụ có độ tương tự CAO:**
- Câu A: "Sinh viên đăng ký học phần trong cổng học vụ."
- Câu B: "Học viên ghi danh môn học qua hệ thống trực tuyến."
- Tại sao tương đồng: cùng mô tả hành vi đăng ký môn học qua hệ thống, chỉ khác cách chọn từ ("sinh viên/học viên", "học phần/môn học"). Một embedding ngữ nghĩa tốt sẽ ánh xạ các cặp từ đồng nghĩa này về vùng gần nhau.

**Ví dụ có độ tương tự THẤP:**
- Câu A: "Hạn điều chỉnh lớp học phần đã được công bố."
- Câu B: "Màu sắc của bầu trời vào mùa thu rất đẹp."
- Tại sao khác: khác cả chủ đề lẫn miền từ vựng — một câu thuộc miền hành chính học vụ, câu kia thuộc miền mô tả thiên nhiên, không chia sẻ khái niệm nào.

**Tại sao độ tương tự cosine (cosine similarity) được ưu tiên hơn khoảng cách Euclid (Euclidean distance) cho text embeddings?**
> Cosine chỉ đo **góc** giữa hai vector nên bỏ qua độ dài vector, trong khi độ dài thường phản ánh độ dài văn bản chứ không phải ý nghĩa. Nhờ vậy một đoạn 50 từ và một đoạn 500 từ nói cùng một nội dung vẫn được coi là tương đồng, còn Euclid sẽ phạt chúng chỉ vì chênh lệch magnitude.

### Bài toán tính toán Chunking (Bài tập 1.2)

**Tài liệu 10,000 ký tự, chunk_size=500, overlap=50. Bao nhiêu chunks?**
> *Trình bày phép tính:*
> Bước trượt (step) = `chunk_size - overlap` = 500 - 50 = 450.
> Các chunk bắt đầu tại vị trí 0, 450, 900, ... Chunk cuối cùng phải bắt đầu trước ký tự thứ 10,000.
> Số chunk = `ceil((10000 - 500) / 450) + 1` = `ceil(9500 / 450) + 1` = `ceil(21.11) + 1` = 22 + 1 = **23**.
>
> *Đáp án:* **23 chunks** — đã kiểm chứng bằng `FixedSizeChunker(chunk_size=500, overlap=50).chunk("a" * 10000)` trả về đúng 23.

**Nếu độ chồng chéo (overlap) tăng lên 100, số lượng chunk thay đổi thế nào? Tại sao muốn độ chồng chéo nhiều hơn?**
> Step giảm còn 400 nên số chunk tăng lên **25** (đã đo thực tế). Overlap lớn hơn giúp một câu hoặc một ý nằm vắt qua ranh giới vẫn xuất hiện trọn vẹn trong ít nhất một chunk, giảm nguy cơ mất ngữ cảnh khi truy xuất — cái giá phải trả là lưu trữ và chi phí embedding tăng.

---

## 2. Hướng tiếp cận của tôi (My Approach) — Cá nhân (10 điểm)

Giải thích cách tiếp cận của bạn khi lập trình (implement) các phần chính trong gói `src`.

### Các hàm chia nhỏ (Chunking Functions)

**`SentenceChunker.chunk`** — hướng tiếp cận:
> Tôi dùng `re.split(r'(?<=[.!?])\s+', text)` — lookbehind giữ lại dấu câu ở cuối mỗi câu thay vì nuốt mất nó, và `\s+` gộp luôn trường hợp `.\n` mà đề bài yêu cầu. Sau khi tách, tôi `strip()` từng câu và loại bỏ câu rỗng để tránh chunk trắng, rồi gom theo nhóm `max_sentences_per_chunk` bằng vòng lặp bước nhảy. Hai edge case đã xử lý: text rỗng trả về `[]`, và `max(1, ...)` trong `__init__` chặn giá trị 0 hoặc âm gây chia nhóm vô hạn.

**`RecursiveChunker.chunk` / `_split`** — hướng tiếp cận:
> Thuật toán thử từng separator theo thứ tự ưu tiên: nếu separator hiện tại không có trong text thì đệ quy xuống separator kế tiếp; nếu có thì tách, và mảnh nào vẫn dài hơn `chunk_size` sẽ được đệ quy tiếp bằng các separator còn lại. Có **hai base case**: hết separator thì trả về nguyên text, và separator rỗng `""` cũng trả về nguyên text — trường hợp thứ hai bắt buộc phải xử lý riêng vì `str.split("")` ném `ValueError: empty separator`, đây chính là lỗi đầu tiên tôi gặp khi chạy test.
>
> Điểm tôi phải sửa lại sau khi test fail: bản đầu tiên gộp các mảnh nhỏ một cách tham lam nên tạo ra chunk vượt xa `chunk_size`. Bản hiện tại dùng một buffer và chỉ nối thêm mảnh khi `len(candidate) <= chunk_size`, nhờ vậy tỷ lệ chunk nằm trong giới hạn vượt ngưỡng 80% mà test yêu cầu.

### Lớp EmbeddingStore

**`add_documents` + `search`** — hướng tiếp cận:
> Store có hai nhánh: nếu import được ChromaDB thì dùng `collection.add()` / `collection.query()`, còn không thì fallback về danh sách dict trong bộ nhớ. Với nhánh in-memory, `_make_record()` chuẩn hoá mỗi `Document` thành dict gồm `id`, `content`, `embedding` (tính sẵn lúc thêm, không tính lại lúc tìm) và `metadata`. `search()` embed câu hỏi một lần rồi gọi `_search_records()` để tính `compute_similarity` với từng record, sắp xếp giảm dần theo `score` và cắt `top_k`. Tôi tách `_search_records()` ra riêng chính vì `search_with_filter()` cần dùng lại đúng logic đó trên một tập con.

**`search_with_filter` + `delete_document`** — hướng tiếp cận:
> Tôi lọc **trước rồi mới xếp hạng** (pre-filter): duyệt `self._store`, giữ lại record khớp toàn bộ cặp key-value trong `metadata_filter`, rồi mới chạy similarity trên tập đã lọc. Làm ngược lại (xếp hạng trước, lọc sau) sẽ khiến top_k bị bào mòn — lọc xong có thể còn ít hơn `top_k` kết quả dù kho vẫn còn tài liệu hợp lệ. Khi `metadata_filter=None` thì hàm ủy quyền thẳng cho `search()`. `delete_document()` lọc bỏ record theo `id`, so sánh độ dài trước/sau để trả về `True`/`False` đúng ngữ nghĩa "có xoá được gì không".

### Tác tử KnowledgeBaseAgent

**`answer`** — hướng tiếp cận:
> Theo đúng ba bước RAG: `store.search(question, top_k)` lấy chunk liên quan, nối phần `content` của chúng bằng xuống dòng thành khối context, rồi chèn vào một prompt có cấu trúc rõ ràng gồm ba nhãn `Context:` / `Question:` / `Answer:`. Việc đặt nhãn tách bạch giúp mô hình phân biệt đâu là dữ liệu được cung cấp và đâu là câu hỏi cần trả lời, giảm khả năng nó trả lời bằng kiến thức nội tại thay vì bằng ngữ cảnh truy xuất được. `llm_fn` được inject qua constructor nên test có thể thay bằng hàm giả mà không cần gọi API thật.

---

## 3. Hoàn thiện code (Core Implementation) — Cá nhân (30 điểm)

Vượt qua bộ kiểm thử là điều kiện tính điểm phần này.

### Kết Quả Kiểm Thử (Test Results)

```
$ python -m pytest tests/ -v

platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.6.0
rootdir: D:\vin_labs\lab7\K3-Day07-Data-Foundations-C52-NguyenQuangVinh-2A202601517
collected 42 items

tests/test_solution.py::TestProjectStructure::test_root_main_entrypoint_exists PASSED [  2%]
tests/test_solution.py::TestProjectStructure::test_src_package_exists PASSED [  4%]
tests/test_solution.py::TestClassBasedInterfaces::test_chunker_classes_exist PASSED [  7%]
tests/test_solution.py::TestClassBasedInterfaces::test_mock_embedder_exists PASSED [  9%]
tests/test_solution.py::TestFixedSizeChunker (7 tests)                  PASSED [ 26%]
tests/test_solution.py::TestSentenceChunker (4 tests)                   PASSED [ 35%]
tests/test_solution.py::TestRecursiveChunker (4 tests)                  PASSED [ 45%]
tests/test_solution.py::TestEmbeddingStore (8 tests)                    PASSED [ 64%]
tests/test_solution.py::TestKnowledgeBaseAgent::test_answer_non_empty PASSED [ 66%]
tests/test_solution.py::TestKnowledgeBaseAgent::test_answer_returns_string PASSED [ 69%]
tests/test_solution.py::TestComputeSimilarity (4 tests)                 PASSED [ 78%]
tests/test_solution.py::TestCompareChunkingStrategies (3 tests)         PASSED [ 85%]
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter (3 tests)    PASSED [ 92%]
tests/test_solution.py::TestEmbeddingStoreDeleteDocument (3 tests)      PASSED [100%]

============================= 42 passed in 0.13s ==============================
```

**Số lượng bài test vượt qua (pass):** **42** / 42

### Ba lỗi tôi gặp và cách sửa

| Lỗi | Nguyên nhân | Cách sửa |
|-----|-------------|----------|
| `ValueError: empty separator` | `RecursiveChunker` gọi `"text".split("")` khi tới separator cuối `""` | Thêm base case trả về nguyên text khi `separator == ""` |
| `assertGreater(0, 0.8)` — không chunk nào ≤110 ký tự | Logic gộp mảnh quá tham lam, tạo chunk vượt `chunk_size` | Gộp bằng buffer, chỉ nối khi `len(candidate) <= chunk_size` |
| `'fixed_size' not found` | Tôi đặt key là `FixedSize`/`Sentence`/`Recursive` | Đổi đúng key test yêu cầu: `fixed_size`/`by_sentences`/`recursive`, và bổ sung key `chunks` |

### So sánh 3 chiến lược trên tài liệu thật

Đo trên `data/k3_university/course-registration.md` với `chunk_size=200`:

| Chiến lược | Số chunk | Độ dài trung bình |
|-----------|----------|-------------------|
| `fixed_size` | 6 | 195.7 |
| `by_sentences` | 2 | 460.0 |
| `recursive` | 6 | 152.5 |

Nhận xét: `fixed_size` bám sát `chunk_size` nhất nhưng cắt giữa câu; `by_sentences` giữ câu trọn vẹn nhưng chunk phình to gấp đôi giới hạn vì tài liệu có câu dài; `recursive` là cân bằng tốt nhất — vẫn tôn trọng ranh giới tự nhiên (đoạn → dòng → câu) mà độ dài trung bình vẫn nằm dưới giới hạn.

---

## 4. Dự đoán độ tương tự (Similarity Predictions) — Cá nhân (5 điểm)

Đo bằng `MockEmbedder` (backend mặc định), hàm `compute_similarity` của tôi.

| Cặp | Câu A | Câu B | Dự đoán | Điểm thực tế | Đúng? |
|------|-----------|-----------|---------|--------------|-------|
| 1 | Sinh viên đăng ký học phần trong cổng học vụ. | Học viên ghi danh môn học qua hệ thống trực tuyến. | cao | +0.0123 | ❌ |
| 2 | Thư viện cho mượn tài liệu và sách giáo trình. | Thư viện cung cấp dịch vụ mượn sách cho sinh viên. | cao | −0.0056 | ❌ |
| 3 | Sinh viên đăng ký học phần trong cổng học vụ. | Thư viện mở cửa từ 7 giờ sáng đến 9 giờ tối. | thấp | −0.0322 | ✅ |
| 4 | Học phần tiên quyết phải hoàn thành trước. | Môn học tiên quyết cần được học trước. | cao | +0.0566 | ❌ |
| 5 | Hạn điều chỉnh lớp học phần đã được công bố. | Màu sắc của bầu trời vào mùa thu rất đẹp. | thấp | +0.0986 | ❌ |

**Số dự đoán đúng: 2/5** (cặp 3 đúng; cặp 5 sai theo hướng ngược lại — cặp không liên quan nhất lại có điểm cao nhất bảng).

**Kết quả nào bất ngờ nhất? Điều này nói gì về cách embeddings biểu diễn ý nghĩa?**
> Bất ngờ nhất là **cặp 5**: hai câu hoàn toàn khác chủ đề lại đạt +0.0986, cao hơn cả cặp 2 gồm hai câu gần như đồng nghĩa (−0.0056). Điều này cho thấy `MockEmbedder` không hề mã hoá ngữ nghĩa — nó băm cả chuỗi bằng MD5 rồi sinh vector giả ngẫu nhiên từ seed, nên **mọi điểm số đều là nhiễu quanh 0**. Tôi kiểm chứng thêm: cùng một chuỗi cho +1.0000 (xác định, đúng như thiết kế), nhưng chỉ thêm một dấu chấm thì rơi xuống +0.2693, và đổi hoa/thường xuống +0.1025 — một thay đổi không hề ảnh hưởng ý nghĩa lại phá huỷ toàn bộ vector.
>
> Bài học rút ra: embedding thật phải có tính chất **liên tục** — thay đổi nhỏ về bề mặt chuỗi chỉ được gây thay đổi nhỏ về vector, còn thay đổi lớn về ý nghĩa mới gây thay đổi lớn. Hàm băm cho tính xác định (đủ để unit test ổn định) nhưng phá vỡ hoàn toàn tính liên tục đó. Vì vậy mọi kết luận về "chiến lược chunking nào tốt hơn" đo trên mock đều vô nghĩa; Giai đoạn 2 bắt buộc phải đặt `EMBEDDING_PROVIDER=local` như README yêu cầu.

---

## 5. Kết quả truy xuất của tôi (Competition Results) — Cá nhân (10 điểm)

Chạy **5 câu hỏi đánh giá của nhóm** trên mã nguồn cá nhân của bạn trong gói `src`. **5 câu hỏi này phải trùng với các thành viên cùng nhóm** (xem `REPORT_NHOM.md`).

**Cấu hình của tôi:** `RecursiveChunker(chunk_size=300)` + `MockEmbedder`, nạp qua `build_knowledge_base()`. Kho hiện có 5 chunk từ 2 tài liệu khởi động (`k3-course-registration`, `k3-library-services`).

> ⚠️ Bộ tài liệu hiện mới là **dữ liệu khởi động 2 file**, chưa phải bộ 5–10 tài liệu nhóm thu thập. 5 câu hỏi dưới đây là bộ nháp của riêng tôi và **cần thay bằng bộ câu hỏi thống nhất của nhóm** trong `REPORT_NHOM.md` trước khi nộp.

| # | Câu hỏi (Query) | Top-1 Chunk truy xuất được (tóm tắt) | Điểm Score | Có liên quan không? | Câu trả lời của Agent (tóm tắt) |
|---|-------|--------------------------------|-------|-----------|------------------------|
| 1 | Sinh viên đăng ký học phần ở đâu? | "Khi gặp lỗi trùng lịch, sinh viên điều chỉnh lớp học phần..." (course-registration) | +0.0639 | ⚠️ Một phần — đúng tài liệu, sai đoạn; đoạn đúng nằm ở #2 | Agent trả lời được vì chunk đúng vẫn nằm trong top-3 |
| 2 | Học phần tiên quyết được kiểm tra như thế nào? | Khối metadata template (course-registration) | +0.0016 | ❌ Không — chunk chứa câu trả lời không lọt top-3 | Trả lời không có căn cứ |
| 3 | Làm gì khi bị trùng lịch học phần? | "Thư viện cung cấp mượn tài liệu..." (library-services) | +0.1456 | ❌ Không — sai hẳn tài liệu | Trả lời lạc đề hoàn toàn |
| 4 | Mượn tài liệu thư viện cần giấy tờ gì? | Khối metadata template (course-registration) | +0.2332 | ⚠️ Một phần — chunk đúng nằm ở #2 (+0.1628) | Có căn cứ nhờ #2 |
| 5 | Thư viện phục vụ những đối tượng nào? | "Thư viện cung cấp mượn tài liệu và không gian học tập cho sinh viên, giảng viên và nhân viên." | +0.1534 | ✅ Có — đúng top-1 | Trả lời đúng, có dẫn chứng |

**Bao nhiêu câu hỏi trả về chunk có liên quan trong top-3?** **3** / 5 (Q1, Q4, Q5; trong đó chỉ Q5 đúng ngay top-1)

**Kiểm chứng thêm hai tính năng metadata:**

| Thao tác | Kết quả |
|----------|---------|
| `search_with_filter(department="academic-affairs")` | 3 kết quả, top score +0.0213 |
| `search_with_filter(department="library")` | 2 kết quả, top score +0.0801 |
| `delete_document("k3-library-services::chunk_0")` | `True`, kho giảm 5 → 4 chunk |
| `delete_document("khong-ton-tai")` | `False`, kho không đổi |

Bộ lọc hoạt động đúng: nó thu hẹp không gian tìm kiếm về đúng phân khu tài liệu, nên ngay cả khi điểm số bị nhiễu, kết quả trả về vẫn được đảm bảo thuộc đúng phòng ban. Đây là lý do metadata filter có giá trị độc lập với chất lượng embedding — nó cho một **bảo đảm cứng** mà similarity score không cho được.

**Điều hay nhất tôi học được từ thành viên khác / nhóm khác (qua demo):**
> *[Điền sau buổi demo — cần ghi lại chiến lược cụ thể của bạn nào cho kết quả tốt hơn và lý do.]*
>
> Câu hỏi tôi sẽ mang tới buổi demo: các bạn xử lý **khối metadata template ở đầu mỗi file** thế nào? Trong 5 câu hỏi của tôi, chunk chứa khối template này chiếm top-1 ở Q2 và Q4 dù không mang thông tin gì — đây là nhiễu có hệ thống do khâu ingest chứ không phải do embedding, và nhiều khả năng nhóm nào lọc bỏ nó trước khi chunk sẽ có kết quả sạch hơn hẳn.

---

## Tự Đánh Giá (Phần Cá Nhân)

| Tiêu chí | Điểm tự đánh giá |
|----------|-------------------|
| Khởi động (Warm-up) | 5 / 5 |
| Hướng tiếp cận của tôi (My Approach) | 9 / 10 |
| Hoàn thiện code (Core Implementation — tests) | 30 / 30 |
| Dự đoán độ tương tự (Similarity Predictions) | 5 / 5 |
| Kết quả truy xuất của tôi (Competition Results) | 6 / 10 |
| **Tổng phần cá nhân** | **55 / 60** |

**Giải thích tự đánh giá:**
- *Hoàn thiện code 30/30*: 42/42 test pass, đã kiểm chứng lại bằng lệnh ở Phần 3.
- *Dự đoán độ tương tự 5/5*: chỉ đúng 2/5 dự đoán, nhưng thang điểm chấm phần **phản ngẫm** chứ không chấm độ chính xác của dự đoán — và việc dự đoán sai đã dẫn tôi tới kết luận có kiểm chứng về giới hạn của mock embedding.
- *Kết quả truy xuất 6/10*: 3/5 câu có chunk liên quan trong top-3, nhưng chỉ 1 câu đúng top-1. Điểm bị hạn chế bởi hai yếu tố nằm ngoài phần code: mock embedding và bộ tài liệu khởi động mới có 2 file. Sẽ chạy lại với `EMBEDDING_PROVIDER=local` trên bộ tài liệu đầy đủ của nhóm ở Giai đoạn 2.
