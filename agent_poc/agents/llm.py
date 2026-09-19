"""Thin Anthropic client wrapper shared by every agent in this project.

Deliberately generic: this module knows nothing about memory, routing,
synthesis, or any other agent-specific concern. `call_tool` is the one forced
tool-use primitive reused by `agents/memory.py` today and by the Supervisor,
sub-agents, and Evidence Synthesis Agent in later phases.
"""

import anthropic

from config.settings import settings

client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)


def count_tokens(model: str, text: str) -> int:
    """Return the exact token count for `text` under `model`'s tokenizer."""
    result = client.messages.count_tokens(
        model=model,
        messages=[{"role": "user", "content": text}],
    )
    return result.input_tokens


def call_tool(
    model: str,
    system: str,
    user_content: str,
    tool_name: str,
    tool_schema: dict,
) -> dict:
    """Make one forced tool-use call and return the parsed tool input dict.

    `tool_schema` is the JSON schema for the tool's `input_schema` (e.g.
    `{"type": "object", "properties": {...}, "required": [...]}`). The model
    is forced to call `tool_name` via `tool_choice`, so the response is
    always structured — never free text.
    """
    response = client.messages.create(
        model=model,
        max_tokens=4096,
        system=system,
        messages=[{"role": "user", "content": user_content}],
        tools=[
            {
                "name": tool_name,
                "description": f"Return the result via the {tool_name} tool.",
                "input_schema": tool_schema,
            }
        ],
        tool_choice={"type": "tool", "name": tool_name},
    )

    for block in response.content:
        if block.type == "tool_use" and block.name == tool_name:
            return block.input

    raise ValueError(f"No tool_use block for '{tool_name}' found in response")


def run_agent_loop(
    model: str,
    system,
    user_content,
    tools: list[dict],
    tool_executor,
    finish_tool_name: str,
    finish_tool_schema: dict,
    max_iterations: int = 5,
) -> dict:
    """Manual ReAct-with-an-exit-hatch loop: the model freely decides when to
    call a regular tool vs. the `finish_tool_name` "exit" tool, one tool call
    per turn (`disable_parallel_tool_use=True`, since parallel tool use is on
    by default and would otherwise let the model call a search tool *and*
    the finish tool in the same turn with undefined precedence).

    `tool_executor(name, input) -> str` exceptions are caught here and fed
    back as an `is_error` tool_result so a flaky/unbuilt retrieval backend
    never crashes the loop.
    """
    finish_tool = {
        "name": finish_tool_name,
        "description": f"Call this when you are done, to return your final {finish_tool_name} result.",
        "input_schema": finish_tool_schema,
        "strict": True,
    }
    all_tools = tools + [finish_tool]

    messages = [{"role": "user", "content": user_content}]

    for _ in range(max_iterations):
        response = client.messages.create(
            model=model,
            max_tokens=4096,
            system=system,
            messages=messages,
            tools=all_tools,
            tool_choice={"type": "any", "disable_parallel_tool_use": True},
        )
        messages.append({"role": "assistant", "content": response.content})

        tool_use_block = None
        for block in response.content:
            if block.type == "tool_use":
                tool_use_block = block
                break

        if tool_use_block is None:
            continue

        if tool_use_block.name == finish_tool_name:
            return tool_use_block.input

        try:
            result_text = tool_executor(tool_use_block.name, tool_use_block.input)
            tool_result = {
                "type": "tool_result",
                "tool_use_id": tool_use_block.id,
                "content": result_text,
            }
        except Exception as e:
            tool_result = {
                "type": "tool_result",
                "tool_use_id": tool_use_block.id,
                "content": str(e),
                "is_error": True,
            }

        messages.append({"role": "user", "content": [tool_result]})

    final_response = client.messages.create(
        model=model,
        max_tokens=4096,
        system=system,
        messages=messages,
        tools=[all_tools[-1]],
        tool_choice={"type": "tool", "name": finish_tool_name, "disable_parallel_tool_use": True},
    )
    for block in final_response.content:
        if block.type == "tool_use" and block.name == finish_tool_name:
            return block.input

    raise ValueError(f"No tool_use block for '{finish_tool_name}' found in final forced response")
