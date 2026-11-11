"""Real HTTP/container smoke, intended to run inside the backend Compose service."""

import argparse
import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from sqlalchemy import text

from querypilot.core.config import Settings
from querypilot.db.session import create_database
from querypilot.evaluation.dataset import load_dataset
from querypilot.evaluation.metrics import score_case
from querypilot.evaluation.runner import verify_fixture
from querypilot.schemas.agent import AgentResponse
from querypilot.services.document_search import DocumentIndex


def fetch(path: str, body: dict | None = None) -> tuple[int, dict]:
    request = Request(
        "http://127.0.0.1:8000" + path,
        data=json.dumps(body).encode() if body else None,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urlopen(request, timeout=120) as response:
            return response.status, json.load(response)
    except HTTPError as error:
        return error.code, json.load(error)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--unavailable", action="store_true")
    args = parser.parse_args()
    assert fetch("/health")[0] == 200
    if args.unavailable:
        assert fetch("/ready")[0] == 503
        print("PASS database unavailable: liveness 200, readiness 503")
        return
    settings = Settings()
    dataset, _ = load_dataset()
    fixture = verify_fixture(settings, dataset)
    index = DocumentIndex.from_directory(settings.documents_path)
    corpus = {c.citation: c.metadata.document_id for c in index.chunks}
    assert fetch("/ready")[0] == 200
    database = create_database(settings, reader=True)
    try:
        with database.transaction() as session:
            session.execute(text("SET TRANSACTION READ ONLY"))
            failed = session.scalar(
                text("SELECT count(*) FROM payments WHERE payment_status='failed'")
            )
    finally:
        database.close()
    for case in dataset.cases:
        if not case.id.startswith("accept-"):
            continue
        status, value = fetch("/api/v1/agent/ask", {"question": case.question, "mode": "mock"})
        outcome = AgentResponse.model_validate(value)
        assert status == 200 and score_case(case, outcome, corpus)["passed"]
        if case.id == "accept-failed-payments":
            rows = outcome.tools[0].result.data.rows
            assert next(r.payment_count for r in rows if r.payment_status == "failed") == failed
        print(f"PASS {case.id}: actual HTTP, mock provider, real tools")
    with urlopen("http://frontend:8501/_stcore/health", timeout=5) as response:
        assert response.status == 200
    print(
        json.dumps(
            {
                "failed_payment_attempts": failed,
                "fixture_sha256": fixture["sha256"],
                "frontend_reachable": True,
            }
        )
    )


if __name__ == "__main__":
    main()
