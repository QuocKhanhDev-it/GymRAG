"""Single gateway to the LLM: timeout, retry, token counting, cost."""
import time
from dataclasses import dataclass

from openai import APIError, OpenAI

from app.config import get_config, get_settings


class LLMError(Exception):
    """LLM call failed and retries did not help."""


@dataclass
class LLMResult:
    text: str
    tokens_in: int
    tokens_out: int      # includes thinking tokens
    cost_usd: float
    latency_ms: int
    model: str


class LLMClient:
    def __init__(self) -> None:
        self.cfg = get_config().llm
        self.settings = get_settings()
        self.client = OpenAI(
            base_url=self.settings.llm_base_url,
            api_key=self.settings.llm_api_key.get_secret_value(),
            timeout=self.cfg.timeout_s,
            max_retries=self.cfg.max_retries,  # SDK retries 429/5xx/timeouts with backoff
        )

    def cost(self, tokens_in: int, tokens_out: int) -> float:
        s = self.settings
        return tokens_in / 1e6 * s.price_in_per_m + tokens_out / 1e6 * s.price_out_per_m

    def chat(self, system: str, user: str, json_mode: bool = False) -> LLMResult:
        extra = {"response_format": {"type": "json_object"}} if json_mode else {}
        start = time.perf_counter()
        try:
            resp = self.client.chat.completions.create(
                model=self.settings.llm_model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=self.cfg.temperature,
                max_tokens=self.cfg.max_tokens,
                **extra,
            )
        except APIError as e:  # retries exhausted, or a non-retryable error
            raise LLMError(f"LLM call failed: {type(e).__name__}") from e
        latency_ms = int((time.perf_counter() - start) * 1000)

        text = resp.choices[0].message.content
        if not text:
            raise LLMError("Empty LLM response (max_tokens hit while thinking?)")

        u = resp.usage
        tokens_in = u.prompt_tokens
        tokens_out = u.total_tokens - u.prompt_tokens
        return LLMResult(
            text=text,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=round(self.cost(tokens_in, tokens_out), 6),
            latency_ms=latency_ms,
            model=self.settings.llm_model,
        )