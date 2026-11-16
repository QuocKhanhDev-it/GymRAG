"""Shared test setup: fake settings, so tests never need a real .env or API key."""

import pytest

from app import config


@pytest.fixture(autouse=True)
def fake_env(monkeypatch):
    # Real env vars win over .env in pydantic-settings, so these replace your real values.
    monkeypatch.setenv("LLM_BASE_URL", "http://fake-llm.local/v1/")
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_MODEL", "fake-model")
    monkeypatch.setenv("PRICE_IN_PER_M", "1.0")
    monkeypatch.setenv("PRICE_OUT_PER_M", "2.0")
    config.get_settings.cache_clear()  # drop settings cached by a previous test
    config.get_config.cache_clear()
    yield
    config.get_settings.cache_clear()
    config.get_config.cache_clear()
