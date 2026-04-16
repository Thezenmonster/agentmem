---
title: My Claude Code agent stopped forgetting. Here's the 2-minute setup.
published: false
description: How I gave my coding agent persistent memory with trust governance. Two commands. No cloud. No API keys.
tags: ai, productivity, mcp, opensource
cover_image:
---

I fix a bug on Monday. On Wednesday my agent debugs the same bug from scratch.

I tell it "use pnpm, not npm" and by Thursday it's running npm again. I solve an FFmpeg audio issue at 2am and three weeks later I'm staring at the exact same stack trace, wondering if I'm losing my mind or if my agent is.

The problem isn't that AI assistants are bad at coding. They're good. The problem is they have no memory between sessions. Every conversation starts from zero.

## I tried the existing tools

Mem0 needs an OpenAI API key and a cloud account. Letta wants you to self-host a server. The official MCP memory server uses a knowledge graph I didn't need. I wanted something simpler: store things locally, search them, get them back when relevant, and know which ones are still true.

That last part turned out to be the hard part.

## 330 memories and my agent got worse

After two months of building a memory system, I had 330 memories in my database. And my agent started breaking things.

Not because it forgot. Because it remembered too much. An old rule said "always apply loudnorm to voice audio." A newer rule said "never apply loudnorm." Both were active. Both were retrievable. The agent picked the wrong one and ruined a production build.

Storage isn't the problem. Trust is the problem. Your agent needs to know which memories are still true and which ones got replaced.

## What I built

[agentmem](https://github.com/Thezenmonster/agentmem) is governed memory for coding agents. Every memory has a trust status:

```
hypothesis → active → validated → deprecated / superseded
```

Validated memories rank highest in recall. Deprecated ones are excluded entirely. If two memories contradict each other, the system catches it. If a memory's source file changed since it was recorded, the system flags it as stale.

It runs on SQLite. No cloud. No API keys. No vector database. Just a `.db` file in your project.

## Setup (actually 2 minutes)

```bash
pip install quilmem[mcp]
agentmem init --tool claude --project myapp
```

The init command creates your database, adds a starter memory, and prints the MCP config. Paste it into your editor settings, restart, done. Your agent now has 13 memory tools.

Works with Claude Code, Cursor, Codex CLI, and Windsurf.

## What it looks like in practice

My agent runs `load_session` at the start of every conversation. It picks up where the last session left off. No context lost.

When it learns something new, it stores it:

```bash
agentmem add --type bug --title "loudnorm lifts noise floor" \
  --status validated \
  "Never apply loudnorm to final mix. It re-normalizes everything."
```

When I want to know if the memory system is healthy:

```bash
agentmem health
# Health: 92/100 | Conflicts: 0 | Stale: 1 | Validated: 48
```

When two rules contradict each other, I find out before they break something:

```bash
agentmem conflicts
# !! "Always apply loudnorm" vs "Never apply loudnorm"
# Contradiction on shared topic (voice, loudnorm, audio)
```

## Results after 65 production builds

I produce short-form video with an AI pipeline. Voice generation, image prompting, FFmpeg assembly, uploads. Lots of settings, lots of things that can break.

Since deploying governed memory: zero repeated production bugs. Not "fewer." Zero. Every bug gets caught once, fixed once, stored as validated, and never repeated.

The database went from 330 unmanaged memories to 226 governed ones. The 104 that got cut were stale, contradictory, or superseded. They were noise that made my agent worse, not better.

## The copy-paste agent instructions

This is the part most memory tools skip. Installing the tool isn't enough. You have to tell your agent how to use it.

Paste this into your `CLAUDE.md` (or `.cursorrules` for Cursor):

```markdown
## Memory (agentmem)

You have governed memory via MCP tools.

- **Session start:** call `load_session` to restore context.
- **Session end:** call `save_session` with what was done, in progress, blocked.
- **Before acting on a remembered rule:** call `search_memory` to verify it's active/validated.
- **When you learn something durable:** search first (no duplicates), then `add_memory`.
- **Trust:** validated > active > hypothesis. Deprecated excluded from recall.
- **Health:** Run `memory_health` periodically. Flag conflicts to user.
```

That block is the difference between "memory is installed" and "memory is actually used."

## Try it

```bash
pip install quilmem[mcp]
agentmem init --tool claude --project myapp
```

**GitHub:** [github.com/Thezenmonster/agentmem](https://github.com/Thezenmonster/agentmem)
**Docs:** [thezenmonster.github.io/agentmem](https://thezenmonster.github.io/agentmem/)

MIT licensed. Zero infrastructure. 84 tests. Works with Claude Code, Cursor, Codex, Windsurf.

If your agent keeps forgetting things between sessions, or worse, remembering the wrong things, this fixes it. Two commands.
