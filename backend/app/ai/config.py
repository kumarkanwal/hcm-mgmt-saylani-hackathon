from zoneinfo import ZoneInfo

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", env_file=None)
    ai_provider: str = "gemini"
    ai_api_key: SecretStr = SecretStr("")
    ai_model: str = ""
    gemini_api_key: SecretStr = SecretStr("")
    gemini_model: str = ""
    ai_timeout_seconds: float = Field(15, gt=0, le=15)
    ai_rate_limit_per_hour: int = Field(20, ge=1, le=1000)
    ai_timezone: str = "Asia/Karachi"

    @field_validator("ai_provider")
    @classmethod
    def provider(cls, v):
        if v != "gemini":
            raise ValueError("Unsupported AI provider")
        return v

    @field_validator("ai_timezone")
    @classmethod
    def timezone(cls, v):
        try:
            ZoneInfo(v)
        except (KeyError, ValueError):
            raise ValueError("Invalid AI timezone") from None
        return v
