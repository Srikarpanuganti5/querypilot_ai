"""Read-only local readiness checks; never migrate, seed, reset or call OpenAI."""

import argparse
import asyncio
from datetime import date
from typing import Literal

from alembic.config import Config
from alembic.script import ScriptDirectory
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import func, inspect, select, text

from querypilot.agent.mock import MultiStepMockProvider
from querypilot.agent.tool_schemas import function_schemas
from querypilot.core.config import Settings
from querypilot.db.analytics import UnsafeDatabaseError, _check_reader
from querypilot.db.models import Base
from querypilot.db.session import DATABASE_MESSAGES, DatabaseError, create_database, database_url
from querypilot.db.verify import VerificationError, verify_database
from querypilot.frontend.api_client import ApiClient, ClientError
from querypilot.frontend.config import FrontendSettings
from querypilot.schemas.documents import DocumentSearchInput
from querypilot.services.document_search import DocumentError, DocumentIndex
from querypilot.tools.registry import ToolRegistry


class Check(BaseModel):
    name: str
    status: Literal["PASS", "FAIL", "SKIP"]
    code: str
    message: str
    counts: dict[str, int] = Field(default_factory=dict)


class DoctorReport(BaseModel):
    checks: list[Check]

    @property
    def failed(self) -> bool:
        return any(check.status == "FAIL" for check in self.checks)


