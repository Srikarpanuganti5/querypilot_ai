"""Run: streamlit run src/querypilot/frontend/app.py --server.address 127.0.0.1"""

from dataclasses import dataclass
from typing import Literal

import streamlit as st
from pydantic import ValidationError

from querypilot.core.security import SecretGuard
from querypilot.frontend.api_client import ApiClient, ClientError
from querypilot.frontend.components import render_response
from querypilot.frontend.config import FrontendSettings
from querypilot.frontend.messages import message_for
from querypilot.schemas.agent import AgentResponse, AskRequest

EXAMPLES = (
    "What are our top five products by revenue?",
    "What is our return policy?",
    "Which products generated the most revenue, and what is our refund policy?",
    "How are failed payments handled?",
)


@dataclass
class ChatTurn:
    question: str
    mode: Literal["mock", "live"]
    response: AgentResponse | None = None
    error: str | None = None


def queue_question() -> None:
    if st.session_state.busy or st.session_state.get("pending"):
        return
    try:
        request = AskRequest(
            question=st.session_state.question_input,
            mode="live" if st.session_state.mode == "Live OpenAI" else "mock",
        )
        if SecretGuard().contains(request.question):
            raise ClientError("sensitive_input")
    except ValidationError:
        st.session_state.input_error = "invalid_question"
        return
    except ClientError as exc:
        st.session_state.input_error = exc.code
        return
    st.session_state.pending = request
    st.session_state.busy = True
    st.session_state.input_error = None


def clear_history() -> None:
    if not st.session_state.busy:
        st.session_state.history = []
        st.session_state.pop("pending", None)
        st.session_state.input_error = None
        st.session_state.question_input = ""


def fill_example(question: str) -> None:
    st.session_state.question_input = question


def main() -> None:
    st.set_page_config(page_title="QueryPilot AI", page_icon="🔎", layout="wide")
    for key, value in {"history": [], "busy": False, "input_error": None}.items():
        st.session_state.setdefault(key, value)
    st.title("QueryPilot AI")
    st.write("Ask questions about business data and policies using an AI-powered agent.")
    try:
        client = ApiClient(FrontendSettings())
    except ValidationError:
        st.error("Invalid frontend API URL configuration. Check QUERYPILOT_API_BASE_URL.")
        st.stop()
    capabilities, connection_error = None, None
    try:
        capabilities = client.capabilities()
    except ClientError as exc:
        connection_error = exc.code
    with st.sidebar:
        st.subheader("Workspace")
        selected = st.selectbox(
            "Execution mode",
            ["Mock demo", "Live OpenAI"],
            key="mode",
            disabled=st.session_state.busy,
        )
        st.caption(
            "Mock uses deterministic model fixtures and real approved tools. "
            "Live submissions may incur API charges."
        )
        st.button("Clear conversation", on_click=clear_history, disabled=st.session_state.busy)
        st.button("Reconnect", disabled=st.session_state.busy)
        st.divider()
        st.subheader("Try a question")
        st.caption("Choose an example to fill the composer, then send it.")
        for index, question in enumerate(EXAMPLES):
            st.button(
                question,
                key=f"example_{index}",
                on_click=fill_example,
                args=(question,),
                disabled=st.session_state.busy,
                width="stretch",
            )
        st.divider()
        st.caption(
            "Tools: top products, revenue, refunds, customer order aggregates, "
            "payment summaries, and business document search."
        )
        if capabilities:
            st.caption(
                f"Server limits: {capabilities.max_iterations} iterations · "
                f"{capabilities.max_tool_calls} tool calls · "
                f"{capabilities.max_tools_per_iteration} per round · "
                f"{capabilities.execution_timeout_seconds:g} s"
            )
        st.caption("Local development · Synthetic data only")
    mode = "live" if selected == "Live OpenAI" else "mock"
    st.caption(
        f"{'Live OpenAI' if mode == 'live' else 'Mock demonstration'} · "
        f"Backend {'connected' if capabilities else 'unavailable'}"
    )
    ready = capabilities is not None
    if connection_error:
        st.error(message_for(connection_error))
    if mode == "live" and capabilities:
        if not capabilities.live_enabled:
            st.warning(message_for("live_disabled"))
            ready = False
        elif not capabilities.live_configured:
            st.warning(message_for("configuration_error"))
            ready = False
    st.caption(
        "Each question runs independently. Displayed history is not sent as agent memory. "
        "Showing up to 20 recent questions."
    )
    if not st.session_state.history:
        st.info(
            "Ask about product revenue or a business policy. Start with an example in the sidebar."
        )
    for turn in st.session_state.history:
        with st.chat_message("user"):
            st.text(turn.question)
        with st.chat_message("assistant"):
            if turn.response:
                render_response(turn.response)
            else:
                st.error(message_for(turn.error or "execution_error"))
    if st.session_state.input_error:
        st.warning(message_for(st.session_state.input_error))
    st.chat_input(
        "Ask a business question…",
        key="question_input",
        max_chars=4000,
        disabled=st.session_state.busy or not ready,
        on_submit=queue_question,
    )
    pending = st.session_state.get("pending")
    if pending:
        with st.chat_message("user"):
            st.text(pending.question)
        with (
            st.chat_message("assistant"),
            st.status("Retrieving evidence…", expanded=True) as progress,
        ):
            turn = ChatTurn(question=pending.question, mode=pending.mode)
            try:
                if not ready:
                    raise ClientError(connection_error or "live_disabled")
                turn.response = client.ask(
                    pending, execution_timeout_seconds=capabilities.execution_timeout_seconds
                )
                if turn.response.question:
                    turn.question = turn.response.question
                progress.update(
                    label="Execution finished",
                    state="error" if turn.response.status == "error" else "complete",
                )
            except ClientError as exc:
                turn.error = exc.code
                progress.update(label="Request could not finish", state="error")
            except Exception:
                turn.error = "execution_error"
                progress.update(label="Request could not finish", state="error")
            finally:
                st.session_state.history = (st.session_state.history + [turn])[-20:]
                st.session_state.pop("pending", None)
                st.session_state.busy = False
        st.rerun()


if __name__ == "__main__":
    main()
