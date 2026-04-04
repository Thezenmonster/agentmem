# Troubleshooting

Common problems and how to fix them.

## Install Problems

### `pip install quilmem` fails

Make sure you're on Python 3.11+:

```bash
python --version
```

If you're in a venv, make sure it's activated. If you're on Windows with multiple Pythons, try `py -3.11 -m pip install quilmem`.

### `agentmem` command not found after install

The `agentmem` script may not be on your PATH. Try running it as a module:

```bash
python -m agentmem --help
```

If that works, your install is fine but the scripts directory isn't on PATH. Fix it or use `python -m agentmem` as the command in MCP configs.

## MCP Connection Problems

### Tools don't appear in Claude Code / Cursor

1. Make sure the MCP extra is installed:

```bash
pip install quilmem[mcp]
```

2. Re-run init to get the config:

```bash
agentmem init --tool claude --project myapp
```

3. Copy the JSON into the correct config file:
   - Claude Code: `.claude/settings.json` or `~/.claude/settings.json`
   - Cursor: `.cursor/mcp.json` or `~/.cursor/mcp.json`
   - Windsurf: `.windsurf/mcp.json`
   - Codex: `.codex/config.toml`

4. **Restart your coding agent.** MCP config changes don't take effect until restart.

5. Test manually:

```bash
agentmem serve
```

If this prints an error, that's your problem. If it hangs silently, the server is working (it waits for MCP clients on stdin).

### `agentmem serve` fails with ImportError

You need the MCP extra:

```bash
pip install quilmem[mcp]
```

### Tools appear but return errors

Run doctor and check:

```bash
agentmem doctor
```

The most common cause is the DB path in your MCP config not matching where you ran `init`. Use absolute paths in the config.

## Database Problems

### "Database not found"

Run init first:

```bash
agentmem init --project myapp
```

### Health score is low

```bash
agentmem health
agentmem conflicts
agentmem stale --days 14
```

Fix conflicts by deprecating or superseding the wrong one. Review stale memories and update or deprecate them.

## Still Stuck?

### Get your debug info

```bash
agentmem debug-info
```

This prints your version, platform, DB state, and health in one block. Paste it into a bug report.

### Report the problem

Open an issue with your debug info:

**https://github.com/thezenmonster/agentmem/issues/new/choose**

Pick the template that fits:
- **Setup Help** — install or init didn't work
- **MCP Connection** — tools not showing up in your coding agent
- **Bug Report** — something broke during use
- **Docs Confusion** — the docs said X but Y happened

We read every issue. If it broke for you, it's probably breaking for others.
