"""MCP stdio server exposing agentmem tools."""

from __future__ import annotations

import json

from .core import Memory
from .models import MEMORY_TYPES

_mem: Memory | None = None


def _get_mem() -> Memory:
    if _mem is None:
        raise RuntimeError("Memory not initialized. Call run_server() first.")
    return _mem


def run_server(db_path: str = "./memory.db", project: str = ""):
    """Start the MCP stdio server."""
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import TextContent, Tool

    global _mem
    _mem = Memory(path=db_path, project=project)

    server = Server("agentmem")

    @server.list_tools()
    async def list_tools():
        return [
            Tool(
                name="add_memory",
                description="Store a new memory. Use when something is worth remembering: a preference, fix, decision, or procedure.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "type": {"type": "string", "enum": list(MEMORY_TYPES),
                                 "description": "Memory category"},
                        "title": {"type": "string", "description": "Short summary, max 120 chars"},
                        "content": {"type": "string", "description": "Full memory content"},
                        "tags": {"type": "array", "items": {"type": "string"}, "default": []},
                    },
                    "required": ["type", "title", "content"],
                },
            ),
            Tool(
                name="search_memory",
                description="Search memories by text query. Returns ranked results.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "type": {"type": "string", "enum": list(MEMORY_TYPES)},
                        "limit": {"type": "integer", "default": 10},
                    },
                    "required": ["query"],
                },
            ),
            Tool(
                name="recall_memory",
                description="Get the most relevant memories for a topic, fitted to a token budget. Use at the start of a task to load context.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "max_tokens": {"type": "integer", "default": 4000},
                    },
                    "required": ["query"],
                },
            ),
            Tool(
                name="update_memory",
                description="Update an existing memory by ID.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "title": {"type": "string"},
                        "content": {"type": "string"},
                        "tags": {"type": "array", "items": {"type": "string"}},
                        "confidence": {"type": "number"},
                    },
                    "required": ["id"],
                },
            ),
            Tool(
                name="delete_memory",
                description="Delete a memory by ID.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                    },
                    "required": ["id"],
                },
            ),
            Tool(
                name="list_memories",
                description="List memories, optionally filtered by type.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "type": {"type": "string", "enum": list(MEMORY_TYPES)},
                        "limit": {"type": "integer", "default": 20},
                    },
                },
            ),
            Tool(
                name="save_session",
                description="Save current session state before conversation ends or context compresses. Capture: what's in progress, what's blocked, what's done, decisions made. The next agent instance loads this automatically.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "summary": {"type": "string", "description": "Full session state: in-progress work, blocked items, completed items, key decisions"},
                        "tags": {"type": "array", "items": {"type": "string"}, "default": ["session", "state"]},
                    },
                    "required": ["summary"],
                },
            ),
            Tool(
                name="load_session",
                description="Load the most recent session state. Call this at the start of a conversation to pick up where the last instance left off.",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict):
        mem = _get_mem()

        if name == "add_memory":
            record = mem.add(
                type=arguments["type"],
                title=arguments["title"],
                content=arguments["content"],
                tags=arguments.get("tags", []),
                source="mcp",
            )
            return [TextContent(type="text", text=f"Memory added: {record.id}\n[{record.type}] {record.title}")]

        elif name == "search_memory":
            results = mem.search(
                query=arguments["query"],
                type=arguments.get("type"),
                limit=arguments.get("limit", 10),
            )
            if not results:
                return [TextContent(type="text", text="No results found.")]
            lines = []
            for r in results:
                score = f" (score: {r.rank:.3f})" if r.rank is not None else ""
                lines.append(f"[{r.type}] {r.title}{score}\nid: {r.id}\n{r.content[:200]}")
            return [TextContent(type="text", text="\n\n---\n\n".join(lines))]

        elif name == "recall_memory":
            context = mem.recall(
                query=arguments["query"],
                max_tokens=arguments.get("max_tokens", 4000),
            )
            return [TextContent(type="text", text=context or "No relevant memories found.")]

        elif name == "update_memory":
            kwargs = {k: v for k, v in arguments.items() if k != "id" and v is not None}
            record = mem.update(arguments["id"], **kwargs)
            if record:
                return [TextContent(type="text", text=f"Updated: {record.id}\n[{record.type}] {record.title}")]
            return [TextContent(type="text", text=f"Not found: {arguments['id']}")]

        elif name == "delete_memory":
            if mem.delete(arguments["id"]):
                return [TextContent(type="text", text=f"Deleted: {arguments['id']}")]
            return [TextContent(type="text", text=f"Not found: {arguments['id']}")]

        elif name == "list_memories":
            records = mem.list(
                type=arguments.get("type"),
                limit=arguments.get("limit", 20),
            )
            if not records:
                return [TextContent(type="text", text="No memories found.")]
            lines = [f"[{r.type}] {r.title} (id: {r.id})" for r in records]
            return [TextContent(type="text", text="\n".join(lines))]

        elif name == "save_session":
            record = mem.save_session(
                summary=arguments["summary"],
                tags=arguments.get("tags", ["session", "state"]),
            )
            return [TextContent(type="text", text=f"Session saved: {record.id}\n{record.content[:200]}...")]

        elif name == "load_session":
            record = mem.load_session()
            if record:
                return [TextContent(type="text", text=f"Last session ({record.created_at}):\n\n{record.content}")]
            return [TextContent(type="text", text="No previous session found.")]

        return [TextContent(type="text", text=f"Unknown tool: {name}")]

    import asyncio
    async def _run():
        async with stdio_server() as (read, write):
            await server.run(read, write, server.create_initialization_options())

    asyncio.run(_run())
