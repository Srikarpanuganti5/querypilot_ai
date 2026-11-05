"""Call an approved SQL or document tool using --arguments with a JSON object."""

import argparse
import json
import sys

from pydantic import ValidationError

from querypilot.core.config import Settings
from querypilot.core.logging import configure_logging
from querypilot.db.session import DatabaseError
from querypilot.schemas.analytics import ToolError, ToolResult
from querypilot.tools.registry import create_registry


def main() -> None:
    if sys.argv[1:2] == ["ask"]:
        from querypilot.agent.cli import main as ask_main

        ask_main(sys.argv[2:])
        return
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tool")
    parser.add_argument("--arguments", default="{}", help="JSON object of tool arguments")
    args = parser.parse_args()
    registry = None
    try:
        arguments = json.loads(args.arguments)
        settings = Settings()
        configure_logging(settings.log_level, settings=settings)
        registry = create_registry(settings)
        result = registry.execute(args.tool, arguments)
        print(result.model_dump_json())
        if result.status == "error":
            raise SystemExit(1)
    except json.JSONDecodeError:
        print(
            ToolResult(
                tool=None,
                status="error",
                duration_ms=0,
                error=ToolError(code="invalid_arguments", message="Arguments must be JSON."),
            ).model_dump_json()
        )
        raise SystemExit(1) from None
    except (DatabaseError, ValidationError):
        print(
            ToolResult(
                tool=None,
                status="error",
                duration_ms=0,
                error=ToolError(
                    code="configuration_error",
                    message="Check local tool configuration; SQL requires READER_DATABASE_URL.",
                ),
            ).model_dump_json()
        )
        raise SystemExit(1) from None
    finally:
        if registry is not None:
            registry.close()


if __name__ == "__main__":
    main()
