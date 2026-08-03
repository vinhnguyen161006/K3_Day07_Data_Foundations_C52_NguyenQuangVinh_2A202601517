# Báo Cáo Nhóm — Lab 7: Embedding & Vector Store

**Nhóm:** C52

**Thành viên:**
- Vũ Văn Phong — 2A202601647
- Hoàng Lê Minh — 2A202601653
- Hà Duy Anh — 2A202601511
- Đoàn Nhật Nam — 2A202601123
- Phạm Sỹ Đức — 2A202601601
- Nguyễn Quang Vinh — 2A202601517

**Ngày:** 03/08/2026

Báo cáo được chốt theo trạng thái repository của từng thành viên tại thời điểm nộp. Kết quả thiếu hoặc không chạy cùng điều kiện được ghi là N/A hoặc non-comparable thay vì được suy đoán hay chấm 0.

---

## 1. Lựa chọn tài liệu (Document Set Quality)

### Phạm vi bộ tài liệu

Chủ đề K3: dịch vụ / quy định đại học.

Phạm vi cụ thể: quy trình đăng ký học phần, add/drop, course withdrawal, điều kiện đăng ký và kênh hỗ trợ của VinUniversity, ưu tiên tài liệu hiện hành và các thông báo Spring/Summer 2026.

Tất cả kết quả được xem là benchmark chung chỉ khi dùng cùng 8 tài liệu trong `data/vinuni_course_registration/` và đúng 5 query trong `benchmarks/vinuni_course_registration.json`.

### Data Inventory

| # | Tài liệu | Nguồn | Ngày lấy / phiên bản | Ký tự | Metadata |
|---|---|---|---|---:|---|
| 1 | registration-hub | https://registrar.vinuni.edu.vn/academics/class-schedule-course-registration/ | 2026-08-03 / not-stated | 2293 | audience=all, category=registration-guide |
| 2 | summer-2026-registration | https://registrar.vinuni.edu.vn/2026/05/22/official-announcement-summer-2026-course-registration/ | 2026-08-03 / 2026-05-22 | 2351 | audience=student, semester=summer-2026 |
| 3 | summer-2026-new-student-portal | https://registrar.vinuni.edu.vn/2026/06/29/announcement-launch-of-the-new-student-portal-for-summer-2026-course-registration/ | 2026-08-03 / 2026-06-29 | 2183 | audience=student, semester=summer-2026 |
| 4 | spring-2026-registration | https://registrar.vinuni.edu.vn/2025/12/15/official-announcement-spring-2026-course-registration/ | 2026-08-03 / 2025-12-15 | 2243 | audience=student, semester=spring-2026 |
| 5 | undergraduate-academic-regulations | https://policy.vinuni.edu.vn/all-policies/academic-regulations-for-full-time-undergraduate-programs/ | 2026-08-03 / 8.1-2024-10-30 | 4767 | audience=all, category=academic-policy |
| 6 | forms-and-petitions | https://registrar.vinuni.edu.vn/academics/forms-petitions/ | 2026-08-03 / not-stated | 1588 | audience=student, category=academic-request-process |
| 7 | spring-2026-important-notes | https://registrar.vinuni.edu.vn/2026/01/28/important-announcement-for-spring-2026-semester/ | 2026-08-03 / 2026-01-28 | 2438 | audience=all, semester=spring-2026 |
| 8 | registrar-faq | https://registrar.vinuni.edu.vn/faqs/ | 2026-08-03 / not-stated | 1465 | audience=all, category=registrar-faq |

### Data Governance Checklist

- [x] Chỉ dùng trang chính thức, công khai của `registrar.vinuni.edu.vn` và `policy.vinuni.edu.vn`.
- [x] Đã kiểm tra `robots.txt`: registrar disallow các khu vực như `/wp-admin/`, `/search/`, query search/page; các URL dùng trong corpus không thuộc rule bị cấm. Policy domain không disallow.
- [x] Không dùng nội dung cần đăng nhập, CAPTCHA, API riêng, snippet search, menu/footer/cookie banner.
- [x] Mỗi file có `source_url`, `retrieved_at`, `document_version` và metadata lọc.
- [x] `scripts/validate_group_corpus.py` pass với 8 markdown documents plus `sources.csv`.

