"""Multi-step mock/live ask command; live failures never substitute fake responses."""

import argparse
import asyncio
import json
import logging
from uuid import uuid4

from pydantic import ValidationError

from querypilot.agent.mock import MultiStepMockProvider
from querypilot.agent.multistep import MultiStepService
from querypilot.agent.provider import OpenAIProvider, ProviderError
from querypilot.core.config import Settings
from querypilot.core.logging import configure_logging
from querypilot.core.security import SecretGuard
from querypilot.schemas.llm import ExecutionError, ExecutionOutcome
from querypilot.tools.registry import create_registry


async def ask(question: str, *, live: bool, limits: dict | None = None) -> ExecutionOutcome:
    provider, registry, outcome = None, None, None
    try:
        settings = Settings(**limits) if limits else Settings()
        configure_logging(settings.log_level, settings=settings)
        provider = OpenAIProvider(settings) if live else MultiStepMockProvider()
        registry = create_registry(settings)
        outcome = await MultiStepService(provider, registry, settings).run(question)
    except (ProviderError, ValidationError) as exc:
        outcome = ExecutionOutcome(
            trace_id=str(uuid4()),
            mode="live" if live else "mock",
            question="",
            status="error",
            errors=[
                ExecutionError(
                    code=exc.code if isinstance(exc, ProviderError) else "configuration_error",
                    message=str(exc)
                    if isinstance(exc, ProviderError)
                    else "Invalid application settings.",
                )
            ],
        )
    finally:
        try:
            if provider is not None:
                await provider.close()
        except Exception:
            if outcome is not None:
                outcome.status, outcome.answer = "error", None
                outcome.errors = outcome.errors[:20] + [
                    ExecutionError(code="cleanup_error", message="Provider cleanup failed.")
                ]
            logging.getLogger("querypilot.llm").error(
                "cleanup_failed", extra={"error_category": "cleanup_error"}
            )
        finally:
            if registry is not None:
                try:
                    registry.close()
                except Exception:
                    if outcome is not None:
                        outcome.status, outcome.answer = "error", None
                        outcome.errors = outcome.errors[:20] + [
                            ExecutionError(code="cleanup_error", message="Tool cleanup failed.")
                        ]
                    logging.getLogger("querypilot.llm").error(
                        "cleanup_failed", extra={"error_category": "cleanup_error"}
                    )
    return outcome


def main(arguments: list[str]) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument(
        "--mock",
        action="store_true",
        help="Deterministic fake model, actual registry tools (default)",
    )
    modes.add_argument(
        "--live",
        action="store_true",
        help="Explicitly permit paid OpenAI requests using configured credentials",
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Include bounded tool evidence traces"
    )
    for flag, kind in (
        ("max-iterations", int),
        ("max-tool-calls", int),
        ("max-tools-per-iteration", int),
        ("timeout-seconds", float),
        ("max-context-bytes", int),
        ("max-messages", int),
    ):
        parser.add_argument(f"--{flag}", type=kind)
    args = parser.parse_args(arguments)
    limits = {
        f"agent_{name}": getattr(args, name)
        for name in (
            "max_iterations",
            "max_tool_calls",
            "max_tools_per_iteration",
            "timeout_seconds",
            "max_context_bytes",
            "max_messages",
        )
        if getattr(args, name) is not None
    }
    try:
        outcome = asyncio.run(ask(args.question, live=args.live, limits=limits))
    except KeyboardInterrupt:
        print(
            json.dumps(
                {
                    "status": "error",
                    "errors": [{"code": "request_cancelled", "message": "Request cancelled."}],
                }
            )
        )
        raise SystemExit(130) from None
    value = outcome.model_dump(mode="json")
    if not args.verbose:
        value.pop("question")
        value["tools"] = [
            {
                key: trace[key]
                for key in (
                    "evidence_id",
                    "tool",
                    "status",
                    "iteration",
                    "citations",
                    "output_truncated",
                    "error",
                )
            }
            for trace in value["tools"]
        ]
    print(json.dumps(SecretGuard().sanitize(value), ensure_ascii=False))
    if outcome.status == "error":
        raise SystemExit(1)
