"""Environment settings; constructing the app never contacts external services."""

from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="QUERYPILOT_", env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    cors_origins: list[AnyHttpUrl] = []

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
