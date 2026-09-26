"""Stdio MCP server exposing the case-study knowledge base as a tool + resources.

Shape follows the MCP_SESSION/travelops_mcp_server.py example already on this machine.
Run standalone (e.g. from an .mcp.json entry): python -m mcp_server.case_study_server
"""
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Resource, TextContent, Tool

from backend.config import DOCS_DIR, settings
from backend.rag.retriever import TfidfRetriever

server = Server("case-study-mcp")
_retriever = TfidfRetriever(DOCS_DIR)


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="retrieve_case_study",
            description="Search the Claude-healthcare case-study knowledge base for relevant passages.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "top_k": {"type": "integer", "default": settings.retrieval_top_k},
                },
                "required": ["query"],
            },
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name != "retrieve_case_study":
        raise ValueError(f"Unknown tool: {name}")
    chunks = _retriever.retrieve(arguments["query"], top_k=arguments.get("top_k", settings.retrieval_top_k))
    if not chunks:
        return [TextContent(type="text", text="No relevant passages found.")]
    text = "\n\n".join(f"[{c.doc_id} | {c.heading}]\n{c.text}" for c in chunks)
    return [TextContent(type="text", text=text)]


@server.list_resources()
async def list_resources() -> list[Resource]:
    return [
        Resource(
            uri=f"case-study://{doc_id}",
            name=doc_id,
            description=f"Full text of {doc_id}",
            mimeType="text/markdown",
        )
        for doc_id in sorted(p.name for p in DOCS_DIR.glob("*.md"))
    ]


@server.read_resource()
async def read_resource(uri: str) -> str:
    doc_id = uri.removeprefix("case-study://")
    path = DOCS_DIR / doc_id
    if not path.is_file():
        raise ValueError(f"Unknown resource: {uri}")
    return path.read_text(encoding="utf-8")


async def main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
