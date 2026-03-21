# agentmem

Production-ready agent memory in one line. No vector DB. No infrastructure. Just SQLite.

[![PyPI](https://img.shields.io/pypi/v/agentmem)](https://pypi.org/project/agentmem/)
[![Python](https://img.shields.io/pypi/pyversions/agentmem)](https://pypi.org/project/agentmem/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://github.com/thezenmonster/agentmem/actions/workflows/ci.yml/badge.svg)](https://github.com/thezenmonster/agentmem/actions)

## Install

```bash
pip install agentmem
```

## 30-Second Demo

```python
from agentmem import Memory

mem = Memory()

# Store memories by type
mem.add(type="bug", title="loudnorm undoes SFX reductions",
        content="Never apply loudnorm to final amix output. It lifts noise floor.")

mem.add(type="setting", title="Voice speed config",
        content="atempo 0.90 per-line then 1.15x global.",
        tags=["voice", "audio"])

# Full-text search (instant, FTS5-powered)
results = mem.search("audio mixing")

# Context-budgeted recall (the killer feature)
context = mem.recall("building a narration track", max_tokens=2000)
# Returns: formatted markdown of the most relevant memories,
#          fitted to your token budget, ranked by relevance + recency
```

## Why agentmem?

Every agent builder hits the same wall: your agent forgets everything between sessions.

Current solutions are either too heavy (vector databases, API keys, cloud services) or too simple (flat files that don't scale). agentmem sits in the sweet spot:

| Feature | Mem0 | Engram | MCP Memory | agentmem |
|---|---|---|---|---|
| `pip install`, done | Needs API key or vector DB | Go binary | npm package | **Yes** |
| Typed memories | Blob store | Key-value | Entities/relations | **6 types** |
| Python API | Yes | Go only | Node.js | **Yes** |
| Full-text search | Vector-based | FTS5 | No search | **FTS5** |
| MCP server | Separate setup | Built-in | Built-in | **Built-in** |
| CLI | No | Yes | No | **Yes** |
| Token budgeting | No | No | No | **Yes** |
| Markdown import | No | No | No | **Yes** |
| Zero infrastructure | No | Yes | Yes | **Yes** |

## Three Interfaces, One Store

### Python API

```python
from agentmem import Memory

mem = Memory("./my-agent.db")

# Add
record = mem.add(type="decision", title="Ban 3rd-person narration",
                 content="Average 25 views. Every time, without exception.",
                 tags=["scripting", "pov"])

# Search
results = mem.search("narration style")
results = mem.search("audio", type="bug")
results = mem.search("voice", tags=["speed"])

# Recall (context-budgeted)
context = mem.recall("preparing audio mix", max_tokens=3000)

# CRUD
mem.get(record.id)
mem.update(record.id, content="Updated: still banned.")
mem.delete(record.id)
mem.list(type="bug", limit=20)

# Stats
mem.stats()  # {"total": 142, "by_type": {"bug": 38, ...}, "db_size_kb": 340}
```

### CLI

```bash
# Add a memory
agentmem add --type bug --title "loudnorm undoes SFX" "Never apply loudnorm to final output"

# Search
agentmem search "voice speed"
agentmem search "audio" --type bug

# Context-budgeted recall
agentmem recall "building narration track" --tokens 2000

# Import from markdown files
agentmem import ./errors_and_fixes.md --type bug

# List and manage
agentmem list --type setting
agentmem stats

# Start MCP server
agentmem serve
```

### MCP Server

agentmem includes a built-in [Model Context Protocol](https://modelcontextprotocol.io/) server. Connect it to Claude Desktop, Cursor, or any MCP client.

```bash
pip install agentmem[mcp]
```

**Claude Desktop config** (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "agentmem": {
      "command": "agentmem",
      "args": ["serve", "--db", "/path/to/memory.db"]
    }
  }
}
```

**Available MCP tools:**
- `add_memory` — Store a new typed memory
- `search_memory` — Full-text search with filters
- `recall_memory` — Context-budgeted retrieval
- `update_memory` — Update by ID
- `delete_memory` — Delete by ID
- `list_memories` — List with optional type filter

## Typed Memory

Not a blob store. agentmem has six memory types that cover real agent workflows:

| Type | What it stores | Example |
|---|---|---|
| `setting` | Configuration, parameters, profiles | "Voice speed: atempo 0.90" |
| `bug` | Errors encountered and their fixes | "loudnorm lifts noise floor" |
| `decision` | Rules, policies, architectural choices | "3rd-person narration is banned" |
| `procedure` | Workflows, pipelines, sequences | "Voice chain: TTS → speed → 48kHz" |
| `context` | Background knowledge, who/what/where | "Project uses FFmpeg + Python" |
| `feedback` | User corrections and confirmations | "Michael: 'perfect, keep this setting'" |

## Context Budgeting — The Killer Feature

The `recall()` method answers: *"Given a query and a token budget, what memories should I inject into my LLM context?"*

```python
# Get the most relevant memories, fitted to 2000 tokens
context = mem.recall("fixing audio pipeline issues", max_tokens=2000)
```

**How it works:**
1. FTS5 search returns top candidates
2. Each candidate is scored: `relevance × 0.4 + recency × 0.2 + frequency × 0.2 + confidence × 0.2`
3. Highest-scored memories are greedily packed into your token budget
4. Returned as formatted markdown, ready for LLM injection
5. Access counts are automatically updated (frequently-used memories rank higher)

No embeddings needed. No vector database. Just SQLite FTS5 with porter stemming.

## Import from Markdown

Migrating from flat-file memory? Import your existing markdown files:

```bash
agentmem import ./errors_and_fixes.md --type bug
agentmem import ./MEMORY.md
```

The importer:
- Splits by H2/H3 headers (each section → one memory)
- Reads YAML frontmatter for defaults (type, project, tags)
- Extracts inline `tags: x, y, z` patterns
- Infers types from section titles ("bug", "fix", "setting", etc.)

**Frontmatter example:**

```markdown
---
type: bug
project: my-agent
---

### Database connection timeout

The connection pool was exhausting under load.
Fix: increase pool_size from 5 to 20.

tags: database, performance
```

## Project Scoping

Share one database across multiple projects or agents:

```python
agent_a = Memory("./shared.db", project="frontend")
agent_b = Memory("./shared.db", project="backend")

agent_a.add(type="bug", title="CSS grid issue", content="...")
agent_b.add(type="bug", title="API timeout", content="...")

agent_a.search("bug")  # Only returns frontend bugs
agent_b.search("bug")  # Only returns backend bugs
```

## How It Works

- **Storage:** SQLite with WAL mode (concurrent reads, thread-safe)
- **Search:** FTS5 with porter stemming and unicode61 tokenizer
- **Ranking:** Composite score combining text relevance, recency, access frequency, and confidence
- **Token counting:** Defaults to `len(text) // 4` estimate. Install `tiktoken` for accuracy:

```bash
pip install agentmem[tokens]
```

```python
import tiktoken
enc = tiktoken.encoding_for_model("gpt-4")
mem = Memory("./memory.db", token_counter=enc.encode)
```

## API Reference

### `Memory(path, project, token_counter)`

| Method | Description |
|---|---|
| `add(type, title, content, tags, ...)` | Store a memory. Returns `MemoryRecord`. |
| `get(id)` | Retrieve by ID. Returns `MemoryRecord \| None`. |
| `update(id, **kwargs)` | Update fields. Returns `MemoryRecord \| None`. |
| `delete(id)` | Delete by ID. Returns `bool`. |
| `search(query, type, tags, limit)` | FTS5 search. Returns `list[MemoryRecord]`. |
| `recall(query, max_tokens, format)` | Context-budgeted retrieval. Returns `str`. |
| `list(type, project, since, limit)` | List memories with filters. Returns `list[MemoryRecord]`. |
| `stats()` | Database statistics. Returns `dict`. |

### `MemoryRecord`

```python
@dataclass
class MemoryRecord:
    id: str
    type: str           # setting, bug, decision, procedure, context, feedback
    title: str
    content: str
    tags: list[str]
    source: str
    project: str
    confidence: float   # 0.0-1.0
    created_at: str     # ISO8601
    updated_at: str
    accessed_at: str
    access_count: int
    rank: float | None  # populated on search results
```

## License

MIT
