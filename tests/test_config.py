"""Unit tests for config loading and cost math (no network)."""

from app.config import config_hash, get_config, load_prompt
from app.llm import LLMClient


def test_config_yaml_loads():
    cfg = get_config()
    assert cfg.llm.temperature == 0
    assert cfg.llm.max_retries >= 1


def test_configured_prompt_file_exists():
    # Catches a PR that bumps prompt.version but forgets to add the file
    assert load_prompt(get_config().prompt.version).strip()


def test_config_hash_is_stable():
    assert config_hash() == config_hash()
    assert len(config_hash()) == 8


def test_cost_uses_prices_from_env():
    llm = LLMClient()  # building the client makes no network call
    # 1M tokens in at $1 + 1M tokens out at $2 (fake prices from conftest.py)
    assert llm.cost(1_000_000, 1_000_000) == 3.0
