"""MCP stdio server exposing agentmem tools."""

from __future__ import annotations

import json

from .core import Memory
from .models import MEMORY_TYPES, MEMORY_STATUSES

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
                description="Full-text search across all active memories. Returns results ranked by relevance, trust status, and recency. Deprecated and superseded memories are excluded automatically.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query. Supports natural language and keywords."},
                        "type": {"type": "string", "enum": list(MEMORY_TYPES), "description": "Filter results to a specific memory type (bug, decision, setting, procedure, context, feedback, session)"},
                        "limit": {"type": "integer", "default": 10, "description": "Maximum number of results to return"},
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
                description="Update the title, content, tags, or confidence of an existing memory. Use when a rule changes, a fix gets refined, or new context applies to an existing memory.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "id": {"type": "string", "description": "ID of the memory to update"},
                        "title": {"type": "string", "description": "New title (short summary, max 120 chars)"},
                        "content": {"type": "string", "description": "New content body"},
                        "tags": {"type": "array", "items": {"type": "string"}, "description": "New tag list (replaces existing tags)"},
                        "confidence": {"type": "number", "description": "Confidence score between 0.0 and 1.0"},
                    },
                    "required": ["id"],
                },
            ),
            Tool(
                name="delete_memory",
                description="Permanently delete a memory by ID. Prefer deprecate_memory for memories that were once true but are no longer. Only delete memories that were created in error or contain incorrect information.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "id": {"type": "string", "description": "ID of the memory to permanently delete"},
                    },
                    "required": ["id"],
                },
            ),
            Tool(
                name="list_memories",
                description="List all memories, optionally filtered by type. Returns memories sorted by most recently created. Use to browse what the memory system knows about a topic or to audit stored rules.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "type": {"type": "string", "enum": list(MEMORY_TYPES), "description": "Filter to a specific memory type (bug, decision, setting, procedure, context, feedback, session)"},
                        "limit": {"type": "integer", "default": 20, "description": "Maximum number of memories to return"},
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
            Tool(
                name="promote_memory",
                description="Promote a memory's trust level: hypothesis -> active -> validated. Use when evidence confirms a memory is true.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "id": {"type": "string", "description": "Memory ID to promote"},
                    },
                    "required": ["id"],
                },
            ),
            Tool(
                name="deprecate_memory",
                description="Mark a memory as deprecated. It will be excluded from search/recall but kept for history. Use when a rule or fact is no longer true.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "id": {"type": "string", "description": "Memory ID to deprecate"},
                        "reason": {"type": "string", "description": "Why this memory is no longer true", "default": ""},
                    },
                    "required": ["id"],
                },
            ),
            Tool(
                name="supersede_memory",
                description="Replace an old memory with a new one. Old memory is marked superseded and linked to the replacement.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "old_id": {"type": "string", "description": "Memory ID being replaced"},
                        "new_id": {"type": "string", "description": "Memory ID of the replacement"},
                    },
                    "required": ["old_id", "new_id"],
                },
            ),
            Tool(
                name="memory_health",
                description="Run a health check on the memory system. Returns: score (0-100), conflict count, stale count, status distribution. Use to audit memory quality.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "stale_days": {"type": "integer", "default": 30, "description": "Days without update to consider stale"},
                    },
                },
            ),
            Tool(
                name="memory_conflicts",
                description="Detect contradictions between active memories. Returns pairs of memories that assert and negate the same topic.",
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

        elif name == "promote_memory":
            record = mem.promote(arguments["id"])
            if record:
                return [TextContent(type="text", text=f"Promoted: {record.id} -> {record.status}\n[{record.type}] {record.title}")]
            return [TextContent(type="text", text=f"Not found: {arguments['id']}")]

        elif name == "deprecate_memory":
            record = mem.deprecate(arguments["id"], reason=arguments.get("reason", ""))
            if record:
                return [TextContent(type="text", text=f"Deprecated: {record.id}\n[{record.type}] {record.title}")]
            return [TextContent(type="text", text=f"Not found: {arguments['id']}")]

        elif name == "supersede_memory":
            old, new = mem.supersede(arguments["old_id"], arguments["new_id"])
            if old and new:
                return [TextContent(type="text", text=f"Superseded: {old.title} -> {new.title}\nOld: {old.id} (superseded)\nNew: {new.id} (active)")]
            return [TextContent(type="text", text="One or both memory IDs not found.")]

        elif name == "memory_health":
            from .governance import health_check
            report = health_check(mem._conn, project=mem.project, stale_days=arguments.get("stale_days", 30))
            lines = [
                f"Memory Health: {report.health_score:.0f}/100",
                f"Total: {report.total_memories}",
                f"By status: {report.by_status}",
                f"Conflicts: {len(report.conflicts)}",
                f"Stale: {len(report.stale)}",
                f"Never accessed: {report.never_accessed}",
            ]
            if report.conflicts:
                lines.append("\nTop conflicts:")
                for c in report.conflicts[:5]:
                    lines.append(f"  {'!!' if c.severity == 'critical' else '?'} {c.memory_a.title[:40]} vs {c.memory_b.title[:40]}")
            if report.health_score >= 100:
                validated = report.by_status.get("validated", 0)
                lines.append(f"\nFully governed. 0 conflicts, 0 stale, {validated} validated rules.")
            return [TextContent(type="text", text="\n".join(lines))]

        elif name == "memory_conflicts":
            from .governance import detect_conflicts
            found = detect_conflicts(mem._conn, project=mem.project)
            if not found:
                return [TextContent(type="text", text="No conflicts detected.")]
            lines = [f"Found {len(found)} conflict(s):"]
            for c in found:
                icon = "!!" if c.severity == "critical" else "?"
                lines.append(f"\n{icon} [{c.memory_a.type}] {c.memory_a.title}\n   vs [{c.memory_b.type}] {c.memory_b.title}\n   {c.reason}")
            return [TextContent(type="text", text="\n".join(lines))]

        return [TextContent(type="text", text=f"Unknown tool: {name}")]

    import asyncio
    async def _run():
        async with stdio_server() as (read, write):
            await server.run(read, write, server.create_initialization_options())

    asyncio.run(_run())
