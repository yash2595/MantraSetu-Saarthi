"""Environment-driven configuration for LLM providers."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMSettings(BaseSettings):
    """Typed LLM configuration loaded from environment variables."""

    provider: str = Field(default="qwen")
    timeout_seconds: float = Field(default=30.0, gt=0)
    max_retries: int = Field(default=2, ge=0)
    retry_backoff_seconds: float = Field(default=0.5, ge=0)
    qwen_base_url: str = Field(default="https://dashscope.aliyuncs.com/compatible-mode/v1")
    qwen_api_key: str = Field(default="")
    qwen_model: str = Field(default="qwen-plus")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_prefix="LLM_",
    )


@lru_cache(maxsize=1)
def get_llm_settings() -> LLMSettings:
    """Return cached LLM settings."""
    return LLMSettings()
