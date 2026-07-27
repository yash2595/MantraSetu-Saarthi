"""Environment-driven settings for Session Management."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class SessionSettings(BaseSettings):
    """Typed Session configuration loaded from environment variables."""

    ttl_seconds: int = Field(default=3600, gt=0, description="Session TTL in seconds.")
    max_history_length: int = Field(default=50, gt=0, description="Max messages per session.")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="SESSION_",
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_session_settings() -> SessionSettings:
    """Return cached SessionSettings instance."""
    return SessionSettings()


session_settings = get_session_settings()