### Metadata Schema

| Trường | Kiểu | Ví dụ | Công dụng retrieval |
|---|---|---|---|
| `doc_id` | string | `summer-2026-registration` | Định danh nguồn gốc, delete/filter theo tài liệu |
| `title` | string | `Summer 2026 Course Registration Announcement` | Hiểu nội dung nguồn |
| `source_url` | HTTPS URL | `https://registrar.vinuni.edu.vn/...` | Truy vết evidence |
| `retrieved_at` | date | `2026-08-03` | Kiểm soát độ mới |
| `document_version` | string | `2026-05-22` | Phân biệt bản/announcement |
| `audience` | string | `student`, `all` | Metadata filter |
| `department` | string | `registrar` | Nguồn nghiệp vụ |
| `category` | string | `academic-policy` | Phân loại tài liệu |
| `language` | string | `en` | Lọc ngôn ngữ |
| `semester` | string | `summer-2026` | Temporal scope |
| `temporal_scope` | string | `semester-specific` | Tránh nhầm general vs semester |
| `source_type` | string | `official-announcement` | Ưu tiên loại nguồn |

---

## 2. Thiết kế chiến lược (Strategy Design)

### Baseline Analysis

Chạy `ChunkingStrategyComparator().compare(..., chunk_size=420)` trên 3 tài liệu.

| Tài liệu | Strategy | Chunks | Avg | Min | Max | Nhận xét |
|---|---|---:|---:|---:|---:|---|
| registration-hub | fixed_size | 6 | 417.17 | 403 | 420 | Có thể cắt giữa ý vì theo ký tự |
| registration-hub | by_sentences | 11 | 206.73 | 85 | 469 | Dễ đọc nhưng một số chunk dài |
| registration-hub | recursive | 8 | 284.0 | 200 | 406 | Giữ paragraph tốt hơn, có thể tách heading |
| summer-2026-registration | fixed_size | 7 | 371.86 | 83 | 420 | Dates vẫn xuất hiện nhưng ranh giới cứng |
| summer-2026-registration | by_sentences | 5 | 467.2 | 275 | 584 | Coherent nhưng vượt kích thước ký tự |
| summer-2026-registration | recursive | 7 | 332.14 | 274 | 418 | Cân bằng tốt cho mốc ngày |
| undergraduate-academic-regulations | fixed_size | 13 | 405.46 | 231 | 420 | Có nguy cơ cắt điều kiện policy |
| undergraduate-academic-regulations | by_sentences | 11 | 430.64 | 38 | 603 | Có chunk rất ngắn/rất dài |
| undergraduate-academic-regulations | recursive | 17 | 278.0 | 159 | 415 | Tách policy chi tiết hơn |

Fixed-size tạo kích thước đều nhưng có nguy cơ cắt giữa ý. Sentence chunking giữ ranh giới ngôn ngữ nhưng độ dài không đều. Recursive chunking cân bằng khá tốt. Heading-aware phù hợp với policy có cấu trúc nhưng cần giữ câu mở đầu và bullet evidence trong cùng chunk.

### Chiến lược của từng thành viên

#### Vũ Văn Phong

- Strategy: `HeadingAwareRecursiveChunker(target_chars=420, min_body_chars=120)`.
- Embedding: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`.
- Chunk count: 87.
- Score: 6/10, verified in current repository.
- Điểm mạnh: Giữ heading path, token audit an toàn, raw output tái chạy được.
- Điểm yếu: Evidence của Q1/Q4 bị tách; Q5 bị policy chunk lấn át forms process.

#### Hoàng Lê Minh

- Strategy: `SentenceChunker(max_sentences_per_chunk=3)`.
- Embedding: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`.
- Chunk count: 65.
- Score: 9/10, self-reported, common L12 benchmark, raw output not available.
- Điểm mạnh: Chunk ngắn và trực tiếp; Q1-Q4 được báo cáo đúng top-1.
- Điểm yếu: Q5 chỉ ở rank 2; không có raw output/runner để tái kiểm chứng.

#### Hà Duy Anh

