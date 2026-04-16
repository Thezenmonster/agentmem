# Dev.to: Delete Old Article, Publish New One

## Step 1: Delete the old v0.1 article

1. Go to https://dev.to/dashboard
2. Find **"I gave my AI coding assistant a memory. It changed how I work."**
3. Click the **...** menu (or Edit > scroll to bottom)
4. Click **Delete** / **Unpublish**
5. Confirm

This article has 0 reactions, 0 comments, and all its CTAs link to `agent-recall` (wrong project). Nothing is lost by deleting it.

## Step 2: Publish the new article

1. Go to https://dev.to/dashboard
2. Click **Create Post**
3. Copy the entire contents of `docs/devto-new-article.md` and paste it into the editor
4. Dev.to uses the same frontmatter format, so the title, tags, and description will auto-populate
5. Add a cover image if you have one (optional, the animated SVG from `assets/demo.svg` could work as a screenshot)
6. Change `published: false` to `published: true` in the frontmatter
7. Click **Publish**

The new article:
- Title: **"My Claude Code agent stopped forgetting. Here's the 2-minute setup."**
- Angle: activation story (2-minute setup + what changes), not a governance deep-dive (that's the v0.2 article)
- All CTAs point to the correct repo (agentmem) and package (quilmem)
- Includes the copy-paste CLAUDE.md instruction block
- Tags: ai, productivity, mcp, opensource

## Step 3: Check the v0.2 article is still correct

The v0.2 article is here: https://dev.to/michael_onyekwere/my-ai-remembered-the-wrong-thing-and-broke-my-build-so-i-built-memory-governance-50b2

Quick check: make sure its CTAs point to `github.com/Thezenmonster/agentmem` and `pip install quilmem`. Codex confirmed this one is correct, but worth a glance.
