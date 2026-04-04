# agentmem

Governed memory for long-lived coding agents. Your agent stops forgetting, stops repeating mistakes, and knows what's still true.

[![PyPI](https://img.shields.io/pypi/v/quilmem)](https://pypi.org/project/quilmem/)
[![Python](https://img.shields.io/pypi/pyversions/quilmem)](https://pypi.org/project/quilmem/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://github.com/thezenmonster/agentmem/actions/workflows/ci.yml/badge.svg)](https://github.com/thezenmonster/agentmem/actions)

## The Problem

Your AI coding assistant forgets everything between sessions. It repeats old mistakes. It can't tell current rules from outdated ones. Context compresses and recovery is painful.

Most memory tools solve **storage**. agentmem solves **trust**.

## Install

```bash
pip install quilmem
```

## 60-Second Demo

```python
from agentmem import Memory

mem = Memory()

# Store typed memories
mem.add(type="bug", title="loudnorm undoes SFX levels",
        content="Never apply loudnorm to final mix. It re-normalizes everything.",
        status="validated")

mem.add(type="decision", title="Use per-line atempo",
        content="Bake speed into per-line TTS. No global pass.",
        status="active")

# Something you're not sure about yet
hypothesis = mem.add(type="decision", title="Maybe try 2-second gaps before CTA",
        content="Hypothesis from last session. Needs testing.",
        status="hypothesis")

# Search — validated and active memories rank highest.
# Deprecated and superseded memories are excluded automatically.
results = mem.search("audio mixing")

# Context-budgeted recall — fits the best memories into your token limit
context = mem.recall("building a narration track", max_tokens=2000)

# Lifecycle — promote what's proven, deprecate what's not
mem.promote(hypothesis.id)                # hypothesis -> active -> validated
mem.deprecate(hypothesis.id, reason="Disproven by data")
mem.supersede(old.id, new.id)             # old points to replacement

# Health check — is your memory system trustworthy?
from agentmem import health_check
report = health_check(mem._conn)
# Health: 85/100 | Conflicts: 0 | Stale: 2 | Validated: 14
```

## What Makes This Different

**Other memory tools store things.** agentmem knows what's still true.

| | Mem0 | Letta | Mengram | agentmem |
|---|---|---|---|---|
| Memory storage | Yes | Yes | Yes | Yes |
| Full-text search | Vector | Agent-driven | Knowledge graph | **FTS5** |
| Memory lifecycle states | No | Partial | No | **hypothesis -> active -> validated -> deprecated -> superseded** |
| Conflict detection | No | No | Partial | **Built-in** |
| Staleness detection | No | No | No | **Built-in** |
| Health scoring | No | No | No | **Built-in** |
| Provenance tracking | No | No | No | **source_path + source_hash** |
| Trust-ranked recall | No | No | No | **Validated > active > hypothesis** |
| Human-readable source files | No | No | No | **Canonical markdown** |
| Local-first, zero infrastructure | No | Self-host option | Self-host option | **Yes, always** |
| MCP server | Separate | Separate | Yes | **Built-in** |

## Truth Governance

The core idea: every memory has a **status** that tracks how much you should trust it.

```
hypothesis    New observation. Not yet confirmed. Lowest trust in recall.
    |
  active      Default. Currently believed true. Normal trust.
    |
 validated    Explicitly confirmed. Highest trust in recall.

 deprecated   Was true, no longer. Excluded from recall. Kept for history.
 superseded   Replaced by a newer memory. Points to replacement.
```

**Why this matters:** Without governance, your agent's memory accumulates stale rules, contradictions, and outdated decisions. It doesn't know that the voice setting from January was overridden in March. It retrieves both and the LLM picks randomly. Governed memory solves this.

## Conflict Detection

```python
from agentmem import detect_conflicts

conflicts = detect_conflicts(mem._conn)
# Found 2 conflict(s):
#   !! [decision] "Always apply loudnorm to voice"
#      vs [decision] "NEVER apply loudnorm to voice"
#      Contradiction on shared topic (voice, loudnorm, audio)
```

agentmem finds memories that contradict each other:
- Detects topic overlap (Jaccard similarity)
- Separates **duplicates** from **contradictions**
- Sentence-level negation matching (not just keyword scanning)
- Severity: `critical` (both active) vs `warning` (one deprecated)

## Staleness Detection

```python
from agentmem import detect_stale

stale = detect_stale(mem._conn, stale_days=30)
# [decision] "Use atempo 0.90" — Source changed since import (hash mismatch)
# [bug] "Firewall blocks port" — Not updated in 45 days
```

Finds outdated memories by:
- Age (not updated in N days)
- Source file missing (referenced file was deleted)
- Hash drift (source file content changed but memory wasn't updated)

## Health Check

```python
from agentmem import health_check

report = health_check(mem._conn)
print(f"Health: {report.health_score}/100")
print(f"Conflicts: {len(report.conflicts)}")
print(f"Stale: {len(report.stale)}")
```

Scores your memory system 0-100 based on: conflicts, stale percentage, orphaned references, deprecated weight, and whether you have any validated memories.

## Provenance-Aware Sync

Sync canonical markdown files into the DB with source tracking:

```python
# Each memory tracks where it came from
mem.add(type="bug", title="loudnorm lifts noise",
        content="...",
        source_path="/docs/errors.md",
        source_section="Audio Bugs",
        source_hash="a1b2c3d4e5f6")
```

The sync engine:
- **Same hash = skip** (idempotent, re-running changes nothing)
- **Different hash = update** (source file changed)
- **Section removed = deprecate** (with reason)
- **Section restored = resurrect** (reactivates deprecated memory)

## Three Interfaces

### Python API

```python
from agentmem import Memory

mem = Memory("./my-agent.db", project="frontend")

# CRUD
record = mem.add(type="decision", title="Use TypeScript", content="...")
mem.get(record.id)
mem.update(record.id, content="Updated reasoning.")
mem.delete(record.id)
mem.list(type="bug", limit=20)

# Search + recall
results = mem.search("typescript migration", type="decision")
context = mem.recall("setting up the build", max_tokens=3000)

# Governance
mem.promote(record.id)              # hypothesis -> active -> validated
mem.deprecate(record.id, reason="No longer relevant")
mem.supersede(old.id, new.id)       # links old to replacement

# Session persistence
mem.save_session("Working on auth refactor. Blocked on token refresh.")
mem.load_session()                  # picks up where last instance left off

# Health
mem.stats()
```

### CLI

```bash
# Get started in 30 seconds
agentmem init --tool claude --project myapp

# Check if everything's working
agentmem doctor

# Core
agentmem add --type bug --title "CSS grid issue" "Flexbox fallback needed"
agentmem search "grid layout"
agentmem recall "frontend styling" --tokens 2000

# Governance
agentmem promote <id>
agentmem deprecate <id> --reason "Fixed in v2.3"
agentmem health
agentmem conflicts
agentmem stale --days 14

# Import + sessions
agentmem import ./errors.md --type bug
agentmem save-session "Finished auth module, starting tests"
agentmem load-session

# MCP server
agentmem serve
```

### MCP Server

Built-in [Model Context Protocol](https://modelcontextprotocol.io/) server for Claude Code, Cursor, and any MCP client.

```bash
pip install quilmem[mcp]
```

**Claude Code config** (`.claude/settings.json`):

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

**MCP tools:** `add_memory`, `search_memory`, `recall_memory`, `update_memory`, `delete_memory`, `list_memories`, `save_session`, `load_session`, `promote_memory`, `deprecate_memory`, `supersede_memory`, `memory_health`, `memory_conflicts`

## Typed Memory

Seven types that cover real agent workflows:

| Type | What it stores | Example |
|---|---|---|
| `setting` | Configuration, parameters | "Voice speed: atempo 1.08" |
| `bug` | Errors and their fixes | "loudnorm lifts noise floor" |
| `decision` | Rules, policies, choices | "3rd-person narration banned" |
| `procedure` | Workflows, pipelines | "TTS -> speed -> 48kHz -> mix" |
| `context` | Background knowledge | "Project uses FFmpeg + Python 3.11" |
| `feedback` | User corrections | "Always pick, don't ask" |
| `session` | Current work state | "Working on auth. Blocked on tokens." |

## Trust-Ranked Recall

`recall()` doesn't just find relevant memories. It finds the **most trustworthy** relevant memories:

1. FTS5 search returns candidates
2. Each scored: `relevance (25%) + trust status (20%) + provenance (20%) + recency (15%) + frequency (10%) + confidence (10%)`
3. Validated canonical memories rank above unprovenanced hypothesis memories
4. Deprecated and superseded memories are excluded entirely
5. Packed greedily into your token budget

## Project Scoping

```python
frontend = Memory("./shared.db", project="frontend")
backend = Memory("./shared.db", project="backend")

frontend.search("bug")  # Only frontend bugs
backend.search("bug")   # Only backend bugs
```

## Battle-Tested

This isn't theoretical. agentmem was built under production pressure over 2+ months of daily use:
- 65+ YouTube Shorts produced with zero repeated production bugs
- 330+ memories governing voice generation, FFmpeg assembly, image prompting, upload workflows
- Every bug caught once, fixed once, never repeated
- Governance engine reduced conflicts from 1,848 false positives to 11 real findings

## How It Works

- **Storage:** SQLite with WAL mode (concurrent reads, thread-safe)
- **Search:** FTS5 with porter stemming and unicode61 tokenizer
- **Ranking:** Composite score: text relevance + trust status + provenance + recency + frequency + confidence
- **Governance:** Status lifecycle, conflict detection, staleness detection, health scoring
- **Sync:** Provenance-aware with source hashing and resurrection
- **Zero infrastructure:** No API keys, no cloud, no vector DB. Just a `.db` file.

## License

MIT
