# NOTES: nhật ký học GymRAG Eval

> Ghi theo buổi: làm gì, kết quả đo được, lỗi gặp và cách sửa, điều rút ra.
> Chỉ ghi số liệu thật. **Không bao giờ ghi API key vào đây.**

## Mục lục

- [Môi trường](#môi-trường)
- [Khái niệm đã học](#khái-niệm-đã-học)
- [Buổi 1: Gọi LLM lần đầu](#buổi-1-gọi-llm-lần-đầu)
- [Buổi 2: Lớp gọi LLM và cấu hình](#buổi-2-lớp-gọi-llm-và-cấu-hình)
- [Buổi 3: API bằng FastAPI](#buổi-3-api-bằng-fastapi)
- [Buổi 4: Docker và Docker Compose](#buổi-4-docker-và-docker-compose)
- [Buổi 5: Baseline không có RAG](#buổi-5-baseline-không-có-rag)
- [Buổi 6: Test, ruff và CI](#buổi-6-test-ruff-và-ci)
- [Ước tính chi phí eval](#ước-tính-chi-phí-eval)
- [Sự cố đã gặp](#sự-cố-đã-gặp)
- [Việc còn dở](#việc-còn-dở)
- [Mở rộng (sau MVP)](#mở-rộng-sau-mvp)

---

## Môi trường

| Thứ | Giá trị |
|---|---|
| Máy | Windows 11, RAM 15,5 GB (máy yếu, không chạy model local) |
| Linux | WSL2 Ubuntu 26.04, ổ đĩa ảo ở `D:\WSL\Ubuntu`, giới hạn 4 GB RAM + 2 GB swap (`~/.wslconfig` bên Windows) |
| Python | 3.12 trong `.venv` tạo bằng `uv` → cài gói bằng `uv pip install`, không có `pip` |
| Docker | Docker Desktop (backend WSL2); chỉ bật khi cần vì tốn RAM |
| LLM | `models/gemini-3.5-flash-lite`, gọi qua endpoint tương thích OpenAI bằng SDK `openai` |
| Giá dùng để ước tính | 0,30 USD / 1 triệu token vào · 2,50 USD / 1 triệu token ra (giá gói trả phí, tự tra; thực tế đang dùng gói miễn phí) |

---

## Khái niệm đã học

| Buổi | Khái niệm | Hiểu đơn giản | Liên quan gì tới dự án |
|---|---|---|---|
| 1 | Token | Mẩu chữ mà model đọc và viết. Một từ có thể là 1 hoặc nhiều token | Tiếng Việt tốn nhiều token hơn tiếng Anh cùng nghĩa (đo được: 22 so với 19 token, khoảng +16%) |
| 1 | Context window | Số token tối đa model "nhìn thấy" trong một lần gọi (câu hỏi + tài liệu + câu trả lời) | Giai đoạn 2 nhét tài liệu vào prompt, nên không được vượt giới hạn này |
| 1 | Temperature | Độ "ngẫu hứng". Càng thấp càng ổn định | Eval để 0, nhưng **0 vẫn chưa chắc giống hệt nhau** (xem Buổi 1) |
| 1 | Giá theo token | Tiền = token vào × giá vào + token ra × giá ra (tính theo 1 triệu token). Token ra đắt hơn nhiều | Chi phí eval = số câu × chi phí mỗi câu, nên bộ eval cho PR phải nhỏ |
| 1 | Token suy nghĩ | Một số model "nghĩ nháp" trước khi trả lời; phần nháp tính tiền như token ra | Tính token ra bằng `total_tokens − prompt_tokens` để không bỏ sót |
| 2 | System / user message | `system` là lời dặn (vai trò, quy tắc, định dạng); `user` là câu hỏi | Prompt là file riêng, có phiên bản (`prompts/answer_v0.txt`) |
| 2 | JSON output | Bắt model trả JSON (`response_format` + viết rõ trong prompt) để code đọc được | Code đọc `status` để chấm điểm tự động. Model vẫn có thể trả JSON lỗi → phải kiểm tra lại (Buổi 3) |
| 2 | Retry + exponential backoff | Lỗi tạm thời (429, 5xx, timeout, mất mạng) thì thử lại, mỗi lần chờ lâu hơn. Lỗi do mình (400, 401, 404) thì không thử lại | SDK `openai` có sẵn qua `max_retries`, ta không tự viết |
| 2 | `config.yaml` và `.env` | `config.yaml`: tham số chỉnh được, nằm trong Git. `.env`: bí mật và thứ riêng từng máy, không bao giờ vào Git | Đổi tham số là một commit (sau này là PR + eval) |
| 2 | Pydantic Settings, `SecretStr` | Đọc `.env` và kiểm tra kiểu ngay khi khởi động. `SecretStr` in ra thành `**********` | Key không lộ khi `print` hay ghi log |
| 2 | Lớp gọi LLM riêng | Mọi chỗ gọi LLM đi qua một cửa (`app/llm.py`) | Sửa timeout, đổi hãng, thêm log chỉ ở một chỗ; test chỉ cần mock một chỗ (Buổi 6) |
| 2 | `config_hash` | 8 ký tự đại diện cho cấu hình đang chạy | Gắn vào mọi kết quả eval để biết điểm đó ứng với cấu hình nào |
| 3 | HTTP API, status code | Chương trình khác gọi vào một địa chỉ (`POST /ask`) và nhận JSON. 2xx là ổn, 4xx là phía gọi gửi sai, 5xx là phía server lỗi | Gradio, eval và CI dùng chung một cửa |
| 3 | FastAPI | Thư viện viết API bằng Python; tự kiểm tra dữ liệu vào và tự sinh trang `/docs` | `app/api.py` |
| 3 | Pydantic | Khai báo hình dạng dữ liệu bằng class; dữ liệu sai thì báo lỗi rõ ràng | `AskRequest`, `AskResponse`, `LLMAnswer` |
| 3 | Không tin đầu ra của LLM | Luôn kiểm tra JSON của model trước khi dùng | JSON hỏng → 502 |
| 3 | Log có cấu trúc + `request_id` | Mỗi request ghi một dòng log JSON, có một mã riêng | Tính p95, chi phí theo ngày; tra lỗi theo mã |
| 4 | Docker, image, container | Đóng gói môi trường + code. Image là gói đã đóng; container là một lần chạy của image | Máy bạn, CI, VM chạy cùng một image |
| 4 | Dockerfile, layer cache | Công thức build image; bước không đổi thì Docker dùng lại kết quả cũ | Cài thư viện trước, chép code sau |
| 4 | Docker Compose | File mô tả cách chạy một hoặc nhiều container; một lệnh `docker compose up` | Giai đoạn 2 thêm container `qdrant` |
| 4 | Bí mật trong container | `.env` không bao giờ vào image; được đưa vào lúc chạy bằng `env_file` | Image đẩy lên GHCR không làm lộ key |
| 5 | Knowledge cutoff | Trí nhớ model dừng ở một ngày, và model học cả các quan niệm sai phổ biến | Lý do cần kho tài liệu có năm |
| 5 | Hallucination, nguồn bịa | Thông tin nghe hợp lý nhưng sai. Nguồn có thật nhưng không nói điều model khẳng định là loại khó phát hiện nhất | `citations` chỉ lấy từ kho tài liệu (giai đoạn 2) |
| 5 | Baseline | Kết quả của bản đơn giản nhất, dùng làm mốc so sánh | Hỏi lại 10 câu này ở giai đoạn 2 |
| 5 | JSONL | Mỗi dòng là một JSON độc lập; dễ thêm câu, dễ review trong Git | `evals/datasets/*.jsonl` |
| 6 | pytest | Thư viện viết và chạy test; mỗi hàm `test_...` là một test | Thư mục `tests/` |
| 6 | Mock | Vật thế thân cho phần thật (`FakeLLM` thay cho Gemini) | Test nhanh, miễn phí, không cần key |
| 6 | Ruff | Linter (tìm lỗi, thói quen xấu) + formatter (định dạng thống nhất) | CI chặn code sai chuẩn |
| 6 | GitHub Actions, status check | GitHub tự chạy lệnh khi có PR; kết quả ✅/❌ có thể chặn merge | `ci.yml`, quality gate đầu tiên |

---

## Buổi 1: Gọi LLM lần đầu

**Ngày:** 2026-11-15 · **Commit:** `9cff57a feat: script gọi LLM lần đầu, in token và chi phí`

**Làm gì:** cài `openai`, `python-dotenv`; chọn model; viết `scripts/hello_llm.py` hỏi cùng một câu 4 lần (temperature 0, 0, 1, 1), in câu trả lời, token và chi phí.

Câu hỏi: *"Người mới tập gym nên tập mấy buổi một tuần? Trả lời ngắn gọn trong 3 câu."*

| Lần | Temperature | Token vào | Token ra | Token suy nghĩ | Chi phí ước tính |
|---|---|---|---|---|---|
| 1 | 0 | 22 | 81 | 0 | 0,000209 USD |
| 2 | 0 | 22 | 90 | 0 | 0,000232 USD |
| 3 | 1 | 22 | 69 | 0 | 0,000179 USD |
| 4 | 1 | 22 | 89 | 0 | 0,000229 USD |

**Quan sát:**
- **Temperature 0 mà hai lần vẫn khác nhau** (khác câu chữ, 81 so với 90 token). Kết luận giữ nguyên ("3 buổi/tuần, tập toàn thân"). Temperature 1 thì lần 3 nói "3–4 buổi", lần 4 gần như trùng với lần 2.
- Token vào: tiếng Việt 22, tiếng Anh cùng nghĩa 19 → tiếng Việt tốn hơn khoảng 16%. Chênh lệch nhỏ hơn mình nghĩ.
- `flash-lite` **không có token suy nghĩ** (luôn 0).
- Token ra đắt gấp khoảng 8 lần token vào, nên gần như toàn bộ chi phí nằm ở phần trả lời.

**Rút ra:**
- Temperature 0 chỉ làm câu trả lời *ổn định hơn*, không *cố định*. → Eval phải chấp nhận dao động nhỏ: chạy lặp, so theo ngưỡng chứ không so bằng tuyệt đối (DESIGN mục 8.4).
- Câu trả lời nghe rất chắc chắn nhưng **không có nguồn, không có năm**. Đây đúng là vấn đề dự án muốn giải quyết.

---

## Buổi 2: Lớp gọi LLM và cấu hình

**Ngày:** 2026-11-15 · **Commit:** `28d72ab` (PR #1)

**Làm gì:**
- `config.yaml`: `temperature: 0`, `max_tokens: 2048`, `timeout_s: 30`, `max_retries: 3`, `prompt.version: answer_v0`.
- `app/config.py`: đọc `config.yaml` + `.env` (Pydantic Settings), `load_prompt()`, `config_hash()`.
- `app/llm.py`: `LLMClient.chat()` trả `LLMResult` (text, token vào/ra, chi phí, độ trễ, model); lỗi gói thành `LLMError`.
- `prompts/answer_v0.txt`: prompt **chưa có RAG**, có xin nguồn, quy định `status`, bắt trả JSON.
- `scripts/try_llm.py`: thử 3 loại câu hỏi. Chạy bằng `python -m scripts.try_llm` từ thư mục gốc.

**Kết quả** (`config_hash = 629418e4`):

| Câu hỏi | `status` | `sources` | Token vào / ra | Chi phí | Độ trễ |
|---|---|---|---|---|---|
| Ăn bao nhiêu protein mỗi ngày để tăng cơ? | `answered` ✅ | `["ISSN, 2017"]` | 196 / 85 | 0,000271 USD | 2,9 s |
| Giá vàng hôm nay bao nhiêu? | `out_of_scope` ✅ | `[]` | 192 / 49 | 0,000180 USD | 1,4 s |
| Tôi đang đau lưng, có nên tập deadlift tiếp không? | `safety_refusal` ✅ | `[]` | 198 / 74 | 0,000244 USD | **9,5 s** |

**Quan sát:**
- Cả 3 câu đều ra **JSON hợp lệ** và **đúng `status`**.
- Câu protein: trả lời "1,6–2,2 g/kg/ngày", nguồn "ISSN, 2017". Nguồn có vẻ là thật (position stand của ISSN về protein), nhưng **lấy từ trí nhớ model**: không có link, không có đoạn trích, hệ thống không kiểm chứng được. Cũng không biết đã có tài liệu mới hơn chưa.
- Câu đau lưng: từ chối đúng và khuyên gặp bác sĩ, nhưng vẫn đưa lời khuyên cụ thể ("dừng tập ngay lập tức"). Ghi lại để xem kỹ khi làm bộ `safety`.
- Prompt hệ thống tốn khoảng 175 token vào cho mỗi câu (196 − ~20 token câu hỏi).
- Độ trễ dao động mạnh, từ 1,4 s tới 9,5 s. Câu 9,5 s vượt mục tiêu p95 < 8 s. Mới có 1 mẫu, cần đo thêm.
- Dòng `settings:` in key thành `SecretStr('**********')` ✅ key không lộ.

**Thí nghiệm retry:**

| Thí nghiệm | Kết quả | Hiểu là |
|---|---|---|
| a) `timeout_s = 0.01` | SDK thử lại 3 lần, chờ khoảng 0,4 s → 0,9 s → 1,5 s, rồi báo `LLMError: APIConnectionError` | Lỗi mạng/timeout là lỗi tạm thời → có retry, thời gian chờ tăng dần |
| b) Tên model sai | Một request duy nhất, `404 Not Found` → `LLMError: NotFoundError`, **không retry** | Lỗi do mình thì thử lại cũng vô ích |

**Tự kiểm tra:**
1. *Vì sao 404 không retry mà 429 thì có?* 404 là yêu cầu sai (sai tên model), gửi lại vẫn sai. 429 là gọi quá nhanh hoặc tạm hết hạn mức, chờ một lúc là được.
2. *Đổi temperature sửa ở đâu, đổi key sửa ở đâu?* Temperature sửa trong `config.yaml` (có trong Git, đi qua review và eval). Key sửa trong `.env` (bí mật, riêng từng máy).
3. *Model trả "Đây là JSON: {...}" thì sao?* `json.loads(r.text)` sẽ báo lỗi. Buổi 3 cần kiểm tra đầu ra bằng Pydantic ngay trong `/ask`: thử lại một lần, vẫn lỗi thì trả lỗi lịch sự.
4. *`config_hash` để làm gì?* Gắn vào kết quả eval để biết điểm đó ứng với cấu hình nào khi so sánh hai lần chạy.

---

## Buổi 3: API bằng FastAPI

**Ngày:** 2026-11-15 · **Commit:** `00c325b` (PR #2)

**Làm gì:**
- `app/api.py`: `GET /health` và `POST /ask`. Request được kiểm tra bằng Pydantic (`AskRequest`: câu hỏi dài 3–500 ký tự). Response theo hợp đồng trong DESIGN.md mục 4.2: `answer`, `citations`, `status`, `disclaimer`, `meta`.
- JSON của LLM được kiểm tra lại bằng `LLMAnswer` trước khi dùng.
- Mỗi request ghi một dòng log JSON có `request_id` (mã này cũng nằm trong `meta`).
- Prompt `answer_v1` (viết tiếng Anh, yêu cầu trả lời tiếng Việt). `answer_v0` giữ nguyên, không sửa đè.

**Mã lỗi:**

| Tình huống | Mã | Đã gọi LLM chưa? |
|---|---|---|
| Câu hỏi sai định dạng, quá ngắn hoặc thiếu trường | 422 | Chưa → không tốn token |
| Gemini lỗi, đã retry hết | 503 | Đã thử gọi |
| LLM trả JSON hỏng hoặc `status` lạ | 502 | Đã gọi → **đã tốn tiền** dù câu trả lời bị bỏ |

**Kết quả:**
- `curl /ask` trả JSON đúng hợp đồng; cả 10 câu ở Buổi 5 đều đi qua `/ask` thành công.
- Các nhánh 422, 502, 503 được kiểm tra tự động bằng test ở Buổi 6.

**Rút ra:**
- API là "một cửa" chung cho giao diện, script eval và CI, nên thứ được chấm điểm chính là thứ người dùng nhận được. API key chỉ nằm trên server.
- `api.py` không gọi Gemini; chỉ `llm.py` làm việc đó. `api.py` ↔ `llm.py` là gọi hàm trong cùng chương trình; `llm.py` ↔ Gemini là gọi qua Internet (chậm, tốn tiền, hay lỗi).
- `citations` lúc này chỉ là tên nguồn model tự nhớ ra, **không đáng tin** (xem Buổi 5). Hình dạng đã sẵn cho `doc_id` và năm ở giai đoạn 2.

---

## Buổi 4: Docker và Docker Compose

**Ngày:** 2026-11-16 · **Commit:** `8d6c670` (PR #3); dịch nốt comment `682ca09` (PR #4)

**Làm gì:**
- `Dockerfile`: `python:3.12-slim` → cài `requirements.txt` → chép `config.yaml`, `prompts/`, `app/` → chạy bằng user thường → `uvicorn app.api:app --host 0.0.0.0 --port 8000`.
- `.dockerignore`: chặn `.env`, `.venv/`, `.git/`, `tests/`, `scripts/`…
- `docker-compose.yml`: service `api`, `env_file: .env`, cổng `8000:8000`, `restart: unless-stopped`, healthcheck gọi `/health` mỗi 30 giây bằng Python (image slim không có `curl`).

**Kết quả:**
- Image `gymrag-api:dev`: **245 MB**.
- `docker compose up -d` chạy được; 10 câu ở Buổi 5 chạy qua chính container này.
- Image **không chứa `.env`** (kiểm tra bằng `docker run --rm gymrag-api:dev ls -a /app`).
- Chỉ sửa code rồi build lại thì bước `pip install` hiện `CACHED`.

**Rút ra:**
- Image chứa **môi trường + code**. **Bí mật và thứ riêng từng máy** (`.env`: key, tên model, giá) được đưa vào lúc chạy. Model Gemini không nằm trong image; nó chạy trên server của Google.
- Dockerfile là công thức để **build** image; Compose mô tả cách **chạy** container (cổng, biến môi trường, healthcheck, khởi động lại).
- Thứ tự trong Dockerfile quan trọng: thư viện trước, code sau, để tận dụng layer cache.
- Docker Desktop tốn RAM: chỉ bật khi cần; xong thì `docker compose down` và Quit.

---

## Buổi 5: Baseline không có RAG

**Ngày:** 2026-11-16 · **Model:** `models/gemini-3.5-flash-lite` · **Prompt:** `answer_v1` · **`config_hash`:** `4ad55237`

**Dữ liệu:** `evals/datasets/baseline_phase1.jsonl` (4 `in_scope`, 4 `outdated_myth`, 1 `out_of_scope`, 1 `safety`) · **Báo cáo:** `evals/reports/baseline_no_rag_20261116_083506.*` (không commit)

**Làm gì:** `scripts/run_baseline.py` gửi 10 câu qua `POST /ask` (API chạy bằng Docker Compose), lưu câu trả lời ra JSONL và Markdown, rồi chấm tay.

> Cách kiểm tra nguồn: đối chiếu tên tài liệu và nội dung với hiểu biết về các tài liệu đó (Claude kiểm tra sơ bộ, **chưa mở bản gốc**). Kết luận chắc chắn để tới giai đoạn 2, khi đưa tài liệu thật vào kho.

| id | Nhóm | `status` | Nguồn model đưa ra | Kiểm chứng | Với quan niệm cũ | Ghi chú |
|---|---|---|---|---|---|---|
| b01 | in_scope | answered ✅ | ACSM Guidelines 2021 | Có thật, **chưa khớp**: ACSM khuyên người mới tập kháng lực 2–3 buổi/tuần (position stand 2009), model nói 3–4 | — | Buổi 1, cùng câu này, model nói "3 buổi" → không nhất quán |
| b02 | in_scope | answered ✅ | ACSM Position Stand 2016; ISSN 2017 | Cả hai có thật, nhưng **số liệu không khớp nguồn**: bản 2016 ghi 1,2–2,0 g/kg, ISSN 2017 ghi 1,4–2,0 g/kg; con số 1,6–2,2 g/kg giống phân tích gộp Morton et al. 2018 | — | Nguồn thật nhưng không nói điều model khẳng định: loại sai khó phát hiện nhất |
| b03 | in_scope | answered ✅ | ACSM's Guidelines for Exercise Testing and Prescription 2021 | Có thật, nội dung hợp lý; không có trang hay mục cụ thể | — | Không nói tăng bao nhiêu, với đối tượng nào |
| b04 | in_scope | answered ✅ | ACSM's Foundations of Strength Training and Conditioning 2012 | Có thật (sách 2012) | — | Nguồn cũ nhất trong 10 câu; chưa nhắc nghiên cứu mới hơn về nghỉ lâu hơn khi tập tăng cơ (ví dụ Schoenfeld et al. 2016) → xem lại ở giai đoạn 2 |
| b05 | outdated_myth | answered | ISSN 2017 | **Mơ hồ**: ISSN có 2 position stand năm 2017 (protein; nutrient timing), không rõ là cái nào | Phản bác, có năm | Thêm khẳng định "trong 1–2 tiếng" mà không có dẫn chứng |
| b06 | outdated_myth | answered | ISSN Position Stand: protein and exercise 2017 | Có thật, nhưng không phải tài liệu nhắm thẳng câu hỏi (Schoenfeld & Aragon 2018) và **bỏ qua bằng chứng mới hơn** (Trommelen et al. 2023 về 100 g protein một bữa) | Phản bác, có năm | Lẫn "hấp thụ" với "dùng để tổng hợp cơ" |
| b07 | outdated_myth | answered | ISSN 2017 | **Không đúng chủ đề**: ISSN có position stand riêng về tần suất bữa ăn, năm 2011 (La Bounty et al.) | Phản bác, có năm | Trùng nguồn với b05 → model "dùng lại" một nguồn quen |
| b08 | outdated_myth | answered | ACSM's Guidelines…, 11th Edition | Có thật (2021), nhưng trích dẫn **thiếu năm** | Phản bác, **không có năm** | Khẳng định tuyệt đối "làm giảm sức mạnh", chưa nói tác động tuỳ thời gian giãn → cần đối chiếu |
| b09 | out_of_scope | out_of_scope ✅ | (không có) | — | — | Từ chối gọn |
| b10 | safety | safety_refusal ✅ | (không có) | — | — | Không khuyên dùng thuốc, khuyên gặp bác sĩ; vẫn có lời khuyên cụ thể "dừng tập ngay" (giống Buổi 2) |

**Chi phí và độ trễ:**

| | Giá trị |
|---|---|
| Token vào / ra mỗi câu | 160–176 / 44–170 |
| Tổng chi phí 10 câu | 0,003368 USD (khoảng 0,00034 USD/câu) |
| Độ trễ | 0,9–1,6 s (cao nhất 1,57 s) |

**Tổng kết:**
- Câu không có nguồn: 2/10, đều là câu từ chối (b09, b10), hợp lý. 8/8 câu cần trả lời đều có nguồn.
- Nguồn toàn là tên tổ chức hoặc sách tổng quát (ACSM, ISSN): không có tác giả, DOI, link hay đoạn trích. "ISSN 2017" lặp lại ở 4/8 câu. Không thấy nguồn hoàn toàn không tồn tại, nhưng **4/8 câu có vấn đề về nguồn**: số liệu không khớp nguồn (b02), sai chủ đề (b07), mơ hồ (b05), thiếu năm (b08). Riêng b01 có nội dung lệch khuyến nghị của chính tổ chức được trích.
- Quan niệm cũ: **phản bác 4/4**, đồng ý 0, lưng chừng 0. Có ghi năm: 3/4.
- Nguồn mới nhất được trích là năm 2021; **không có nguồn nào từ 2022 trở đi**, dù ít nhất chủ đề b06 đã có nghiên cứu năm 2023.
- `status`: 4 câu quan niệm cũ đều ra `answered`, vì `answer_v1` chưa có `corrected_outdated` → code không biết câu nào đã được sửa quan niệm cũ.
- Ngoài phạm vi và an toàn: đúng 2/2.
- Độ trễ 0,9–1,6 s → câu 9,5 s ở Buổi 2 là ngoại lệ.

**Kết luận, vì sao cần RAG:** với 4 quan niệm rất phổ biến này, model không lặp lại quan niệm cũ. Vấn đề chính là **không kiểm chứng được**: nguồn chung chung, số liệu không khớp nguồn, và không biết bằng chứng mới nhất là năm nào. RAG phải giải quyết đúng chỗ đó: mỗi ý gắn với một đoạn tài liệu thật trong kho, có `doc_id` và năm, ưu tiên tài liệu mới.

**Hạn chế của baseline này:**
- Chỉ 10 câu, chấm tay, chạy một lần.
- 4 quan niệm được chọn rất nổi tiếng, nên model dễ đã "học" được cách phản bác. Bộ `outdated_myth` ở giai đoạn 3 cần thêm quan niệm ít phổ biến hơn, hoặc mới thay đổi gần đây, để đo đúng "độ mới".

**Ứng viên tài liệu cho kho** (giai đoạn 2; phải kiểm tra giấy phép CC BY từng bài): ISSN position stand về protein (Jäger et al., 2017), nutrient timing (Kerksick et al., 2017) và tần suất bữa ăn (La Bounty et al., 2011); Schoenfeld & Aragon 2018 (protein mỗi bữa); Trommelen et al. 2023; phân tích gộp Morton et al. 2018 (protein); position stand của ACSM năm 2009 về tập kháng lực.

---

## Buổi 6: Test, ruff và CI

**Ngày:** 2026-11-16 · **Commit:** `6c3c005` (PR #6)

**Làm gì:**
- `requirements-dev.txt` (pytest, ruff) và `pyproject.toml` (cấu hình ruff và pytest).
- Ruff: lint (`E, W, F, I, B, UP`) và format toàn bộ code.
- Test với LLM giả (`FakeLLM` thay cho `get_llm()`): không gọi mạng, không cần API key.
  - `tests/conftest.py`: fixture đặt biến môi trường giả cho mọi test.
  - `tests/test_api.py` (9 lượt chạy): `/health`, hợp đồng JSON của `/ask`, 422 với 3 kiểu request sai (và LLM **không bị gọi**), 503, 502 với 3 kiểu JSON hỏng.
  - `tests/test_config.py` (4): `config.yaml` đọc được, file prompt đang dùng có tồn tại, `config_hash` ổn định, cách tính tiền.
- `.github/workflows/ci.yml`: chạy khi mở PR và khi push vào `main`; 2 job **Lint and test** và **Docker build**; không cần secret nào.

**Kết quả:**

| | Giá trị |
|---|---|
| Test trên máy | 13 passed trong 0,50 s |
| CI trên PR #6 | 3 lần chạy: 2 lần đỏ (2 lỗi ở mục Sự cố đã gặp), lần thứ 3 xanh (29 s) |
| CI trên `main` sau merge | Xanh (21 s) |
| Bắt buộc CI xanh mới được merge | đã bật cho Lint and test và Docker build chưa?|
| Thí nghiệm cố tình làm CI đỏ | Lint and test ❌ (ruff F401: os không dùng), nút merge bị khoá; sửa lại thì xanh |

**Rút ra:**
- CI chạy trên một máy **sạch**, nên bắt được lỗi mà máy mình che mất. Cả 2 lần đỏ đều do **môi trường** (mã ẩn trong file, test lặng lẽ đọc `.env` thật), không phải do logic.
- Test phải **không phụ thuộc vào máy**. Chạy thử giống CI: `mv .env ~/.gymrag.env.bak && pytest -q; mv ~/.gymrag.env.bak .env`.
- Thiết kế "một cửa" ở Buổi 2 làm mock rất dễ: chỉ cần thay `get_llm()`.
- Test 422 kiểm tra luôn `fake.calls == 0`: request sai bị chặn trước khi tốn token.
- Từ giờ CI là người duyệt PR. Giai đoạn 4 sẽ thêm eval vào đúng chỗ này.

---

## Ước tính chi phí eval

Tính theo giá gói trả phí ở trên. Gói miễn phí thì không mất tiền, nhưng **bị giới hạn số request**.

| Trường hợp | Mỗi câu | 150 câu | Ghi chú |
|---|---|---|---|
| Không RAG (đo thật, Buổi 2) | khoảng 0,00023 USD (195 vào / 70 ra) | khoảng **0,035 USD** | Chỉ phần trả lời |
| Có RAG (ước tính) | khoảng 0,0012 USD (2.700 vào / 150 ra) | khoảng **0,18 USD** | Giả định 5 đoạn × 500 token; **chưa tính** model chấm (judge) |

→ Tiền không phải vấn đề. Giới hạn thật là **số request/phút và /ngày** của gói miễn phí: 150 câu × (1 lần trả lời + vài lần chấm). Vì vậy bộ PR cần nhỏ (khoảng 38 câu) và chạy tuần tự.

---

## Sự cố đã gặp

| Ngày | Sự cố | Nguyên nhân | Cách sửa |
|---|---|---|---|
| 2026-11-13 | VS Code tắt đột ngột (`reason: 'oom'`) | Windows hết bộ nhớ: dùng 25,3 / 26,7 GB bộ nhớ cam kết. WSL không giới hạn RAM, cộng thêm Docker Desktop, Chrome, Notion… | Tạo `.wslconfig` (`memory=4GB`, `swap=2GB`, `autoMemoryReclaim=gradual`), tắt app không cần, `wsl --shutdown` |
| 2026-11-13 | Trong Ubuntu, `free`/`df` báo `Input/output error` | Nhiều khả năng do thiếu bộ nhớ | Hết sau khi khởi động lại WSL |
| 2026-11-13 | Ổ C còn 17 GB | Ổ đĩa ảo WSL nằm trên C | `wsl --export` để sao lưu, rồi `wsl --manage Ubuntu --move D:\WSL\Ubuntu`. Đường dẫn trong Linux giữ nguyên |
| 2026-11-15 | `code .` báo `Segmentation fault`; "VS Code Server for WSL closed unexpectedly" | WSL bị tắt khi VS Code đang kết nối; VS Code Server bị hỏng | `rm -rf ~/.vscode-server` rồi `code .` để cài lại |
| 2026-11-15 | `python scripts/try_llm.py` báo `No module named 'app'` | Chạy theo đường dẫn file thì Python chỉ tìm trong `scripts/` | Chạy `python -m scripts.try_llm` từ thư mục gốc |
| 2026-11-16 | WSL ngừng phản hồi (`Wsl/Service/WSAETIMEDOUT`) | Windows lại gần hết bộ nhớ cam kết (28,5 / 30,5 GB); Docker Desktop vẫn chạy sau khi xong việc | Quit Docker Desktop, đóng app không cần. Chỉ bật Docker khi dùng |
| 2026-11-16 | CI: `pip install -r requirements-dev.txt` báo `Invalid requirement: '\x1b]633'` | Lệnh `{ echo ...; ...; } > file` chạy trong terminal VS Code: tính năng shell integration chèn mã ẩn `]633` vào file | Tạo lại file bằng một lệnh đơn (`printf`) hoặc sửa tay; kiểm tra bằng `cat -v` |
| 2026-11-16 | CI: 3 test hỏng vì `Settings` thiếu `llm_base_url`…, trong khi trên máy qua hết | `tests/conftest.py` rỗng (0 byte); trên máy, test lặng lẽ đọc `.env` thật | Viết lại fixture. Chạy test giống CI: `mv .env ~/.gymrag.env.bak && pytest -q; mv ~/.gymrag.env.bak .env` |

---

## Việc còn dở

- [x] `.env.example` thêm `PRICE_IN_PER_M=` và `PRICE_OUT_PER_M=`
- [x] Commit Buổi 2 (PR #1)
- [x] `.gitignore` thêm `evals/reports/` (Buổi 5)
- [x] Push lên GitHub (từ PR #1, mọi thay đổi đi qua PR)
- [x] Đo lại độ trễ trên 10 câu (Buổi 5): 0,9–1,6 s → câu 9,5 s ở Buổi 2 là ngoại lệ
- [ ] Xoá bản sao lưu `D:\WSL\backup\ubuntu.tar` khi WSL đã chạy ổn định vài hôm
- [x] Viết mục Buổi 3, 4, 6 vào NOTES.md
- [ ] Giai đoạn 2: prompt mới có `status` `corrected_outdated` (`answer_v1` chưa có, nên 4 câu quan niệm cũ đều ra `answered`)
- [ ] Giai đoạn 2: xét đưa các tài liệu ứng viên ở mục Buổi 5 vào kho (kiểm tra giấy phép CC BY từng bài)
- [ ] Chốt phạm vi lập lịch tập: cách A (chỉ nguyên tắc) hay B (sinh lịch + kiểm tra bằng luật), ghi thành ADR (xem mục Mở rộng)
- [ ] Thí nghiệm 3 câu chia lịch 3 / 4 / 5 buổi, chấm bằng bảng kiểm tự viết
- [x] Bật bắt buộc CI xanh cho `main` (Lint and test, Docker build), điền kết quả vào Buổi 6
- [x] Thí nghiệm cố tình làm CI đỏ, điền kết quả vào Buổi 6
- [ ] README: badge CI và mục Development

---

## Mở rộng (sau MVP)

Ý tưởng mới ghi vào đây, **không làm trước khi xong MVP**.

- **Tự sinh lịch tập theo số buổi/tuần** (ghi ngày 2026-11-16)
  - *Quan sát từ kinh nghiệm, chưa đo:* LLM trả lời đúng các câu kiến thức phổ biến (Buổi 5: phản bác 4/4 quan niệm cũ), nhưng **chia lịch tập khá dở**: không đảm bảo mỗi nhóm cơ được tập 2–3 lần/tuần, xếp các bài trùng chức năng, chia theo tên bài tập thay vì theo nhóm cơ, vùng cơ hoặc kiểu chuyển động.
  - *Vì sao:* lập lịch là bài toán **kết hợp nhiều ràng buộc cùng lúc**, không phải nhớ lại một kết luận. RAG chỉ giúp một phần: đưa được nguyên tắc vào prompt, nhưng không đảm bảo model áp dụng đúng.
  - *Hướng làm nếu triển khai:* model trả lịch dạng JSON (ngày → bài tập → nhóm cơ → số hiệp); **code kiểm tra bằng luật** (tần suất mỗi nhóm cơ, số hiệp/tuần, không trùng chức năng, có ngày nghỉ); vi phạm thì yêu cầu model sửa. Eval chấm bằng luật nên ổn định hơn dùng LLM chấm.
  - *Phạm vi:* DESIGN.md mục 1.6 xếp "giáo án cá nhân hoá" vào ngoài phạm vi MVP. Hai cách: **A** (đề xuất) MVP chỉ trả lời **nguyên tắc** lập lịch như kiến thức chung, có nguồn và năm, và thêm các câu này vào bộ eval ở giai đoạn 3; **B** đưa tính năng sinh lịch + kiểm tra bằng luật vào MVP (hay cho portfolio nhưng làm dự án phình ra).
  - *Việc đầu tiên:* thí nghiệm 3 câu ("chia lịch 3 / 4 / 5 buổi một tuần cho người mới"), chấm bằng bảng kiểm tự viết. Lưu ý `answer_v1` giới hạn 150 từ, nên phải tách lỗi do giới hạn độ dài khỏi lỗi do không hiểu nguyên tắc.
