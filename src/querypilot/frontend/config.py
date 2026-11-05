"""Frontend-only environment settings; never load the backend .env file."""

from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class FrontendSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="QUERYPILOT_", env_file=None, extra="ignore", hide_input_in_errors=True
    )
    api_base_url: AnyHttpUrl = "http://127.0.0.1:8000"

    @field_validator("api_base_url")
    @classmethod
    def plain_origin(cls, value: AnyHttpUrl) -> AnyHttpUrl:
        if (
            value.username
            or value.password
            or value.query
            or value.fragment
            or value.path not in ("/", "", None)
        ):
            raise ValueError("Use an HTTP(S) origin without credentials, path, query or fragment")
        return value
