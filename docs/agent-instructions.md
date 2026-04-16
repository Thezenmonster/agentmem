# Agent Memory Instructions

Copy-paste the block below into your `CLAUDE.md`, `.cursorrules`, or `AGENTS.md` file. This tells your coding agent how to use agentmem effectively.

---

## For Claude Code (`CLAUDE.md`)

Paste this into your project's `CLAUDE.md` or `~/.claude/CLAUDE.md`:

```markdown
## Memory (agentmem)

You have access to a governed memory system via MCP tools (prefixed `mcp__agentmem__`).

### Session Protocol
- **Start of every session:** call `load_session` to restore context from the previous session.
- **End of every session:** call `save_session` with: what was done, what's in progress, what's blocked.

### Before Acting on a Remembered Rule
- Call `search_memory` to verify the rule is still current (status = active or validated).
- Do not act on deprecated or superseded memories.

### When You Learn Something Durable
- Call `search_memory` first to check for duplicates.
- If no match, call `add_memory` with the appropriate type (bug, decision, setting, procedure, context, feedback).
- New observations start as `hypothesis`. Promote to `active` once confirmed.

### Trust Hierarchy
- `validated` > `active` > `hypothesis`. Deprecated and superseded are excluded from recall.
- Only the user promotes to `validated`. You may add `hypothesis` or `active`.

### Periodic Health
- Run `memory_health` when starting a new task area. Flag any conflicts or stale memories to the user.
- Run `memory_conflicts` if you notice contradictory rules.
```

---

## For Cursor (`.cursorrules`)

Paste this into your project's `.cursorrules` file:

```
## Memory (agentmem)

You have governed memory via MCP tools.

Session protocol:
- Start: call load_session to restore prior context.
- End: call save_session with status of current work.

Before acting on a remembered rule:
- Call search_memory to verify it's still active or validated.
- Ignore deprecated or superseded memories.

When you learn something durable:
- Search first (no duplicates).
- Add with type: bug, decision, setting, procedure, context, or feedback.
- New observations = hypothesis. Promote to active once confirmed.

Trust: validated > active > hypothesis. Deprecated excluded from recall.
Run memory_health at session start. Flag conflicts to the user.
```

---

## For Codex CLI (`AGENTS.md`)

Paste this into your project's `AGENTS.md`:

```markdown
## Memory (agentmem)

Governed memory is available via MCP tools.

- **Session start:** `load_session` to restore context.
- **Session end:** `save_session` with what was done, in progress, and blocked.
- **Before acting on memory:** `search_memory` to verify the rule is active/validated.
- **When learning something new:** `search_memory` first (no duplicates), then `add_memory`.
- **Trust:** validated > active > hypothesis. Deprecated/superseded excluded.
- **Health:** Run `memory_health` periodically. Flag conflicts to user.
```
