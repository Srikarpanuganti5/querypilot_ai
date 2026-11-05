"""Day 9 public response fixture using the actual mock document path."""

import pytest
from fastapi.testclient import TestClient

from querypilot.core.config import Settings
from querypilot.main import create_app
from querypilot.schemas.agent import AgentResponse


@pytest.fixture
def document_response() -> AgentResponse:
    config = Settings(
        _env_file=None,
        database_url=None,
        reader_database_url=None,
        openai_api_key=None,
        openai_model=None,
        agent_live_enabled=False,
    )
    with TestClient(create_app(config)) as client:
        response = client.post(
            "/api/v1/agent/ask", json={"question": "What is our return policy?", "mode": "mock"}
        )
    assert response.status_code == 200
    return AgentResponse.model_validate(response.json())
