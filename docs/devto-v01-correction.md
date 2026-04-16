# Dev.to v0.1 Article Correction

**Article:** https://dev.to/thezenmonster/i-gave-my-ai-coding-assistant-a-memory-it-changed-how-i-work-2jkh

## What to do

Edit the article on Dev.to (Dashboard > Posts > Edit). Make two changes:

### 1. Add this block at the very top of the article body:

```markdown
> **Update (April 2026):** This article describes an earlier version of the project. The tool has since been rebuilt as **agentmem** with governed memory, trust lifecycle, conflict detection, and health scoring.
>
> **Install:** `pip install quilmem[mcp]`
> **GitHub:** [github.com/Thezenmonster/agentmem](https://github.com/Thezenmonster/agentmem)
> **What changed:** [I built memory governance (Dev.to v0.2)](https://dev.to/michael_onyekwere/my-ai-remembered-the-wrong-thing-and-broke-my-build-so-i-built-memory-governance-50b2)
```

### 2. Replace the bottom CTA section

Find this:

```
**npm:** `npx agent-recall`

**GitHub:** [github.com/Thezenmonster/agent-recall](https://github.com/Thezenmonster/agent-recall)

**Knowledge packs:** [github.com/Thezenmonster/agent-recall-packs](https://github.com/Thezenmonster/agent-recall-packs)

MIT licensed. Three dependencies. Works with any MCP client.

**If your AI assistant forgets everything between sessions, try it. One command.**
```

Replace with:

```
**Install:** `pip install quilmem[mcp]`

**Get started:** `agentmem init --tool claude --project myapp`

**GitHub:** [github.com/Thezenmonster/agentmem](https://github.com/Thezenmonster/agentmem)

MIT licensed. Zero infrastructure. Works with Claude Code, Cursor, Codex, Windsurf.

**If your AI assistant forgets everything between sessions, try it. Two commands.**
```
