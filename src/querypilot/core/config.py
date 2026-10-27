"""Environment settings; constructing the app never contacts external services."""

from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="QUERYPILOT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
        hide_input_in_errors=True,
    )

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    cors_origins: list[AnyHttpUrl] = []
    database_url: SecretStr | None = Field(default=None, validation_alias="DATABASE_URL")
    reader_database_url: SecretStr | None = Field(
        default=None, validation_alias="READER_DATABASE_URL"
    )
    db_pool_size: int = Field(default=5, ge=1, le=20)
    db_max_overflow: int = Field(default=5, ge=0, le=20)
    db_pool_timeout: int = Field(default=5, ge=1, le=30)
    db_statement_timeout_ms: int = Field(default=5000, ge=100, le=30000)

    @field_validator("cors_origins")
    @classmethod
    def origins_only(cls, origins: list[AnyHttpUrl]) -> list[AnyHttpUrl]:
        for origin in origins:
            if (
                "*" in (origin.host or "")
                or origin.username
                or origin.password
                or origin.path not in (None, "/")
                or origin.query
                or origin.fragment
            ):
                raise ValueError("CORS origins must contain only scheme, host, and optional port")
        return origins

    @property
    def allowed_origins(self) -> list[str]:
        return [str(origin).rstrip("/") for origin in self.cors_origins]


@lru_cache
def get_settings() -> Settings:
    return Settings()
