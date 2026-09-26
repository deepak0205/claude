"""Conversation memory with rolling-summary trimming (ported pattern from agent_poc/agents/memory.py).

Keeps the latest N turns verbatim; anything older is folded into a running summary
capped at `summary_budget_ratio` of the conversation's accumulated size, so context
sent to the model stays bounded as a session grows long.
"""
from dataclasses import dataclass, field


@dataclass
class Turn:
    role: str  # "user" or "assistant"
    content: str


@dataclass
class ConversationMemory:
    recent_turns: int = 8
    summary_budget_ratio: float = 0.12
    turns: list[Turn] = field(default_factory=list)
    summary: str = ""
    _total_chars_seen: int = 0

    def add_turn(self, role: str, content: str) -> None:
        self.turns.append(Turn(role=role, content=content))
        self._total_chars_seen += len(content)
        self._fold_overflow()

    def _fold_overflow(self) -> None:
        while len(self.turns) > self.recent_turns:
            oldest = self.turns.pop(0)
            self.summary = f"{self.summary}\n[{oldest.role}] {oldest.content}".strip()
        max_chars = max(200, int(self._total_chars_seen * self.summary_budget_ratio))
        if len(self.summary) > max_chars:
            self.summary = self.summary[-max_chars:]

    def context_messages(self) -> list[dict]:
        messages = []
        if self.summary:
            messages.append({"role": "user", "content": f"[Earlier conversation summary]\n{self.summary}"})
        messages.extend({"role": t.role, "content": t.content} for t in self.turns)
        return messages
