"""Environment settings; constructing the app never contacts external services."""

from functools import lru_cache
from pathlib import Path
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
    documents_path: Path = Path("data/documents")
    openai_api_key: SecretStr | None = Field(default=None, validation_alias="OPENAI_API_KEY")
    openai_model: str | None = Field(default=None, validation_alias="OPENAI_MODEL")
    llm_request_timeout_seconds: float = Field(default=25, ge=0.05, le=120)
    llm_max_retries: int = Field(default=1, ge=0, le=2)
    llm_max_output_tokens: int = Field(default=1600, ge=256, le=4000)
    llm_max_tool_calls: int = Field(default=6, ge=1, le=6)
    llm_tool_timeout_seconds: float = Field(default=15, ge=0.01, le=60)
    llm_max_evidence_rows: int = Field(default=10, ge=1, le=20)
    llm_max_evidence_bytes: int = Field(default=12000, ge=1000, le=32000)
    llm_total_evidence_bytes: int = Field(default=48000, ge=2000, le=128000)
    agent_max_iterations: int = Field(default=5, ge=1, le=10)
    agent_max_tool_calls: int = Field(default=10, ge=1, le=20)
    agent_max_tools_per_iteration: int = Field(default=5, ge=1, le=6)
    agent_timeout_seconds: float = Field(default=90, ge=0.01, le=300)
    agent_max_context_bytes: int = Field(default=128000, ge=1000, le=512000)
    agent_max_messages: int = Field(default=128, ge=2, le=256)

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
