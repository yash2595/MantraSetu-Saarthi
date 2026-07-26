"""Environment-driven configuration for LLM providers."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMSettings(BaseSettings):
    """Typed LLM configuration loaded from environment variables."""

    # Provider
    provider: str = Field(default="openrouter")

    # API
    api_key: str = Field(default="")
    base_url: str = Field(default="https://openrouter.ai/api/v1")
    model: str = Field(default="qwen/qwen3-omni")

    # App metadata
    app_name: str = Field(default="MantraSetu AI Backend")
    app_url: str = Field(default="http://localhost:8000")

    # Retry & timeout
    timeout_seconds: float = Field(default=60.0, gt=0)
    max_retries: int = Field(default=2, ge=0)
    retry_backoff_seconds: float = Field(default=2.0, ge=0)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="",
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_llm_settings() -> LLMSettings:
    """Return cached LLM settings."""
    return LLMSettings()