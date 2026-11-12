"""Bounded deployment probes using the existing typed client and acceptance references."""

import argparse
import json
import time

import httpx
from sqlalchemy import text

from querypilot.core.config import Settings
from querypilot.core.security import SecretGuard
from querypilot.db.session import create_database
from querypilot.evaluation.dataset import load_dataset
from querypilot.evaluation.metrics import score_case
from querypilot.evaluation.runner import verify_fixture
from querypilot.frontend.api_client import MAX_RESPONSE_BYTES, ApiClient, ClientError
from querypilot.frontend.config import FrontendSettings
from querypilot.schemas.agent import AskRequest
from querypilot.schemas.system import HealthResponse
from querypilot.services.document_search import DocumentIndex

REQUIRED_PATHS = {"/health", "/ready", "/api/v1/agent/capabilities", "/api/v1/agent/ask"}


def metadata(origin: str, path: str, transport: httpx.BaseTransport | None) -> dict:
    """System probes follow the same no-redirect, bounded, no-env-proxy policy as ApiClient."""
    with httpx.Client(
        base_url=origin,
        transport=transport,
        trust_env=False,
        follow_redirects=False,
        timeout=httpx.Timeout(5, connect=3),
    ) as client:
        with client.stream("GET", path) as response:
            if response.status_code != 200:
                raise ValueError("System prerequisite did not pass")
            raw = bytearray()
            for chunk in response.iter_bytes():
                raw.extend(chunk)
                if len(raw) > MAX_RESPONSE_BYTES:
                    raise ValueError("System response exceeded its limit")
            value = json.loads(raw)
            if not isinstance(value, dict):
                raise ValueError("System response must be an object")
            return value


def sql_snapshot(settings: Settings) -> dict:
    database = create_database(settings, reader=True)
    try:
        with database.transaction() as session:
            session.execute(text("SET TRANSACTION READ ONLY"))
            rows = session.execute(
                text(
                    "SELECT p.product_id, sum(i.quantity*i.unit_price) revenue FROM products p "
                    "JOIN order_items i USING(product_id) JOIN orders o USING(order_id) "
                    "WHERE o.status='completed' GROUP BY p.product_id "
                    "ORDER BY revenue DESC,p.product_id LIMIT 5"
                )
            ).all()
            failed = session.scalar(
                text("SELECT count(*) FROM payments WHERE payment_status='failed'")
            )
        return {"top_five": [[r[0], str(r[1])] for r in rows], "failed_payments": failed}
    finally:
        database.close()


