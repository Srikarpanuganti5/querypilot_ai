"""Explicit mock/live ask command; live failures never substitute fake responses."""

import argparse
import asyncio
from uuid import uuid4

from pydantic import ValidationError

from querypilot.agent.mock import MockProvider
from querypilot.agent.orchestrator import SingleRoundService
from querypilot.agent.provider import OpenAIProvider, ProviderError
from querypilot.core.config import Settings
from querypilot.core.logging import configure_logging
from querypilot.schemas.llm import ExecutionError, ExecutionOutcome
from querypilot.tools.registry import create_registry


async def ask(question: str, *, live: bool) -> ExecutionOutcome:
    provider, registry = None, None
    try:
        settings = Settings()
        configure_logging(settings.log_level)
        provider = OpenAIProvider(settings) if live else MockProvider()
        registry = create_registry(settings)
        return await SingleRoundService(provider, registry, settings).run(question)
    except (ProviderError, ValidationError) as exc:
        return ExecutionOutcome(
            trace_id=str(uuid4()),
            mode="live" if live else "mock",
            question=question[:4000],
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
        if provider is not None:
            await provider.close()
        if registry is not None:
            registry.close()


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
    args = parser.parse_args(arguments)
    outcome = asyncio.run(ask(args.question, live=args.live))
    print(outcome.model_dump_json())
    if outcome.status == "error":
        raise SystemExit(1)