- Strategy: `RecursiveChunker(chunk_size=400)`, inferred from committed runner.
- Embedding/result: not reported.
- Score: N/A — chưa có kết quả benchmark trong repo.
- Status: implementation/runner present, personal benchmark result not submitted.
- Điểm mạnh: Có runner, corpus, benchmark JSON và HeadingChunker.
- Điểm yếu: `REPORT_CANHAN.md` còn template; chưa có benchmark output hoặc score.

#### Đoàn Nhật Nam

- Strategy: `HeadingSectionChunker(max_section_size=450)`.
- Embedding: MockEmbedder.
- Chunk count: 72 reported.
- Score for fair comparison: N/A.
- Reference result: self-reported 10/10; group report 9.5/10.
- Status: non-comparable — mock embedding and modified queries.
- Điểm mạnh: Giữ section Markdown, phù hợp policy.
- Điểm yếu: Mock embedding, query bị rút gọn, filter khác benchmark và score nội bộ không nhất quán.

#### Phạm Sỹ Đức

- Strategy: `RecursiveChunker(chunk_size=1600)`.
- Embedding: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`.
- Retrieval: query-specific metadata filtering.
- Score: 10/10, self-reported, common L12 benchmark, query-specific metadata filters, raw output not available.
- Điểm mạnh: Báo cáo đủ evidence cho cả 5 query; Q5 được giải quyết bằng category filter.
- Điểm yếu: Không có raw benchmark output; chunk_size 1600 chưa có token audit; filter bổ sung khiến chiến lược không còn chỉ khác chunking.

#### Nguyễn Quang Vinh

- Strategy: `RecursiveChunker(chunk_size=300)`.
- Embedding: MockEmbedder.
- Corpus used in reported benchmark: 2 starter documents.
- Reference score: 6/10 on mock starter benchmark.
- Fair comparison score: N/A.
- Status: non-comparable — mock embedding, starter corpus and different queries.
- Điểm mạnh: Phân tích MockEmbedder trung thực; chạy Python 3.11; có metadata checks.
- Điểm yếu: Không chạy corpus và 5 query chung trong personal report.

### Bảng so sánh cuối

| Thành viên | Strategy | Embedding | Benchmark | Điểm dùng để so sánh | Trạng thái bằng chứng |
|---|---|---|---|---:|---|
| Vũ Văn Phong | Heading-aware Recursive 420 | L12 | Common exact | 6/10 | Verified raw output |
| Hoàng Lê Minh | Sentence 3 câu | L12 | Common exact | 9/10 | Self-reported |
| Hà Duy Anh | Recursive 400 | Không xác nhận | Chưa có output | N/A | Incomplete |
| Đoàn Nhật Nam | HeadingSection 450 | Mock | Modified queries | N/A | Non-comparable; self-report 10/10 |
| Phạm Sỹ Đức | Recursive 1600 + filters | L12 | Common exact | 10/10 | Self-reported |
| Nguyễn Quang Vinh | Recursive 300 | Mock | Starter/draft | N/A | Non-comparable; reference 6/10 |

Không đưa `N/A` vào phép tính trung bình.

### Ba kết quả common L12

| Thành viên | Score | Ghi chú |
|---|---:|---|
| Phạm Sỹ Đức | 10/10 reported | Có category filters ở Q4/Q5 |
| Hoàng Lê Minh | 9/10 reported | Sentence chunking, Q5 ở rank 2 |
| Vũ Văn Phong | 6/10 verified | Raw output và token audit đầy đủ |

### Kết luận chiến lược tốt nhất

Trong các kết quả được báo cáo trên cùng corpus, exact benchmark và L12, Phạm Sỹ Đức có điểm cao nhất với `RecursiveChunker(chunk_size=1600)` kết hợp metadata filtering, đạt 10/10 theo personal report. Tuy nhiên, đây là kết quả self-reported và chiến lược thay đổi cả chunk size lẫn query-specific filter.

Hoàng Lê Minh đạt 9/10 theo báo cáo với SentenceChunker 3 câu/chunk và ít phụ thuộc hơn vào category filter, cho thấy sentence chunking là baseline mạnh cho corpus này.

Vũ Văn Phong đạt 6/10 nhưng là kết quả duy nhất trong repo tổng hợp có raw JSON, runner, token audit và khả năng tái chạy đầy đủ. Heading-aware chunking giữ cấu trúc policy tốt, nhưng chưa tốt với các câu hỏi có evidence phân tán hoặc cần ưu tiên loại tài liệu process/form.

Vì vậy, kết luận thực tế là recursive chunking với chunk đủ lớn kết hợp metadata pre-filter cho kết quả được báo cáo tốt nhất; sentence chunking là phương án cân bằng; heading-aware phù hợp policy nhưng cần cải thiện cách gộp bullet evidence.

---

## 3. Câu hỏi đánh giá & chất lượng truy xuất

### Benchmark Queries và Gold Answers

| # | Query | Gold answer | Relevant documents |
|---|---|---|---|
| 1 | Starting in Summer 2026, which portal must students use for course registration, and what checks confirm that registration is complete? | Starting with Summer 2026, course registration is conducted through the VinUniDigi Student Portal at one.vinuni.edu.vn/student. Students should select the correct term, verify prerequisites, class availability and timetable conflicts, click CONFIRM, ensure every course shows the status Registered, and preview the timetable. | summer-2026-new-student-portal |
| 2 | What was the Summer 2026 course registration period, and what was the final add/drop deadline? | The Summer 2026 course registration period ran from June 29 to July 4, 2026. The final add/drop deadline was July 11, 2026. | summer-2026-registration |
| 3 | After the add/drop period, how is a course withdrawal recorded, by what point must it occur, and what is the program-wide withdrawal credit limit? | After add/drop, dropping a course is treated as a withdrawal and a W grade is recorded on the transcript. Withdrawal must occur before the student completes more than 30 percent of the course study time, and students may withdraw from at most 18 credits over the entire program. | undergraduate-academic-regulations; spring-2026-important-notes |
| 4 | What do Full and Conflict mean during course registration, and what happens when prerequisite requirements have not been satisfied? | Full means that no seats are available. Conflict means that the class overlaps with another registered class. The system prevents registration when prerequisite or pre-study requirements have not been satisfied. | summer-2026-new-student-portal; registration-hub |
| 5 | How should students request a course retake, audit or individual study, and how should they request withdrawal after the add/drop period? | Course retake, audit and individual study requests are submitted by email to the Registrar's Office. Withdrawal after the add/drop period is also requested by email and requires the course instructor's approval. | forms-and-petitions |

### Kết quả Vũ Văn Phong

| # | Top-1 doc | Relevant in top-3 | Evidence ok | Score |
|---|---|---|---|---:|
| 1 | summer-2026-new-student-portal | True | False | 1 |
| 2 | summer-2026-registration | True | True | 2 |
| 3 | undergraduate-academic-regulations | True | True | 2 |
| 4 | registration-hub | True | False | 1 |
| 5 | spring-2026-important-notes | False | False | 0 |

Tổng điểm Vũ Văn Phong: 6/10. Có relevant chunk trong top-3 cho 4/5 câu.

### Tổng hợp kết quả theo 5 query

| Query | Kết quả tốt nhất được báo cáo | Nhận xét |
|---|---|---|
| Q1 Portal/checklist | Phạm Sỹ Đức 2/2 reported; Hoàng Lê Minh top-1 reported | Phong retrieve đúng doc nhưng evidence bị tách |
| Q2 Registration period | Cả ba L12 đều retrieve đúng; Phong verified 2/2 | Mốc ngày nằm trong section rõ ràng |
| Q3 Withdrawal | Phạm/Hoàng reported complete; Phong verified 2/2 | Policy section phù hợp semantic query |
| Q4 Full/Conflict | Phạm reported complete với category filter; Hoàng top-1 reported | Phong thiếu evidence `no seats` |
| Q5 Requests/forms | Phạm reported complete với category filter; Hoàng rank 2 | Phong miss vì withdrawal policy lấn át forms page |

### Metadata Filter Analysis

Metadata filtering giúp rõ nhất ở các query hỏi loại thủ tục cụ thể. Trong kết quả của Phong, filter `audience=student` ở Q1 không thay đổi top-3 vì document student-facing vốn đã đứng đầu. Theo báo cáo của Phạm Sỹ Đức, category filter ở Q4 và Q5 giúp loại tài liệu đúng chủ đề rộng nhưng sai mục đích, đặc biệt đưa `forms-and-petitions` lên cho query 5.

Tuy nhiên, khi mục tiêu là chỉ so sánh chunking, tất cả thành viên nên dùng cùng filter. Các bài nộp hiện tại thay đổi cả chunking và filter nên báo cáo chỉ kết luận về retrieval strategy tổng thể, không quy toàn bộ chênh lệch điểm cho chunker.

### Failure Analysis

1. Evidence fragmentation: Q1 và Q4 có thông tin nằm ở nhiều chunk liền kề.
2. Wrong document type: Q5 ưu tiên policy về withdrawal thay vì trang process/form.
3. Temporal ambiguity: General registration hub nhắc SIS, Summer 2026 chuyển sang VinUniDigi.
4. Oversized chunk risk: Chunk lớn có thể giữ đầy đủ evidence nhưng có nguy cơ vượt model sequence limit nếu không token audit.
5. Evaluation inconsistency: Mock embedding, modified queries và query-specific filters làm một số kết quả không thể so sánh công bằng.

### Đề xuất cải thiện

- Giữ câu giới thiệu cùng bullet list.
- Dùng category metadata cho process/form queries.
- Thêm semester/temporal_scope filter khi hỏi học kỳ cụ thể.
- Token audit mọi chunker.
- Chuẩn hóa query, embedding, top_k và filter trước khi so sánh.
- Lưu raw JSON output cho từng thành viên.

---

## 4. Thuyết trình & bài học nhóm

### Ba insight trình bày

1. Chunking không có một cấu hình thắng mọi query.
2. Metadata filter có thể quan trọng hơn chênh lệch similarity score.
3. Reproducibility cần runner, raw output, model name và token audit.

### Kịch bản demo 3 phút

1. 30 giây — giới thiệu corpus 8 nguồn chính thức và metadata.
2. 45 giây — minh họa HeadingAwareRecursiveChunker bằng một policy section.
3. 60 giây — so sánh ba kết quả common L12: Phong, Hoàng Lê Minh và Phạm Sỹ Đức.
4. 30 giây — trình bày failure Q5 và tác dụng của category filter.
5. 15 giây — kết luận về chunking, metadata và reproducibility.

### Bài học nhóm

Qua đối chiếu repository, nhóm nhận thấy sentence chunking cho precision tốt với câu hỏi ngắn và trực tiếp; recursive chunking với chunk lớn giữ đủ evidence cho câu hỏi nhiều ý; heading-aware chunking bảo toàn cấu trúc policy nhưng có thể tách câu mở đầu khỏi bullet list. Kết quả cũng cho thấy metadata filter có thể thay đổi ranking mạnh hơn việc chỉ điều chỉnh chunk size.

---

## Tự Đánh Giá Phần Nhóm

| Tiêu chí | Điểm tự đánh giá | Giải thích |
|---|---:|---|
| Lựa chọn tài liệu | 10/10 | 8 nguồn chính thức, metadata và `sources.csv` đầy đủ, corpus validation pass. |
| Thiết kế chiến lược | 13/15 | Có nhiều chiến lược khác nhau và phân tích cụ thể, nhưng một số kết quả không chạy cùng điều kiện. |
| Chất lượng truy xuất | 8/10 | Có ba kết quả L12 theo benchmark chung, nhưng hai kết quả chỉ self-reported và ba thành viên còn lại không comparable. |
| Thuyết trình/demo | 3/5 | Đã chuẩn bị insight, failure analysis và kịch bản demo, nhưng không tuyên bố đã thực hiện live demo trước thời điểm nộp. |
| **Tổng phần nhóm** | **34/40** | Evidence-based, không tính các kết quả N/A vào trung bình. |

Tự đánh giá tổng:

| Phần | Điểm |
|---|---:|
| Phần cá nhân Vũ Văn Phong | 56/60 |
| Phần nhóm | 34/40 |
| **Tổng tự đánh giá** | **90/100** |

Đây là tự đánh giá của nhóm theo bằng chứng trong repository, không phải điểm chính thức.
