# NOTES: nhật ký học GymRAG Eval

> Ghi theo buổi: làm gì, kết quả đo được, lỗi gặp và cách sửa, điều rút ra.
> Chỉ ghi số liệu thật. **Không bao giờ ghi API key vào đây.**

## Mục lục

- [Môi trường](#môi-trường)
- [Khái niệm đã học](#khái-niệm-đã-học)
- [Buổi 1: Gọi LLM lần đầu](#buổi-1-gọi-llm-lần-đầu)
- [Buổi 2: Lớp gọi LLM và cấu hình](#buổi-2-lớp-gọi-llm-và-cấu-hình)
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

**Ngày:** 2026-11-15 · **Commit:** *(chưa commit)*

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

---

## Việc còn dở

- [ ] `.env.example` thêm `PRICE_IN_PER_M=` và `PRICE_OUT_PER_M=` (hiện vẫn thiếu)
- [ ] Commit Buổi 2: `config.yaml`, `app/config.py`, `app/llm.py`, `prompts/`, `scripts/try_llm.py`, `requirements.txt`, `NOTES.md`
- [ ] `.gitignore` thêm `evals/reports/` (khi làm eval)
- [ ] Push lên GitHub trước Buổi 6 (CI cần push, và đó cũng là bản sao lưu)
- [ ] Đo lại độ trễ trên nhiều câu (Buổi 5), xem câu 9,5 s có phải ngoại lệ không
- [ ] Xoá bản sao lưu `D:\WSL\backup\ubuntu.tar` khi WSL đã chạy ổn định vài hôm

---

## Mở rộng (sau MVP)

Ý tưởng mới ghi vào đây, **không làm trước khi xong MVP**.

- *(chưa có)*
