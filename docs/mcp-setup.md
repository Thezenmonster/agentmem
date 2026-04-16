# MCP Setup Guide

Connect agentmem to your coding agent in 2 minutes. Pick your tool.

## Prerequisites

```bash
pip install quilmem[mcp]
```

Verify it works:

```bash
agentmem --help
```

If that prints the command list, you're good.

---

## Claude Code

Claude Code reads MCP config from `~/.claude/settings.json` (global) or `.claude/settings.json` (project-level).

### Option A: CLI (fastest)

```bash
claude mcp add agentmem -- agentmem --db ./memory.db --project myproject serve
```

That's it. Restart Claude Code. The 13 agentmem tools should appear.

### Option B: Manual config

Add this to `~/.claude/settings.json` (global) or `.claude/settings.json` in your project root:

```json
{
  "mcpServers": {
    "agentmem": {
      "command": "agentmem",
      "args": ["--db", "./memory.db", "--project", "myproject", "serve"],
      "type": "stdio"
    }
  }
}
```

Replace `./memory.db` with wherever you want the database. Replace `myproject` with your project name (used for scoping if you run multiple projects on one DB).

### If agentmem isn't on PATH

Use the full Python path:

```json
{
  "mcpServers": {
    "agentmem": {
      "command": "python",
      "args": ["-m", "agentmem", "--db", "./memory.db", "--project", "myproject", "serve"],
      "type": "stdio"
    }
  }
}
```

On Windows, you may need the full Python path:

```json
{
  "mcpServers": {
    "agentmem": {
      "command": "C:/Python313/python.exe",
      "args": ["-m", "agentmem", "--db", "C:/path/to/memory.db", "--project", "myproject", "serve"],
      "type": "stdio"
    }
  }
}
```

### Verify

In Claude Code, the agentmem tools should show up. Ask Claude to run `memory_health` to confirm the connection.

---

## Cursor

Cursor reads MCP config from `~/.cursor/mcp.json` (global) or `.cursor/mcp.json` (project root).

Create or edit the file:

```json
{
  "mcpServers": {
    "agentmem": {
      "command": "agentmem",
      "args": ["--db", "./memory.db", "--project", "myproject", "serve"]
    }
  }
}
```

If `agentmem` isn't on PATH, use the full Python path:

```json
{
  "mcpServers": {
    "agentmem": {
      "command": "python",
      "args": ["-m", "agentmem", "--db", "./memory.db", "--project", "myproject", "serve"]
    }
  }
}
```

### Verify

Open the command palette (`Ctrl+Shift+P` / `Cmd+Shift+P`), type "MCP", and check that agentmem appears as a connected server. You can also type "Open MCP Settings" to see the config.

---

## Codex (OpenAI)

Codex reads MCP config from `~/.codex/config.toml` (global) or `.codex/config.toml` (project root, trusted projects only).

Add this to the config file:

```toml
[mcp_servers.agentmem]
command = "agentmem"
args = ["--db", "./memory.db", "--project", "myproject", "serve"]
```

If `agentmem` isn't on PATH:

```toml
[mcp_servers.agentmem]
command = "python"
args = ["-m", "agentmem", "--db", "./memory.db", "--project", "myproject", "serve"]
```

### Verify

Run `codex` and ask it to use the `memory_health` tool. If it returns a health score, you're connected.

---

## Windsurf

Windsurf uses the same MCP config format as Cursor. Create `~/.windsurf/mcp.json` or `.windsurf/mcp.json` in your project:

```json
{
  "mcpServers": {
    "agentmem": {
      "command": "agentmem",
      "args": ["--db", "./memory.db", "--project", "myproject", "serve"]
    }
  }
}
```

---

## Available MCP Tools

Once connected, your agent has 13 tools:

| Tool | What it does |
|------|-------------|
| `add_memory` | Store a typed memory (bug, decision, setting, procedure, context, feedback) |
| `search_memory` | Full-text search with filters |
| `recall_memory` | Context-budgeted retrieval — fits best memories into a token limit |
| `update_memory` | Update a memory by ID |
| `delete_memory` | Delete a memory by ID |
| `list_memories` | List memories with optional type filter |
| `save_session` | Save current work state before conversation ends |
| `load_session` | Restore state at the start of a new session |
| `promote_memory` | Advance trust: hypothesis -> active -> validated |
| `deprecate_memory` | Mark as no longer true (excluded from recall) |
| `supersede_memory` | Replace old memory with new one |
| `memory_health` | Score the memory system 0-100 |
| `memory_conflicts` | Find contradictions between active memories |

---

## Tell Your Agent How to Use Memory

Copy-paste a ready-made instruction block into your `CLAUDE.md`, `.cursorrules`, or `AGENTS.md`:

**[Agent Instructions](agent-instructions.md)** - Session protocol, trust hierarchy, when to search vs add.

This is the difference between "memory is installed" and "memory is actually used."

---

## Tips

**Start every session** by having your agent call `load_session`. This restores where the last session left off.

**End every session** with `save_session`. Capture what's in progress, what's blocked, and what was decided.

**Promote memories** that prove correct. A `validated` memory ranks higher than `active` in recall. A `hypothesis` ranks lowest. This is how your agent learns what to trust.

**Run health checks** periodically. `memory_health` tells you if contradictions, stale rules, or orphaned references are degrading trust.

**Use project scoping** if you work on multiple codebases. Each project gets isolated memory with `--project projectname`.

---

## Troubleshooting

**Tools don't appear after config change**
Restart your editor. MCP servers are loaded at startup.

**"Command not found" errors**
Use the full path to Python and `-m agentmem` instead of the `agentmem` command directly.

**Windows path issues**
Use forward slashes in JSON config: `C:/Users/you/memory.db`, not backslashes.

**Server starts but no tools appear**
Check that you have the MCP extra installed: `pip install quilmem[mcp]`. The base package doesn't include the MCP dependency.

**Multiple agents sharing one database**
Use different `--project` values. Each project's memories are isolated in search and recall, but stored in the same file.
