"""HTTP API: /health and /ask (no RAG yet)."""
import json
import logging
import time
import uuid
from functools import lru_cache
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, ValidationError

from app.config import config_hash, get_config, load_prompt
from app.llm import LLMClient, LLMError

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("gymrag.api")

# User-facing text stays in Vietnamese.
DISCLAIMER = "Thông tin chỉ mang tính tham khảo, không thay thế bác sĩ hay huấn luyện viên."

Status = Literal[
    "answered", "corrected_outdated", "contested",
    "no_answer", "out_of_scope", "safety_refusal",
]


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500)


class Citation(BaseModel):
    title: str
    doc_id: str | None = None          # filled from phase 2 (RAG)
    url: str | None = None
    published_year: int | None = None
    evidence_level: int | None = None


class Meta(BaseModel):
    request_id: str
    latency_ms: int
    tokens_in: int
    tokens_out: int
    cost_usd: float
    model: str
    prompt_version: str
    config_hash: str


class AskResponse(BaseModel):
    answer: str
    citations: list[Citation]
    status: Status
    disclaimer: str
    meta: Meta


class LLMAnswer(BaseModel):
    """The JSON shape we expect from the LLM. Never trust it without validating."""

    answer: str
    sources: list[str] = []
    status: Status


app = FastAPI(title="GymRAG", version="0.1.0")


@lru_cache
def get_llm() -> LLMClient:
    return LLMClient()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest) -> AskResponse:
    request_id = uuid.uuid4().hex[:12]
    prompt_version = get_config().prompt.version
    start = time.perf_counter()

    try:
        result = get_llm().chat(load_prompt(prompt_version), req.question, json_mode=True)
        parsed = LLMAnswer.model_validate_json(result.text)
    except LLMError as e:
        log.error(json.dumps({"event": "llm_error", "request_id": request_id, "error": str(e)}))
        raise HTTPException(503, "Hệ thống đang bận, vui lòng thử lại sau.") from e
    except ValidationError as e:
        log.error(json.dumps({"event": "bad_llm_output", "request_id": request_id,
                              "errors": e.error_count()}))
        raise HTTPException(502, "Không đọc được câu trả lời, vui lòng thử lại.") from e

    meta = Meta(
        request_id=request_id,
        latency_ms=int((time.perf_counter() - start) * 1000),
        tokens_in=result.tokens_in,
        tokens_out=result.tokens_out,
        cost_usd=result.cost_usd,
        model=result.model,
        prompt_version=prompt_version,
        config_hash=config_hash(),
    )
    log.info(json.dumps({"event": "ask", "status": parsed.status, **meta.model_dump()}))

    return AskResponse(
        answer=parsed.answer,
        citations=[Citation(title=s) for s in parsed.sources],
        status=parsed.status,
        disclaimer=DISCLAIMER,
        meta=meta,
    )
