"""Chat agent: a tool-use loop over Groq's gpt-oss-120b (OpenAI-compatible Chat Completions API)
that grounds answers in retrieved case-study chunks.
"""
import json

import openai

from backend.config import settings
from backend.memory import ConversationMemory
from backend.rag.retriever import ToolProvider
from backend.telemetry import record_llm_call, traced

SYSTEM_PROMPT = """You are an assistant answering questions about Claude-in-healthcare case studies
(Banner Health, Qualified Health, Carta Healthcare, Elation Health, Commure) and related design docs.

Rules:
- Always call search_case_studies before answering a substantive question.
- Answer only using the retrieved passages. If they don't contain the answer, say so plainly.
- Cite the source document filename(s) you drew from at the end of your answer.
- Never fabricate metrics, company names, or details not present in the retrieved passages.
"""

SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "search_case_studies",
        "description": "Search the case-study knowledge base for passages relevant to a query.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "What to search for"},
            },
            "required": ["query"],
        },
    },
}


class ChatAgent:
    def __init__(self, retriever: ToolProvider, api_key: str, top_k: int | None = None):
        self.retriever = retriever
        self.top_k = top_k or settings.retrieval_top_k
        self.client = openai.OpenAI(api_key=api_key, base_url=settings.groq_base_url)
        self.last_chunks_retrieved = 0
        self.last_context_chars = 0

    @traced("rag.retrieve")
    def _search(self, query: str) -> str:
        chunks = self.retriever.retrieve(query, top_k=self.top_k)
        result_text = (
            "No relevant passages found." if not chunks
            else "\n\n".join(f"[Source: {c.doc_id} | {c.heading}]\n{c.text}" for c in chunks)
        )
        self.last_chunks_retrieved += len(chunks)
        self.last_context_chars += len(result_text)
        return result_text

    def answer(self, memory: ConversationMemory, user_message: str) -> str:
        memory.add_turn("user", user_message)
        messages = [{"role": "system", "content": SYSTEM_PROMPT}, *memory.context_messages()]

        while True:
            response = self.client.chat.completions.create(
                model=settings.groq_model,
                messages=messages,
                tools=[SEARCH_TOOL],
            )
            record_llm_call()
            message = response.choices[0].message

            if not message.tool_calls:
                final_text = message.content or ""
                memory.add_turn("assistant", final_text)
                return final_text

            messages.append({
                "role": "assistant",
                "content": message.content,
                "tool_calls": [tc.model_dump() for tc in message.tool_calls],
            })
            for tool_call in message.tool_calls:
                args = json.loads(tool_call.function.arguments)
                result_text = self._search(args["query"])
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result_text,
                })
