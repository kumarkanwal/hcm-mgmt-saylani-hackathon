from functools import lru_cache
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    database_url: str
    migration_database_url: str | None = None
    jwt_secret: str
    frontend_origin: str = "http://localhost:3000"
    company_timezone: str = "Asia/Karachi"
    company_name: str = "HCM Lite"
    admin_email: str | None = None
    admin_password: str | None = None
    test_database_url: str | None = None
    auth_login_rate_limit: str = "10/minute"
    setup_rate_limit: str = "5/minute"

    jwt_expire_hours: int = Field(default=8, ge=1, le=24)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_ignore_empty=True,
    )

    @field_validator("jwt_secret")
    @classmethod
    def validate_jwt_secret(cls, value: str) -> str:
        if len(value.encode("utf-8")) < 32:
            raise ValueError("JWT_SECRET must contain at least 32 bytes")
        return value

    @field_validator("company_timezone")
    @classmethod
    def validate_company_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("COMPANY_TIMEZONE must be a valid IANA timezone") from exc
        return value

    @property
    def frontend_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.frontend_origin.split(",")
            if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
