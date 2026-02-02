"""Gateway configuration from environment."""

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openclaw_worker_url: str = "http://127.0.0.1:18789"
    openclaw_worker_token: str = ""
    port: int = 8000

    @field_validator("openclaw_worker_token", mode="before")
    @classmethod
    def strip_token(cls, v: str) -> str:
        return (v or "").strip()


def get_settings() -> Settings:
    return Settings()
