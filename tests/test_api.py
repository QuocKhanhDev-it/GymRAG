"""API tests with a fake LLM: fast, free, no network."""

import json

import pytest
from fastapi.testclient import TestClient

from app import api
from app.llm import LLMError, LLMResult

GOOD_REPLY = json.dumps(
    {"answer": "Khoảng 1,6 g/kg mỗi ngày.", "sources": ["ISSN 2017"], "status": "answered"}
)
QUESTION = {"question": "Ăn bao nhiêu protein mỗi ngày để tăng cơ?"}


class FakeLLM:
    """Stands in for LLMClient: returns a canned reply or raises an error."""

    def __init__(self, text: str = "", error: Exception | None = None) -> None:
        self.text = text
        self.error = error
        self.calls = 0

    def chat(self, system: str, user: str, json_mode: bool = False) -> LLMResult:
        self.calls += 1
        if self.error:
            raise self.error
        return LLMResult(
            text=self.text,
            tokens_in=100,
            tokens_out=50,
            cost_usd=0.0002,
            latency_ms=10,
            model="fake-model",
        )


def client_with(monkeypatch, fake: FakeLLM) -> TestClient:
    monkeypatch.setattr(api, "get_llm", lambda: fake)  # swap the single LLM gateway
    return TestClient(api.app)


def test_health():
    assert TestClient(api.app).get("/health").json() == {"status": "ok"}


def test_ask_follows_api_contract(monkeypatch):
    resp = client_with(monkeypatch, FakeLLM(text=GOOD_REPLY)).post("/ask", json=QUESTION)

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "answered"
    assert body["citations"][0]["title"] == "ISSN 2017"
    assert body["disclaimer"]
    assert body["meta"]["tokens_in"] == 100
    assert body["meta"]["prompt_version"] == "answer_v1"
    assert len(body["meta"]["config_hash"]) == 8


@pytest.mark.parametrize("payload", [{"question": "hi"}, {"q": "Ăn bao nhiêu protein?"}, {}])
def test_bad_request_is_422_and_costs_nothing(monkeypatch, payload):
    fake = FakeLLM(text=GOOD_REPLY)
    resp = client_with(monkeypatch, fake).post("/ask", json=payload)

    assert resp.status_code == 422
    assert fake.calls == 0  # rejected before any token is spent


def test_llm_failure_is_503(monkeypatch):
    resp = client_with(monkeypatch, FakeLLM(error=LLMError("boom"))).post("/ask", json=QUESTION)
    assert resp.status_code == 503


@pytest.mark.parametrize(
    "reply",
    ["not json at all", '{"answer": "x"}', '{"answer": "x", "status": "maybe"}'],
)
def test_bad_llm_output_is_502(monkeypatch, reply):
    resp = client_with(monkeypatch, FakeLLM(text=reply)).post("/ask", json=QUESTION)
    assert resp.status_code == 502
