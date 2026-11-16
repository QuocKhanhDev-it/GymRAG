"""Buổi 1 - Bước 3: gọi LLM lần đầu, in token và chi phí ước tính."""

import os
import sys

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()  # đọc .env -> biến môi trường

BASE_URL = os.getenv("LLM_BASE_URL")
API_KEY = os.getenv("LLM_API_KEY")
MODEL = os.getenv("LLM_MODEL")
PRICE_IN = float(os.getenv("PRICE_IN_PER_M") or 0)  # USD / 1 triệu token vào
PRICE_OUT = float(os.getenv("PRICE_OUT_PER_M") or 0)  # USD / 1 triệu token ra

if not (BASE_URL and API_KEY and MODEL):
    sys.exit("Thiếu LLM_BASE_URL / LLM_API_KEY / LLM_MODEL trong .env")

client = OpenAI(base_url=BASE_URL, api_key=API_KEY, timeout=30)

QUESTION = "Người mới tập gym nên tập mấy buổi một tuần? Trả lời ngắn gọn trong 3 câu."


def ask(question: str, temperature: float) -> None:
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": question}],
        temperature=temperature,
    )
    u = resp.usage
    tok_in = u.prompt_tokens
    tok_out = u.total_tokens - u.prompt_tokens  # gồm cả token "suy nghĩ" (nếu có)
    thinking = tok_out - (u.completion_tokens or 0)
    cost = tok_in / 1e6 * PRICE_IN + tok_out / 1e6 * PRICE_OUT

    print(f"\n=== temperature={temperature} ===")
    print(resp.choices[0].message.content)
    print(f"-- vào: {tok_in} | ra: {tok_out} (suy nghĩ: {thinking}) | ~${cost:.6f}")


if __name__ == "__main__":
    for t in (0, 0, 1, 1):  # mỗi mức chạy 2 lần để so
        ask(QUESTION, t)
