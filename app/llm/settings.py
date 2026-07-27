"""Environment-driven settings for LLM providers."""

from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMSettings(BaseSettings):
    """Typed LLM configuration loaded from environment variables."""

    provider: str = Field(default="openrouter")

    # API credentials and endpoints
    api_key: SecretStr = Field(default=SecretStr(""))
    base_url: str = Field(default="https://openrouter.ai/api/v1")
    model: str = Field(default="qwen/qwen3-omni")

    # App metadata for HTTP headers
    app_name: str = Field(default="MantraSetu AI Backend")
    app_url: str = Field(default="http://localhost:8000")

    # Timeout settings in seconds
    timeout_connect: float = Field(default=10.0, gt=0)
    timeout_read: float = Field(default=60.0, gt=0)
    timeout_write: float = Field(default=10.0, gt=0)
    timeout_pool: float = Field(default=10.0, gt=0)

    # Retry configuration
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
    """Return cached LLMSettings instance."""
    return LLMSettings()


llm_settings = get_llm_settings()
