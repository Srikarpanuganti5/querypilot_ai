"""Local-development agent API; live requests require explicit server opt-in."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from querypilot.api.errors import error_response
from querypilot.core.security import SecretGuard
from querypilot.schemas.agent import AgentCapabilities, AgentResponse, AskRequest
from querypilot.services.agent import execute_question

router = APIRouter(prefix="/agent", tags=["Agent"])


@router.get("/capabilities", response_model=AgentCapabilities)
async def capabilities(request: Request) -> AgentCapabilities:
    settings = request.app.state.settings
    return AgentCapabilities(
        live_enabled=settings.agent_live_enabled,
        live_configured=bool(
            settings.openai_api_key
            and settings.openai_api_key.get_secret_value().strip()
            and settings.openai_model
        ),
        execution_timeout_seconds=settings.agent_timeout_seconds,
        max_iterations=settings.agent_max_iterations,
        max_tool_calls=settings.agent_max_tool_calls,
        max_tools_per_iteration=settings.agent_max_tools_per_iteration,
    )


@router.post(
    "/ask",
    response_model=AgentResponse,
    responses={
        403: {"description": "Live execution disabled"},
        413: {"description": "Request body too large"},
    },
)
async def ask(payload: AskRequest, request: Request) -> AgentResponse | JSONResponse:
    settings = request.app.state.settings
    if payload.mode == "live" and not settings.agent_live_enabled:
        return error_response(
            request, 403, "live_disabled", "Live execution is disabled on this backend."
        )
    outcome = await execute_question(
        payload.question, live=payload.mode == "live", settings=settings
    )
    value = outcome.model_dump(mode="json", exclude={"tools"})
    value["request_id"] = request.state.request_id
    value["tools"] = [
        {
            **trace.model_dump(mode="json", exclude={"arguments", "call_id"}),
            "duration_ms": trace.result.duration_ms if trace.result else None,
        }
        for trace in outcome.tools
    ]
    return AgentResponse.model_validate(SecretGuard(settings).sanitize(value))
