"""Load configuration: config.yaml (tunables, in Git) + .env (secrets, per machine)."""
import hashlib
import json
from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parent.parent  # repo root


class LLMConfig(BaseModel):
    temperature: float = 0.0
    max_tokens: int = 2048
    timeout_s: float = 30.0
    max_retries: int = 3


class PromptConfig(BaseModel):
    version: str = "answer_v1"


class AppConfig(BaseModel):
    llm: LLMConfig = LLMConfig()
    prompt: PromptConfig = PromptConfig()


class Settings(BaseSettings):
    """Read from env vars or .env (names are case-insensitive)."""

    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")

    llm_base_url: str
    llm_api_key: SecretStr          # printed as '**********'
    llm_model: str
    price_in_per_m: float = 0.0
    price_out_per_m: float = 0.0


@lru_cache  # read the file once, reuse afterwards
def get_config() -> AppConfig:
    data = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8")) or {}
    return AppConfig(**data)


@lru_cache
def get_settings() -> Settings:
    return Settings()


def load_prompt(version: str) -> str:
    return (ROOT / "prompts" / f"{version}.txt").read_text(encoding="utf-8")


def config_hash() -> str:
    """8-char fingerprint of the running config, attached to every result."""
    raw = json.dumps(get_config().model_dump(), sort_keys=True) + get_settings().llm_model
    return hashlib.sha256(raw.encode()).hexdigest()[:8]