def smoke_test(
    backend_url: str,
    settings: Settings,
    *,
    verify_database: bool = False,
    transport: httpx.BaseTransport | None = None,
) -> dict:
    started = time.perf_counter()
    checks, outcomes = [], []
    snapshot = None
    stage = "backend_liveness"
    try:
        origin = str(FrontendSettings(api_base_url=backend_url).api_base_url)
        health = HealthResponse.model_validate(metadata(origin, "/health", transport))
        if health.service != "querypilot-ai":
            raise ValueError("Wrong backend service")
        checks.append({"name": stage, "status": "PASS"})
        stage = "backend_readiness"
        ready = metadata(origin, "/ready", transport)
        required = {
            "database_connection",
            "required_tables",
            "restricted_reader",
            "seed_data",
            "documents",
            "mock_provider",
        }
        passed = {c["name"] for c in ready.get("checks", []) if c.get("status") == "PASS"}
        if (
            ready.get("status") != "ready"
            or not required <= passed
            or any(c.get("status") == "FAIL" for c in ready.get("checks", []))
        ):
            raise ValueError("Backend is not ready")
        checks.append({"name": stage, "status": "PASS"})
        stage = "api_contract"
        spec = metadata(origin, "/openapi.json", transport)
        if not REQUIRED_PATHS <= set(spec.get("paths", {})) or not spec.get(
            "openapi", ""
        ).startswith("3."):
            raise ValueError("Expected API contract missing")
        if any(
            ("post" if path.endswith("/ask") else "get") not in spec["paths"][path]
            for path in REQUIRED_PATHS
        ):
            raise ValueError("Expected API operations missing")
        api = ApiClient(FrontendSettings(api_base_url=origin), transport=transport)
        capabilities = api.capabilities()
        checks.append({"name": stage, "status": "PASS"})
        stage = "reference_data"
        dataset, checksum = load_dataset()
        acceptance = [c for c in dataset.cases if c.id.startswith("accept-")]
        if {c.id for c in acceptance} != {
            "accept-top-five",
            "accept-return-policy",
            "accept-revenue-refund",
            "accept-failed-payments",
        }:
            raise ValueError("Acceptance reference set incomplete")
        index = DocumentIndex.from_directory(settings.documents_path)
        corpus = {c.citation: c.metadata.document_id for c in index.chunks}
        if verify_database:
            stage = "direct_database"
            fixture = verify_fixture(settings, dataset)
            snapshot = sql_snapshot(settings)
            checks.append(
                {
                    "name": stage,
                    "status": "PASS",
                    "fixture_sha256": fixture["sha256"],
                    "failed_payment_attempts": snapshot["failed_payments"],
                }
            )
        else:
            checks.append(
                {
                    "name": "direct_database",
                    "status": "SKIP",
                    "code": "not_requested; backend database is not independently attested",
                }
            )
        for case in acceptance:
            stage = case.id
            attempt = time.perf_counter()
            try:
                response = api.ask(
                    AskRequest(question=case.question, mode="mock"),
                    execution_timeout_seconds=capabilities.execution_timeout_seconds,
                )
                score = score_case(case, response, corpus)
                good = score["passed"]
                if snapshot:
                    for trace in response.tools:
                        if trace.status != "success":
                            continue
                        if trace.tool == "get_top_products":
                            good &= [
                                [r.product_id, str(r.revenue)] for r in trace.result.data.rows
                            ] == snapshot["top_five"]
                        if trace.tool == "get_payment_status_summary":
                            good &= (
                                next(
                                    (
                                        r.payment_count
                                        for r in trace.result.data.rows
                                        if r.payment_status == "failed"
                                    ),
                                    None,
                                )
                                == snapshot["failed_payments"]
                            )
                checks.append(
                    {
                        "name": stage,
                        "status": "PASS" if good else "FAIL",
                        "failed_checks": [key for key, ok in score["checks"].items() if not ok],
                    }
                )
                outcomes.append(
                    {
                        "id": case.id,
                        "status": response.status,
                        "tools": [t.tool for t in response.tools],
                        "partial": response.partial,
                        "duration_ms": (time.perf_counter() - attempt) * 1000,
                    }
                )
            except ClientError as error:
                checks.append({"name": stage, "status": "FAIL", "code": error.code})
        dataset_version = dataset.version
    except Exception:
        checks.append({"name": stage, "status": "FAIL", "code": "prerequisite_or_contract_failed"})
        dataset_version, checksum = None, None
    return SecretGuard(settings).sanitize(
        {
            "passed": not any(c["status"] == "FAIL" for c in checks),
            "mode": "mock",
            "checks": checks,
            "cases": outcomes,
            "dataset_version": dataset_version,
            "dataset_sha256": checksum,
            "duration_ms": (time.perf_counter() - started) * 1000,
            "direct_database": "REAL DATABASE VERIFIED" if snapshot else "NOT VERIFIED",
            "semantic_faithfulness": "NOT EVALUATED",
            "live_openai": "NOT VERIFIED",
        }
    )


def main(arguments: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend-url")
    parser.add_argument("--verify-database", action="store_true")
    args = parser.parse_args(arguments)
    try:
        origin = args.backend_url or str(FrontendSettings().api_base_url)
        report = smoke_test(origin, Settings(), verify_database=args.verify_database)
    except Exception:
        raise SystemExit(
            "Smoke configuration failed safely; verify the backend origin/settings."
        ) from None
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["passed"] else 1)
