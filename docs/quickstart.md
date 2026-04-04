# Quickstart: Governed Memory in 5 Minutes

Go from zero to a governed memory system in one terminal session.

## 1. Install

```bash
pip install quilmem
```

## 2. Create Your First Memories

```bash
# A validated rule (you're certain about this)
agentmem add --type decision --title "Never force-push to main" \
  --status validated \
  "Enforced after incident on March 3. Use feature branches + PR."

# A bug you've fixed
agentmem add --type bug --title "CORS headers missing on /api/auth" \
  "Symptom: 403 on frontend login. Fix: add Access-Control-Allow-Origin to auth middleware."

# A hypothesis (not yet proven)
agentmem add --type decision --title "Maybe batch DB writes" \
  --status hypothesis \
  "Hypothesis: batching inserts could reduce API latency by 40%. Needs benchmarking."
```

## 3. Search and Recall

```bash
# Full-text search
agentmem search "authentication"

# Context-budgeted recall — get the most relevant memories, fitted to a token limit
agentmem recall "debugging the login flow" --tokens 2000
```

## 4. Govern Your Memory

This is what makes agentmem different.

```bash
# Check your memory health
agentmem health

# Find contradictions
agentmem conflicts

# Find stale memories (not updated in 14+ days)
agentmem stale --days 14

# Promote a hypothesis that proved correct
agentmem promote <id>   # hypothesis -> active -> validated

# Deprecate something that's no longer true
agentmem deprecate <id> --reason "Replaced by new auth system"
```

## 5. Connect to Your Coding Agent (MCP)

```bash
pip install quilmem[mcp]
```

Add to your Claude Code config (`.claude/settings.json`):

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

Your agent now has 13 tools: add, search, recall, promote, deprecate, supersede, health, conflicts, and more.

## What Just Happened

In 5 minutes you built a memory system that:
- **Types** memories (bug, decision, setting, procedure, context, feedback, session)
- **Governs** them (hypothesis -> active -> validated -> deprecated -> superseded)
- **Detects** contradictions and stale rules
- **Scores** overall health
- **Ranks** by trust (validated > active > hypothesis)
- **Excludes** deprecated and superseded memories from search automatically

Your coding agent can now remember decisions, avoid past mistakes, and know what's still true.

## Next Steps

- [Before/After: Why Governance Matters](before-after.md)
- [Full API Reference](../README.md#three-interfaces)
- [MCP Setup Guide](mcp-setup.md)