def diagnose(
    settings: Settings, *, backend_url: str | None = None, reference_date: date | None = None
) -> DoctorReport:
    checks = [
        Check(
            name="configuration",
            status="PASS",
            code="valid",
            message="Settings validated; no values are printed.",
        )
    ]
    database = None
    stage = "database_connection"
    downstream = ["required_tables", "restricted_reader", "seed_data"]
    try:
        database = create_database(settings, reader=True)
        with database.transaction() as session:
            session.execute(text("SET TRANSACTION READ ONLY"))
            session.scalar(text("SELECT 1"))
            checks.append(
                Check(
                    name=stage,
                    status="PASS",
                    code="reachable",
                    message="Configured reader connected to PostgreSQL.",
                )
            )
            stage = "required_tables"
            names = set(inspect(session.connection()).get_table_names())
            if not set(Base.metadata.tables) <= names:
                raise DatabaseError(
                    DATABASE_MESSAGES["database_schema_missing"], code="database_schema_missing"
                )
            checks.append(
                Check(
                    name=stage,
                    status="PASS",
                    code="tables_present",
                    message="All six analytics tables exist.",
                )
            )
            stage = "restricted_reader"
            _check_reader(session)
            checks.append(
                Check(
                    name=stage,
                    status="PASS",
                    code="restricted",
                    message="Reader ownership, memberships and SELECT-only privileges verified.",
                )
            )
            stage = "seed_data"
            counts = {
                table.name: session.scalar(select(func.count()).select_from(table))
                for table in Base.metadata.sorted_tables
            }
            present = all(counts.values())
            checks.append(
                Check(
                    name=stage,
                    status="PASS" if present else "FAIL",
                    code="rows_present" if present else "seed_missing",
                    message="Analytics tables contain data."
                    if present
                    else "Analytics tables are empty; load the synthetic fixture.",
                    counts=counts,
                )
            )
        if reference_date is not None:
            verify_database(database, reference_date)
            checks.append(
                Check(
                    name="fixture",
                    status="PASS",
                    code="fixture_verified",
                    message="Fixture counts, schema, foreign keys and accounting passed.",
                )
            )
        else:
            checks.append(
                Check(
                    name="fixture",
                    status="SKIP",
                    code="reference_date_needed",
                    message="Use --reference-date to verify the full synthetic fixture.",
                )
            )
    except (DatabaseError, UnsafeDatabaseError, VerificationError) as exc:
        code = (
            exc.code
            if isinstance(exc, DatabaseError)
            else "unsafe_database"
            if isinstance(exc, UnsafeDatabaseError)
            else "fixture_mismatch"
        )
        checks.append(
            Check(
                name="fixture" if isinstance(exc, VerificationError) else stage,
                status="FAIL",
                code=code,
                message=DATABASE_MESSAGES.get(
                    code, "Reader privileges or synthetic fixture verification failed."
                ),
            )
        )
        checked = {check.name for check in checks}
        for name in downstream + ["fixture"]:
            if name not in checked:
                checks.append(
                    Check(
                        name=name,
                        status="SKIP",
                        code="prerequisite_failed",
                        message="A database prerequisite failed; this check was not run.",
                    )
                )
    finally:
        if database:
            database.close()
    writer = None
    try:
        if not settings.database_url or not settings.database_url.get_secret_value():
            checks.append(
                Check(
                    name="migrations",
                    status="SKIP",
                    code="setup_url_needed",
                    message="No setup URL configured; exact Alembic revision was not checked.",
                )
            )
        else:
            writer_target, reader_target = (
                database_url(settings),
                database_url(settings, reader=True),
            )
            if (writer_target.host, writer_target.port, writer_target.database) != (
                reader_target.host,
                reader_target.port,
                reader_target.database,
            ):
                raise ValueError("Targets differ")
            writer = create_database(settings)
            with writer.transaction() as session:
                session.execute(text("SET TRANSACTION READ ONLY"))
                revisions = set(session.scalars(text("SELECT version_num FROM alembic_version")))
                expected = set(ScriptDirectory.from_config(Config("alembic.ini")).get_heads())
            checks.append(
                Check(
                    name="migrations",
                    status="PASS" if revisions == expected else "FAIL",
                    code="revision_current" if revisions == expected else "migration_mismatch",
                    message="Alembic revision matches repository head."
                    if revisions == expected
                    else "Alembic revision differs from repository head.",
                )
            )
    except (DatabaseError, ValueError):
        checks.append(
            Check(
                name="migrations",
                status="FAIL",
                code="migration_check_failed",
                message="Migration revision could not be verified against the same database.",
            )
        )
    finally:
        if writer:
            writer.close()
    try:
        index = DocumentIndex.from_directory(settings.documents_path)
        result = index.search(DocumentSearchInput(query="product return window", top_k=1))
        checks.append(
            Check(
                name="documents",
                status="PASS" if result.matches else "FAIL",
                code="passages_found" if result.matches else "documents_empty",
                message="Local corpus search returned a validated passage."
                if result.matches
                else "No policy passages found.",
            )
        )
    except DocumentError:
        checks.append(
            Check(
                name="documents",
                status="FAIL",
                code="document_error",
                message="Local document collection is unavailable.",
            )
        )

    async def mock_check() -> bool:
        provider = MultiStepMockProvider()
        try:
            turn = await provider.respond(
                "",
                [{"role": "user", "content": "Top products by revenue?"}],
                function_schemas(ToolRegistry(settings=settings).definitions()),
            )
            return turn.output[0]["name"] == "get_top_products"
        finally:
            await provider.close()

    ready = asyncio.run(mock_check())
    checks.append(
        Check(
            name="mock_provider",
            status="PASS" if ready else "FAIL",
            code="mock_ready" if ready else "mock_unavailable",
            message="Deterministic provider selects the approved analytics tool; no OpenAI call.",
        )
    )
    if backend_url is None:
        checks.append(
            Check(
                name="backend",
                status="SKIP",
                code="url_not_requested",
                message="Use --backend-url to check a running API.",
            )
        )
    else:
        try:
            ApiClient(FrontendSettings(api_base_url=backend_url)).capabilities()
            checks.append(
                Check(
                    name="backend",
                    status="PASS",
                    code="http_reachable",
                    message="API capabilities are reachable; SQL execution was not checked here.",
                )
            )
        except (ClientError, ValidationError):
            checks.append(
                Check(
                    name="backend",
                    status="FAIL",
                    code="backend_unavailable",
                    message="The configured backend could not be verified.",
                )
            )
    return DoctorReport(checks=checks)


def main(arguments: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend-url")
    parser.add_argument("--reference-date", type=date.fromisoformat)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(arguments)
    try:
        report = diagnose(
            Settings(), backend_url=args.backend_url, reference_date=args.reference_date
        )
    except Exception:
        report = DoctorReport(
            checks=[
                Check(
                    name="configuration",
                    status="FAIL",
                    code="diagnostic_error",
                    message="Diagnostics failed. Check settings and run from the repository root; "
                    "secret values are withheld.",
                )
            ]
        )
    if args.json:
        print(report.model_dump_json())
    else:
        for check in report.checks:
            print(f"{check.status} {check.name}: {check.message} [{check.code}]")
    if report.failed:
        raise SystemExit(1)
