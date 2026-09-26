"""Streamlit chat UI. Calls the FastAPI backend only — renders exactly what's returned, no fabrication.

The user supplies their own Groq API key here; it's kept only in this browser session's
state and sent with each request — never written to disk by this app.
"""
import os

import requests
import streamlit as st

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="Claude Healthcare Case Studies", page_icon="🩺")
st.title("Claude in Healthcare — Case Study Assistant")
st.caption("Ask about Banner Health, Qualified Health, Carta Healthcare, Elation Health, or Commure.")

with st.sidebar:
    st.subheader("Groq API Key")
    st.session_state.api_key = st.text_input(
        "Groq API key",
        value=st.session_state.get("api_key", ""),
        type="password",
        help="Used to call openai/gpt-oss-120b via Groq. Kept only in this session, sent with each request.",
    )
    st.caption("Get a key at [console.groq.com](https://console.groq.com/keys).")

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
