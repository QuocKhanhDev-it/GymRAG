"""Buổi 2: thử lớp LLMClient với 3 loại câu hỏi."""

import json

from app.config import config_hash, get_config, load_prompt
from app.llm import LLMClient

QUESTIONS = [
    "Ăn bao nhiêu protein mỗi ngày để tăng cơ?",  # trong phạm vi
    "Giá vàng hôm nay bao nhiêu?",  # ngoài phạm vi
    "Tôi đang đau lưng, có nên tập deadlift tiếp không?",  # an toàn
]

system = load_prompt(get_config().prompt.version)
llm = LLMClient()
print("settings:", llm.settings)  # thử xem key có bị lộ không

for q in QUESTIONS:
    r = llm.chat(system, q, json_mode=True)
    data = json.loads(r.text)
    print(f"\n### {q}")
    print(json.dumps(data, ensure_ascii=False, indent=2))
    print(
        f"-- vào {r.tokens_in} | ra {r.tokens_out} | ${r.cost_usd} | {r.latency_ms} ms | config {config_hash()}"
    )
