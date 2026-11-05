"""Fixed UI diagnostics; never display arbitrary HTTP/provider exception text."""

MESSAGES = {
    "backend_unavailable": "Cannot reach the backend. Start FastAPI, then reconnect.",
    "request_timeout": "The request timed out. The backend may still finish; no retry was sent.",
    "invalid_response": "The backend returned an incompatible response. Check both app versions.",
    "invalid_question": "Enter a question of 1–4000 characters.",
    "live_disabled": "Live execution is disabled on this backend.",
    "configuration_error": "Configure backend model credentials or read-only database settings.",
    "authentication_error": "The provider rejected the backend credentials.",
    "rate_limit": "The provider rate limit was reached. Wait before submitting again.",
    "provider_timeout": "The model request timed out.",
    "network_error": "The backend could not reach the model provider.",
    "provider_error": "The model provider could not complete the request.",
    "provider_response_error": "The model returned an invalid response.",
    "database_error": "The analytics database is unavailable.",
    "unsafe_database": "The backend database role does not satisfy read-only requirements.",
    "document_error": "The business document collection is unavailable.",
    "timeout": "The analytics query timed out.",
    "agent_timeout": "The agent execution deadline was reached.",
    "tool_timeout": "A tool timed out; subsequent work was stopped.",
    "iteration_limit": "The iteration limit was reached. Try a narrower question.",
    "tool_limit": "The tool-call limit was reached. Try a narrower question.",
    "context_limit": "The context budget was reached. Try a narrower question.",
    "message_limit": "The message budget was reached. Try a narrower question.",
    "evidence_limit": "The evidence budget was reached.",
    "evidence_conflict": "Retrieved evidence conflicts. A combined answer was withheld.",
    "grounding_error": "The answer failed evidence checks and was withheld.",
    "sensitive_input": "Remove credential-like content from your question.",
    "sensitive_output": "Credential-like content was withheld by the backend.",
    "unknown_tool": "An unapproved tool request was rejected.",
    "invalid_json": "The model supplied malformed tool arguments.",
    "invalid_arguments": "The model supplied invalid tool arguments.",
    "repeated_call": "A repeated tool call was skipped.",
    "cleanup_error": "Resource cleanup failed. Inspect backend status before retrying.",
    "payload_too_large": "The request exceeded the backend size limit.",
    "validation_error": "The backend rejected the request. Check your question and mode.",
    "execution_error": "The request could not be completed. You can submit a new question.",
}


def message_for(code: str) -> str:
    return MESSAGES.get(code, MESSAGES["execution_error"])
