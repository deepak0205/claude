"""Streamlit UI. Calls the FastAPI backend only — renders exactly what's returned, no fabrication.

The user supplies their own Groq API key here; it's kept only in this browser session's
state and sent with each request — never written to disk by this app.
"""
import os
from pathlib import Path

import pandas as pd
import requests
import streamlit as st

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
GRAPH_PATH = Path(__file__).resolve().parent.parent / "graphify-out" / "graph.html"

st.set_page_config(page_title="Claude Healthcare Case Studies", page_icon="🩺", layout="wide")

st.markdown(
    """
    <div style="padding: 1.1rem 1.4rem; border-radius: 12px;
                background: linear-gradient(135deg, #7C6CF5 0%, #4B3FBF 100%);
                margin-bottom: 1rem;">
        <h1 style="color: white; margin: 0; font-size: 1.8rem;">
            🩺 Claude in Healthcare — Case Study Assistant
        </h1>
        <p style="color: rgba(255,255,255,0.85); margin: 0.3rem 0 0 0;">
            Ask about Banner Health, Qualified Health, Carta Healthcare, Elation Health, or Commure.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.subheader("Groq API Key")
    st.session_state.api_key = st.text_input(
        "Groq API key",
        value=st.session_state.get("api_key", ""),
        type="password",
        help="Used to call openai/gpt-oss-120b via Groq. Kept only in this session, sent with each request.",
    )
    st.caption("Get a key at [console.groq.com](https://console.groq.com/keys).")
    st.divider()
    st.caption("v1.0.0")

tab_chat, tab_analytics = st.tabs(["💬 Chat", "📊 Analytics"])


def render_traffic_dashboard() -> None:
    if st.button("🔄 Refresh traffic data"):
        st.rerun()
    try:
        resp = requests.get(f"{BACKEND_URL}/metrics", timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as exc:
        st.error(f"Could not reach backend metrics: {exc}")
        return

    col1, col2, col3 = st.columns(3)
    col1.metric("Total requests", data["total_requests"])
    col2.metric("Avg latency (ms)", f"{data['avg_latency_ms']:.0f}")
    recent = data["recent_requests"]
    col3.metric("Recent requests tracked", len(recent))

    if not recent:
        st.info("No chat requests yet — ask a question in the Chat tab to populate this dashboard.")
        return

    st.subheader("Latency over recent requests")
    st.line_chart({"latency_ms": [r["latency_ms"] for r in recent]})

    st.subheader("Context passed to the LLM per request (characters)")
    st.line_chart({
        "context_chars": [r["context_chars"] for r in recent],
        "response_chars": [r["response_chars"] for r in recent],
    })


def render_kb_dashboard() -> None:
    try:
        resp = requests.get(f"{BACKEND_URL}/corpus", timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as exc:
        st.error(f"Could not reach backend corpus stats: {exc}")
        return

    col1, col2, col3 = st.columns(3)
    col1.metric("Documents", data["total_docs"])
    col2.metric("Chunks", data["total_chunks"])
    col3.metric("Total characters", f"{data['total_chars']:,}")

    st.subheader("Chunks per document")
    df = pd.DataFrame(
        {"chunks": [d["chunk_count"] for d in data["docs"]]},
        index=[d["doc_id"] for d in data["docs"]],
    )
    st.bar_chart(df)

    st.subheader("Knowledge graph")
    if GRAPH_PATH.is_file():
        st.components.v1.html(GRAPH_PATH.read_text(encoding="utf-8"), height=700, scrolling=True)
    else:
        st.info(
            "No knowledge graph yet — run `/graphify backend/docs` from the project root "
            "to generate `graphify-out/graph.html`."
        )


with tab_analytics:
    traffic_tab, kb_tab = st.tabs(["Traffic", "Knowledge base"])
    with traffic_tab:
        render_traffic_dashboard()
    with kb_tab:
        render_kb_dashboard()

with tab_chat:
    if "session_id" not in st.session_state:
        st.session_state.session_id = None
    if "history" not in st.session_state:
        st.session_state.history = []

    for turn in st.session_state.history:
        with st.chat_message(turn["role"]):
            st.markdown(turn["content"])

    if not st.session_state.api_key:
        st.info("Enter your Groq API key in the sidebar to start chatting.")

    if prompt := st.chat_input(
        "Ask a question about the case studies...",
        disabled=not st.session_state.api_key,
    ):
        st.session_state.history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            try:
                resp = requests.post(
                    f"{BACKEND_URL}/chat",
                    json={
                        "message": prompt,
                        "session_id": st.session_state.session_id,
                        "api_key": st.session_state.api_key,
                    },
                    timeout=60,
                )
                resp.raise_for_status()
                data = resp.json()
                st.session_state.session_id = data["session_id"]
                answer = data["answer"]
            except requests.RequestException as exc:
                detail = exc.response.json().get("detail") if exc.response is not None else str(exc)
                answer = f"Request failed: {detail}"
            st.markdown(answer)

        st.session_state.history.append({"role": "assistant", "content": answer})
