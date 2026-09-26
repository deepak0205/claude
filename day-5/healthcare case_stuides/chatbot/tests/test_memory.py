from backend.memory import ConversationMemory


def test_recent_turns_kept_verbatim_until_limit():
    memory = ConversationMemory(recent_turns=3, summary_budget_ratio=0.5)
    memory.add_turn("user", "one")
    memory.add_turn("assistant", "two")
    memory.add_turn("user", "three")
    assert [t.content for t in memory.turns] == ["one", "two", "three"]
    assert memory.summary == ""


def test_overflow_turns_fold_into_summary():
    memory = ConversationMemory(recent_turns=2, summary_budget_ratio=0.9)
    memory.add_turn("user", "first message")
    memory.add_turn("assistant", "second message")
    memory.add_turn("user", "third message")
    assert len(memory.turns) == 2
    assert [t.content for t in memory.turns] == ["second message", "third message"]
    assert "first message" in memory.summary


def test_summary_stays_within_budget():
    memory = ConversationMemory(recent_turns=1, summary_budget_ratio=0.1)
    for i in range(20):
        memory.add_turn("user", f"message number {i} " * 5)
    max_chars = max(200, int(memory._total_chars_seen * 0.1))
    assert len(memory.summary) <= max_chars
