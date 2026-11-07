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


@pytest.fixture(scope="session")
def integration_settings() -> Settings:
    from datetime import date

    from querypilot.db.session import create_database
    from querypilot.db.verify import verify_database
    from tests.postgres_support import test_urls

    writer, reader = test_urls()
    settings = Settings(
        _env_file=None,
        database_url=writer,
        reader_database_url=reader,
        openai_api_key=None,
        openai_model=None,
        agent_live_enabled=False,
    )
    database = create_database(settings, reader=True)
    try:
        verify_database(database, date(2026, 10, 27))
    finally:
        database.close()
    return settings


@pytest.fixture(scope="session")
def integration_backend(integration_settings):
    """Real TCP HTTP server, with real tools and a dedicated synthetic PostgreSQL DB."""
    import socket
    import threading
    import time

    import uvicorn

    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    sock.listen(128)
    port = sock.getsockname()[1]
    server = uvicorn.Server(
        uvicorn.Config(
            create_app(integration_settings), host="127.0.0.1", log_config=None, access_log=False
        )
    )
    thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
    thread.start()
    deadline = time.monotonic() + 20
    while not server.started and thread.is_alive() and time.monotonic() < deadline:
        threading.Event().wait(0.05)
    try:
        assert server.started, "Isolated HTTP server failed to start"
        yield f"http://127.0.0.1:{port}"
    finally:
        server.should_exit = True
        thread.join(timeout=20)
        sock.close()
        assert not thread.is_alive(), "Isolated HTTP server did not shut down"
