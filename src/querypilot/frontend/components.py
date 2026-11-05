"""Safe Streamlit rendering: all untrusted narrative/source text is plain text."""

import streamlit as st

from querypilot.frontend.messages import message_for
from querypilot.schemas.agent import AgentResponse


def render_response(outcome: AgentResponse) -> None:
    st.caption("Mock demonstration" if outcome.mode == "mock" else "Live OpenAI execution")
    if outcome.partial:
        st.warning("Partial or limited evidence. Review the execution and evidence panels.")
    if any(error.code == "evidence_conflict" for error in outcome.errors):
        st.error("Conflicting evidence: a combined answer was withheld.")
    if outcome.answer:
        st.text(outcome.answer)
    elif outcome.status == "error":
        st.error("No answer was produced. Earlier evidence may still be available below.")
    if outcome.status == "no_evidence":
        st.info("No reliable nonempty evidence is available for this question.")
    for error in outcome.errors:
        st.warning(message_for(error.code))
    if outcome.grounding_checks == "passed":
        st.caption(
            "Evidence-reference checks passed. These checks do not prove every claim is correct."
        )
    elif outcome.grounding_checks == "failed":
        st.caption("Answer withheld because evidence-reference checks failed.")
    with st.expander("Execution details"):
        st.caption(f"Request {outcome.request_id} • Agent trace {outcome.trace_id}")
        st.write(
            f"Status: {outcome.status} · Iterations: {outcome.iterations} · "
            f"Tool calls: {len(outcome.tools)} · Duration: {outcome.elapsed_ms / 1000:.2f} s"
        )
        if outcome.pending_tool_calls:
            st.warning(f"Unresolved batch calls: {outcome.pending_tool_calls}")
        if outcome.limitations:
            st.text("Limitations: " + ", ".join(outcome.limitations))
        for index, trace in enumerate(outcome.tools, 1):
            duration = f" · {trace.duration_ms} ms" if trace.duration_ms is not None else ""
            st.text(
                f"{index}. Iteration {trace.iteration} · "
                f"{trace.tool or 'Rejected tool'} · {trace.status}{duration}"
            )
    with st.expander("Supporting evidence and citations"):
        available = False
        for trace in outcome.tools:
            if not trace.result or trace.result.status != "success":
                continue
            data = trace.result.data
            st.caption(f"{trace.evidence_id} · {trace.tool}")
            if trace.output_truncated or getattr(data, "truncated", False):
                st.warning(
                    "Selected or truncated records: "
                    "this evidence does not establish complete totals."
                )
            if trace.tool == "search_business_documents":
                for hit in data.matches:
                    available = True
                    st.text(f"{hit.document_title} · {hit.section}")
                    st.code(hit.source_citation, language=None)
                    st.text(hit.excerpt)
            elif data.rows:
                available = True
                st.dataframe(
                    [row.model_dump(mode="json") for row in data.rows],
                    hide_index=True,
                    width="stretch",
                )
        if not available:
            st.info("No successful nonempty evidence to display.")
