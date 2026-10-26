"""Environment and dotenv configuration without application services."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from querypilot.core.config import Settings


def test_environment_overrides_dotenv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    env = tmp_path / "settings.env"
    env.write_text(
        'QUERYPILOT_LOG_LEVEL=WARNING\nQUERYPILOT_CORS_ORIGINS=["http://localhost:8501"]\n'
    )
    monkeypatch.setenv("QUERYPILOT_LOG_LEVEL", "DEBUG")
    monkeypatch.delenv("QUERYPILOT_CORS_ORIGINS", raising=False)
    settings = Settings(_env_file=env)
    assert settings.log_level == "DEBUG"
    assert settings.allowed_origins == ["http://localhost:8501"]


@pytest.mark.parametrize(
    "origin",
    [
        "*",
        "https://*.example.com",
        "not-a-url",
        "https://example.com/path",
        "https://user:password@example.com",
        "https://example.com?token=secret",
        "https://example.com#fragment",
    ],
)
def test_invalid_origins_rejected(origin: str) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, cors_origins=[origin])


def test_bad_log_level_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, log_level="INVALID")
