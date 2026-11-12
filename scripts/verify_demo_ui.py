"""Automated AppTest -> actual HTTP -> real tools; this is not manual browser acceptance."""

import argparse
import json
import os
from pathlib import Path

from streamlit.testing.v1 import AppTest

from querypilot.core.config import Settings
from querypilot.evaluation.dataset import load_dataset
from querypilot.evaluation.metrics import score_case
from querypilot.frontend.config import FrontendSettings
from querypilot.services.document_search import DocumentIndex


def verify(origin: str) -> dict:
    # Validate without echoing credentials/invalid URL input.
    settings = FrontendSettings(api_base_url=origin)
    old = os.environ.get("QUERYPILOT_API_BASE_URL")
    path = Path(__file__).resolve().parents[1] / "src/querypilot/frontend/app.py"
    dataset, _ = load_dataset()
    index = DocumentIndex.from_directory(Settings().documents_path)
    corpus = {chunk.citation: chunk.metadata.document_id for chunk in index.chunks}
    try:
        os.environ["QUERYPILOT_API_BASE_URL"] = str(settings.api_base_url)
        app = AppTest.from_file(str(path), default_timeout=30).run()
        assert not app.exception and app.selectbox[0].value == "Mock demo"
        for case in dataset.cases:
            if not case.id.startswith("accept-"):
                continue
            app.chat_input[0].set_value(case.question).run(timeout=30)
            assert not app.exception
            response = app.session_state.history[-1].response
            assert response.mode == "mock" and score_case(case, response, corpus)["passed"]
        assert len(app.chat_message) == 8 and len(app.dataframe) == 3 and len(app.code) == 3
        assert app.warning  # Selected top-five SQL evidence is explicitly limited.
        app.run()
        assert len(app.session_state.history) == 4
        app.button[0].click().run()
        assert not app.session_state.history and not app.chat_message
        os.environ["QUERYPILOT_API_BASE_URL"] = "http://127.0.0.1:1"
        unavailable = AppTest.from_file(str(path), default_timeout=15).run()
        assert not unavailable.exception and (unavailable.error or unavailable.warning)
        return dict(
            mode="mock",
            workflows=4,
            chat_messages=8,
            sql_tables=3,
            citations=3,
            rerun_preserved_history=True,
            clear_verified=True,
            backend_failure_presented=True,
            verification="AUTOMATED APPTEST + REAL HTTP; NOT MANUAL BROWSER",
        )
    finally:
        if old is None:
            os.environ.pop("QUERYPILOT_API_BASE_URL", None)
        else:
            os.environ["QUERYPILOT_API_BASE_URL"] = old


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend-url", required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(verify(args.backend_url), indent=2))
    except Exception:
        raise SystemExit("Automated UI verification failed; no raw diagnostics exposed.") from None
