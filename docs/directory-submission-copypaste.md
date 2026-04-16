# Browser Tasks: Article + Directory Submissions

Four tasks. About 10 minutes total.

---

## 1. Dev.to: Delete old article, publish new one (5 min)

### Delete the old one

1. Go to **https://dev.to/dashboard**
2. Find **"I gave my AI coding assistant a memory. It changed how I work."**
3. Click **...** menu > **Delete** (or Unpublish)
4. Confirm. It has 0 reactions, 0 comments, and links to the wrong project. Nothing lost.

### Publish the new one

1. On the dashboard, click **Create Post**
2. Open `docs/devto-new-article.md` in a text editor
3. Copy the entire file contents and paste into the Dev.to editor
4. The frontmatter (title, tags, description) auto-populates
5. Change `published: false` to `published: true`
6. Optional: add a cover image
7. Click **Publish**

The new article title: **"My Claude Code agent stopped forgetting. Here's the 2-minute setup."**

### Quick check on v0.2 article

Glance at https://dev.to/michael_onyekwere/my-ai-remembered-the-wrong-thing-and-broke-my-build-so-i-built-memory-governance-50b2 and confirm the CTAs point to `agentmem`, not `agent-recall`.

---

## 2. mcpservers.org (2 min)

1. Go to **https://mcpservers.org/submit**
2. Fill in:

| Field | Paste this |
|---|---|
| Server Name | `agentmem` |
| Short Description | `Governed memory for coding agents with trust lifecycle, conflict detection, staleness tracking, and health scoring. SQLite + FTS5, zero infrastructure. Works with Claude Code, Cursor, Codex, Windsurf.` |
| Link | `https://github.com/Thezenmonster/agentmem` |
| Category | **Development** |
| Contact Email | `talesafterdark.official@gmail.com` |

3. Submit (free listing)

---

## 3. PulseMCP (30 sec)

1. Go to **https://www.pulsemcp.com/submit**
2. Select **MCP Server**
3. Paste URL: `https://github.com/Thezenmonster/agentmem`
4. Submit

PulseMCP pulls everything else from the repo.

---

## 4. mcp.so (30 sec)

1. Go to **https://mcp.so/submit**
2. Paste: `https://github.com/Thezenmonster/agentmem`
3. Submit

The site extracts metadata from GitHub.

---

## Already done (no action needed)

- **awesome-mcp-servers PR:** https://github.com/punkpeye/awesome-mcp-servers/pull/4959 (auto-merge bot enabled)
- **Glama:** auto-syncs from awesome-mcp-servers once PR merges
