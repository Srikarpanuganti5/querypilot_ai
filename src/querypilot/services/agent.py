"""One request lifecycle shared by HTTP and CLI; orchestration stays in the agent."""

import logging
from collections.abc import Callable
from uuid import uuid4

from pydantic import ValidationError

from querypilot.agent.mock import MultiStepMockProvider
from querypilot.agent.multistep import MultiStepService
from querypilot.agent.provider import ModelProvider, OpenAIProvider, ProviderError
from querypilot.core.config import Settings
from querypilot.schemas.llm import ExecutionError, ExecutionOutcome
from querypilot.tools.registry import ToolRegistry, create_registry


async def execute_question(
    question: str,
    *,
    live: bool,
    settings: Settings,
    provider_factory: Callable[[Settings], ModelProvider] | None = None,
    registry_factory: Callable[[Settings], ToolRegistry] = create_registry,
) -> ExecutionOutcome:
    provider, registry, outcome = None, None, None
    try:
        factory = provider_factory or (
            lambda config: OpenAIProvider(config) if live else MultiStepMockProvider()
        )
        provider = factory(settings)
        registry = registry_factory(settings)
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
