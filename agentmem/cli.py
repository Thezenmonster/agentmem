"""CLI interface for agentmem."""

from __future__ import annotations

import io
import json
import sys

# Windows cp1252 breaks on unicode chars like arrows/dashes in memory titles
if sys.stdout and hasattr(sys.stdout, 'encoding') and sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if sys.stderr and hasattr(sys.stderr, 'encoding') and sys.stderr.encoding and sys.stderr.encoding.lower() != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import click

from . import __version__
from .core import Memory
from .models import MEMORY_TYPES, MEMORY_STATUSES


def _get_mem(ctx: click.Context) -> Memory:
    return Memory(path=ctx.obj["db"], project=ctx.obj.get("project", ""))


@click.group()
@click.option("--db", default="./memory.db", envvar="AGENTMEM_DB", help="Database path.")
@click.option("--project", default="", help="Project scope.")
@click.pass_context
def main(ctx, db, project):
    """agentmem -- Governed memory for coding agents."""
    ctx.ensure_object(dict)
    ctx.obj["db"] = db
    ctx.obj["project"] = project


@main.command()
@click.option("--type", "mem_type", type=click.Choice(MEMORY_TYPES), required=True)
@click.option("--title", required=True)
@click.option("--status", "mem_status", type=click.Choice(MEMORY_STATUSES), default="active",
              help="Initial status (default: active).")
@click.option("--tags", default="", help="Comma-separated tags.")
@click.argument("content")
@click.pass_context
def add(ctx, mem_type, title, mem_status, tags, content):
    """Add a memory."""
    mem = _get_mem(ctx)
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    record = mem.add(type=mem_type, title=title, content=content, tags=tag_list,
                     source="cli", status=mem_status)
    status_label = f" ({record.status})" if record.status != "active" else ""
    click.echo(f"Added: {record.id}")
    click.echo(f"  [{record.type}] {record.title}{status_label}")
    mem.close()


@main.command()
@click.argument("query")
@click.option("--type", "mem_type", type=click.Choice(MEMORY_TYPES), default=None)
@click.option("--limit", default=10)
@click.option("--json-output", "as_json", is_flag=True, help="Output as JSON.")
@click.pass_context
def search(ctx, query, mem_type, limit, as_json):
    """Search memories by text query."""
    mem = _get_mem(ctx)
    results = mem.search(query, type=mem_type, limit=limit)

    if as_json:
        click.echo(json.dumps([r.to_dict() for r in results], indent=2))
    else:
        if not results:
            click.echo("No results.")
        for r in results:
            score = f" (score: {r.rank:.3f})" if r.rank is not None else ""
            click.echo(f"\n  [{r.type}] {r.title}{score}")
            click.echo(f"  id: {r.id}")
            preview = r.content[:120].replace("\n", " ")
            click.echo(f"  {preview}...")
    mem.close()


@main.command()
@click.argument("query")
@click.option("--tokens", default=4000, help="Max token budget.")
@click.pass_context
def recall(ctx, query, tokens):
    """Get context-budgeted memories for a query."""
    mem = _get_mem(ctx)
    context = mem.recall(query, max_tokens=tokens)
    if context:
        click.echo(context)
    else:
        click.echo("No relevant memories found.")
    mem.close()


@main.command("list")
@click.option("--type", "mem_type", type=click.Choice(MEMORY_TYPES), default=None)
@click.option("--since", default=None, help="ISO date filter.")
@click.option("--limit", default=20)
@click.pass_context
def list_cmd(ctx, mem_type, since, limit):
    """List memories."""
    mem = _get_mem(ctx)
    records = mem.list(type=mem_type, since=since, limit=limit)

    if not records:
        click.echo("No memories.")
    for r in records:
        tags = f" [{', '.join(r.tags)}]" if r.tags else ""
        click.echo(f"  [{r.type}] {r.title}{tags}")
        click.echo(f"    id: {r.id}  accessed: {r.access_count}x")
    mem.close()


@main.command()
@click.argument("id")
@click.pass_context
def get(ctx, id):
    """Get a memory by ID."""
    mem = _get_mem(ctx)
    record = mem.get(id)
    if record:
        click.echo(json.dumps(record.to_dict(), indent=2))
    else:
        click.echo(f"Not found: {id}", err=True)
        sys.exit(1)
    mem.close()


@main.command()
@click.argument("id")
@click.option("--title", default=None)
@click.option("--content", default=None)
@click.option("--tags", default=None, help="Comma-separated tags.")
@click.pass_context
def update(ctx, id, title, content, tags):
    """Update a memory by ID."""
    mem = _get_mem(ctx)
    kwargs = {}
    if title is not None:
        kwargs["title"] = title
    if content is not None:
        kwargs["content"] = content
    if tags is not None:
        kwargs["tags"] = [t.strip() for t in tags.split(",") if t.strip()]

    record = mem.update(id, **kwargs)
    if record:
        click.echo(f"Updated: {record.id}")
    else:
        click.echo(f"Not found: {id}", err=True)
        sys.exit(1)
    mem.close()


@main.command()
@click.argument("id")
@click.pass_context
def delete(ctx, id):
    """Delete a memory by ID."""
    mem = _get_mem(ctx)
    if mem.delete(id):
        click.echo(f"Deleted: {id}")
    else:
        click.echo(f"Not found: {id}", err=True)
        sys.exit(1)
    mem.close()


@main.command("import")
@click.argument("path", type=click.Path(exists=True))
@click.option("--type", "mem_type", type=click.Choice(MEMORY_TYPES), default=None)
@click.pass_context
def import_cmd(ctx, path, mem_type):
    """Import memories from a markdown file."""
    from .importer import import_markdown

    mem = _get_mem(ctx)
    records = import_markdown(mem, path, type=mem_type)
    click.echo(f"Imported {len(records)} memories from {path}")
    for r in records:
        click.echo(f"  [{r.type}] {r.title}")
    mem.close()


@main.command()
@click.pass_context
def stats(ctx):
    """Show memory statistics."""
    mem = _get_mem(ctx)
    s = mem.stats()
    click.echo(f"Total memories: {s['total']}")
    click.echo(f"Database size: {s['db_size_kb']} KB")
    if s["by_type"]:
        click.echo("By type:")
        for t, c in sorted(s["by_type"].items()):
            click.echo(f"  {t}: {c}")
    mem.close()


@main.command("save-session")
@click.argument("summary")
@click.pass_context
def save_session(ctx, summary):
    """Save session state for the next agent instance."""
    mem = _get_mem(ctx)
    record = mem.save_session(summary)
    click.echo(f"Session saved: {record.id}")
    mem.close()


@main.command("load-session")
@click.pass_context
def load_session(ctx):
    """Load the most recent session state."""
    mem = _get_mem(ctx)
    record = mem.load_session()
    if record:
        click.echo(f"Last session ({record.created_at}):\n")
        click.echo(record.content)
    else:
        click.echo("No previous session found.")
    mem.close()


@main.command()
@click.argument("id")
@click.pass_context
def promote(ctx, id):
    """Promote a memory: hypothesis -> active -> validated."""
    mem = _get_mem(ctx)
    record = mem.promote(id)
    if record:
        click.echo(f"Promoted: {record.id} -> {record.status}")
        click.echo(f"  [{record.type}] {record.title}")
    else:
        click.echo(f"Not found: {id}", err=True)
        sys.exit(1)
    mem.close()


@main.command()
@click.argument("id")
@click.option("--reason", default="", help="Why this memory is deprecated.")
@click.pass_context
def deprecate(ctx, id, reason):
    """Mark a memory as deprecated. Excluded from recall, kept for history."""
    mem = _get_mem(ctx)
    record = mem.deprecate(id, reason=reason)
    if record:
        click.echo(f"Deprecated: {record.id}")
        click.echo(f"  [{record.type}] {record.title}")
        if reason:
            click.echo(f"  Reason: {reason}")
    else:
        click.echo(f"Not found: {id}", err=True)
        sys.exit(1)
    mem.close()


@main.command()
@click.pass_context
def conflicts(ctx):
    """Detect contradictions between active memories."""
    from .governance import detect_conflicts
    mem = _get_mem(ctx)
    found = detect_conflicts(mem._conn, project=ctx.obj.get("project", ""))

    if not found:
        click.echo("No conflicts detected.")
    else:
        click.echo(f"Found {len(found)} potential conflict(s):\n")
        for i, c in enumerate(found, 1):
            icon = "!!" if c.severity == "critical" else "?"
            click.echo(f"  {icon} Conflict {i} ({c.severity})")
            click.echo(f"    A: [{c.memory_a.type}] {c.memory_a.title}")
            click.echo(f"       id: {c.memory_a.id}  status: {c.memory_a.status}")
            click.echo(f"    B: [{c.memory_b.type}] {c.memory_b.title}")
            click.echo(f"       id: {c.memory_b.id}  status: {c.memory_b.status}")
            click.echo(f"    Reason: {c.reason}")
            click.echo()
    mem.close()


@main.command()
@click.option("--days", default=30, help="Days without update to consider stale.")
@click.pass_context
def stale(ctx, days):
    """Find memories that may be outdated."""
    from .governance import detect_stale
    mem = _get_mem(ctx)
    found = detect_stale(mem._conn, project=ctx.obj.get("project", ""), stale_days=days)

    if not found:
        click.echo(f"No stale memories (threshold: {days} days).")
    else:
        click.echo(f"Found {len(found)} stale memory/memories (>{days} days):\n")
        for s in found:
            click.echo(f"  [{s.memory.type}] {s.memory.title}")
            click.echo(f"    id: {s.memory.id}  status: {s.memory.status}")
            click.echo(f"    Last updated: {s.days_since_update} days ago")
            click.echo(f"    Reason: {s.reason}")
            click.echo()
    mem.close()


@main.command()
@click.option("--days", default=30, help="Stale threshold in days.")
@click.pass_context
def health(ctx, days):
    """Run a full health check on the memory system."""
    from .governance import health_check
    mem = _get_mem(ctx)
    report = health_check(mem._conn, project=ctx.obj.get("project", ""), stale_days=days)

    click.echo(f"{'=' * 50}")
    click.echo(f"MEMORY HEALTH: {report.health_score:.0f}/100")
    click.echo(f"{'=' * 50}")
    click.echo(f"  Total memories: {report.total_memories}")
    click.echo(f"  By status:")
    for status in ("validated", "active", "hypothesis", "deprecated", "superseded"):
        count = report.by_status.get(status, 0)
        if count:
            click.echo(f"    {status}: {count}")
    click.echo(f"  Never accessed: {report.never_accessed}")
    click.echo()

    if report.conflicts:
        click.echo(f"  CONFLICTS: {len(report.conflicts)}")
        for c in report.conflicts:
            icon = "!!" if c.severity == "critical" else "?"
            click.echo(f"    {icon} {c.memory_a.title[:40]} vs {c.memory_b.title[:40]}")

    if report.stale:
        click.echo(f"  STALE: {len(report.stale)}")
        for s in report.stale[:5]:
            click.echo(f"    {s.memory.title[:50]} ({s.days_since_update}d)")
        if len(report.stale) > 5:
            click.echo(f"    ... and {len(report.stale) - 5} more")

    if report.orphaned_supersedes:
        click.echo(f"  ORPHANED: {len(report.orphaned_supersedes)}")

    if report.health_score >= 100:
        validated = report.by_status.get("validated", 0)
        click.echo(f"  Fully governed. 0 conflicts, 0 stale, {validated} validated rules.")
        click.echo(f"  You're running a clean memory system. That's rare.")
        click.echo(f"\n  If this helped, share your setup:")
        click.echo(f"    https://github.com/thezenmonster/agentmem/discussions")

    click.echo(f"\n{'=' * 50}")
    mem.close()


@main.command()
@click.option("--tool", type=click.Choice(["claude", "cursor", "codex", "windsurf"]),
              default=None, help="Generate MCP config for this tool.")
@click.option("--project", "proj", default="", help="Project name for scoping.")
@click.pass_context
def init(ctx, tool, proj):
    """Set up agentmem in 30 seconds. Creates DB, adds a starter memory, shows health."""
    import os
    from pathlib import Path

    db_path = ctx.obj["db"]
    project = proj or ctx.obj.get("project", "") or Path.cwd().name

    click.echo("agentmem init")
    click.echo(f"{'=' * 50}\n")

    # Step 1: Create DB
    mem = Memory(path=db_path, project=project)
    is_new = mem.stats()["total"] == 0
    if is_new:
        click.echo(f"  [1/4] Created database: {db_path}")
    else:
        click.echo(f"  [1/4] Database exists: {db_path} ({mem.stats()['total']} memories)")

    # Step 2: Add starter memory if empty
    if is_new:
        mem.add(
            type="context",
            title=f"Project: {project}",
            content=f"This memory database was initialized for project '{project}'. "
                    f"Add memories with mem.add() or the CLI. "
                    f"Run 'agentmem health' to check system status.",
            status="active",
        )
        click.echo(f"  [2/4] Added starter memory for project '{project}'")
    else:
        click.echo(f"  [2/4] Skipped starter memory (DB already has content)")

    # Step 3: Generate MCP config
    # Detect the agentmem command path
    agentmem_cmd = "agentmem"
    db_abs = str(Path(db_path).resolve()).replace("\\", "/")

    if tool:
        # Check MCP dependency
        try:
            import mcp  # noqa: F401
        except ImportError:
            click.echo(f"  [!] MCP package not installed. Run:")
            click.echo(f"      pip install quilmem[mcp]")
            click.echo()

        click.echo(f"  [3/4] MCP config for {tool}:\n")

        if tool in ("claude",):
            config = {
                "mcpServers": {
                    "agentmem": {
                        "command": agentmem_cmd,
                        "args": ["--db", db_abs, "--project", project, "serve"],
                        "type": "stdio"
                    }
                }
            }
            config_path = ".claude/settings.json" if tool == "claude" else ""
            click.echo(f"    Add to {config_path} (or ~/.claude/settings.json for global):\n")
            click.echo(f"    {json.dumps(config, indent=2).replace(chr(10), chr(10) + '    ')}")

        elif tool in ("cursor", "windsurf"):
            config = {
                "mcpServers": {
                    "agentmem": {
                        "command": agentmem_cmd,
                        "args": ["--db", db_abs, "--project", project, "serve"]
                    }
                }
            }
            dir_name = ".cursor" if tool == "cursor" else ".windsurf"
            click.echo(f"    Add to {dir_name}/mcp.json (or ~/{dir_name}/mcp.json for global):\n")
            click.echo(f"    {json.dumps(config, indent=2).replace(chr(10), chr(10) + '    ')}")

        elif tool == "codex":
            click.echo(f"    Add to ~/.codex/config.toml (or .codex/config.toml for project):\n")
            click.echo(f'    [mcp_servers.agentmem]')
            click.echo(f'    command = "{agentmem_cmd}"')
            click.echo(f'    args = ["--db", "{db_abs}", "--project", "{project}", "serve"]')

        click.echo()
    else:
        click.echo(f"  [3/4] Skipped MCP config (use --tool claude|cursor|codex|windsurf)")

    # Step 4: Health check
    from .governance import health_check
    report = health_check(mem._conn, project=project)
    click.echo(f"  [4/4] Health: {report.health_score:.0f}/100 | "
               f"Memories: {report.total_memories} | "
               f"Conflicts: {len(report.conflicts)} | "
               f"Stale: {len(report.stale)}")

    mem.close()

    click.echo(f"\n{'=' * 50}")
    click.echo(f"  Done. Your memory DB is at: {db_abs}")
    click.echo(f"  Project: {project}")
    click.echo(f"\n  Try the differentiators:")
    click.echo(f"    # Add a rule you're certain about")
    click.echo(f"    agentmem add --type decision --status validated \\")
    click.echo(f"      --title \"Never force-push to main\" \"Enforced after incident.\"")
    click.echo(f"")
    click.echo(f"    # Add something unproven")
    click.echo(f"    agentmem add --type decision --status hypothesis \\")
    click.echo(f"      --title \"Maybe batch DB writes\" \"Needs benchmarking.\"")
    click.echo(f"")
    click.echo(f"    # Save your session so the next agent picks up where you left off")
    click.echo(f"    agentmem save-session \"Working on auth refactor. Blocked on tokens.\"")
    click.echo(f"    agentmem load-session")
    click.echo(f"")
    click.echo(f"    # Check what your agent should trust")
    click.echo(f"    agentmem health")
    if not tool:
        click.echo(f"")
        click.echo(f"    # Connect to your coding agent")
        click.echo(f"    agentmem init --tool claude   # or cursor, codex, windsurf")
    click.echo(f"{'=' * 50}")
    click.echo(f"\n  Something break? {NEW_ISSUE_URL}")
    click.echo(f"  Paste debug context: agentmem debug-info")


@main.command()
@click.pass_context
def doctor(ctx):
    """Check if agentmem is set up correctly. Diagnoses common problems."""
    import os
    from pathlib import Path

    db_path = ctx.obj["db"]
    project = ctx.obj.get("project", "")
    all_ok = True

    click.echo("agentmem doctor")
    click.echo(f"{'=' * 50}\n")

    # Check 1: Database exists and is readable
    db_exists = Path(db_path).exists()
    if db_exists:
        try:
            mem = Memory(path=db_path, project=project)
            stats = mem.stats()
            click.echo(f"  [OK] Database: {db_path} ({stats['total']} memories, {stats['db_size_kb']} KB)")
        except Exception as e:
            click.echo(f"  [FAIL] Database: {db_path} -- {e}")
            all_ok = False
            mem = None
    else:
        click.echo(f"  [FAIL] Database not found: {db_path}")
        click.echo(f"         Run: agentmem init")
        all_ok = False
        mem = None

    # Check 2: MCP dependency
    try:
        import mcp  # noqa: F401
        click.echo(f"  [OK] MCP package installed")
    except ImportError:
        click.echo(f"  [WARN] MCP package not installed")
        click.echo(f"         Run: pip install quilmem[mcp]")

    # Check 3: Schema version
    if mem:
        try:
            row = mem._conn.execute("SELECT MAX(version) FROM schema_version").fetchone()
            version = row[0] if row else 0
            if version >= 2:
                click.echo(f"  [OK] Schema version: {version} (governance enabled)")
            else:
                click.echo(f"  [WARN] Schema version: {version} (governance not migrated)")
                click.echo(f"         This will auto-migrate on next use.")
        except Exception:
            click.echo(f"  [WARN] Could not check schema version")

    # Check 4: Health check
    if mem:
        from .governance import health_check
        report = health_check(mem._conn, project=project)
        if report.health_score >= 70:
            click.echo(f"  [OK] Health: {report.health_score:.0f}/100")
        elif report.health_score >= 40:
            click.echo(f"  [WARN] Health: {report.health_score:.0f}/100")
            if report.conflicts:
                click.echo(f"         {len(report.conflicts)} conflicts -- run: agentmem conflicts")
            if report.stale:
                click.echo(f"         {len(report.stale)} stale -- run: agentmem stale")
        else:
            click.echo(f"  [FAIL] Health: {report.health_score:.0f}/100 -- needs attention")
            all_ok = False

    # Check 5: Project scoping
    if mem and project:
        click.echo(f"  [OK] Project: {project}")
    elif mem:
        click.echo(f"  [WARN] No project scope set (memories not isolated)")
        click.echo(f"         Use: agentmem --project myproject <command>")

    # Check 6: Governance status
    if mem:
        by_status = {}
        for row in mem._conn.execute(
            "SELECT COALESCE(status, 'active') as s, COUNT(*) as c FROM memories GROUP BY s"
        ):
            by_status[row["s"]] = row["c"]
        validated = by_status.get("validated", 0)
        if validated > 0:
            click.echo(f"  [OK] Validated memories: {validated}")
        elif stats["total"] > 0:
            click.echo(f"  [WARN] No validated memories yet")
            click.echo(f"         Promote trusted rules: agentmem promote <id>")

    if mem:
        mem.close()

    click.echo(f"\n{'=' * 50}")
    if all_ok:
        click.echo(f"  All checks passed.")
    else:
        click.echo(f"  Some checks failed. See above for fixes.")
        click.echo(f"\n  Still stuck? {NEW_ISSUE_URL}")
        click.echo(f"  Paste debug context: agentmem debug-info")
    click.echo(f"{'=' * 50}")


ISSUES_URL = "https://github.com/thezenmonster/agentmem/issues"
NEW_ISSUE_URL = f"{ISSUES_URL}/new/choose"


@main.command("debug-info")
@click.option("--json-output", "as_json", is_flag=True, help="Output as JSON for pasting into issues.")
@click.pass_context
def debug_info(ctx, as_json):
    """Print system info for bug reports. Paste the output into a GitHub issue."""
    import platform
    from pathlib import Path

    db_path = ctx.obj["db"]
    project = ctx.obj.get("project", "")

    info = {
        "agentmem_version": __version__,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "os": platform.system(),
        "db_path": str(Path(db_path).resolve()),
        "db_exists": Path(db_path).exists(),
        "project": project,
    }

    # Check MCP
    try:
        import mcp
        info["mcp_installed"] = True
        info["mcp_version"] = getattr(mcp, "__version__", "unknown")
    except ImportError:
        info["mcp_installed"] = False

    # DB stats if exists
    if info["db_exists"]:
        try:
            mem = Memory(path=db_path, project=project)
            stats = mem.stats()
            info["total_memories"] = stats["total"]
            info["db_size_kb"] = stats["db_size_kb"]

            row = mem._conn.execute("SELECT MAX(version) FROM schema_version").fetchone()
            info["schema_version"] = row[0] if row else 0

            from .governance import health_check as hc
            report = hc(mem._conn, project=project)
            info["health_score"] = report.health_score
            info["conflicts"] = len(report.conflicts)
            info["stale"] = len(report.stale)

            by_status = {}
            for r in mem._conn.execute(
                "SELECT COALESCE(status, 'active') as s, COUNT(*) as c FROM memories GROUP BY s"
            ):
                by_status[r["s"]] = r["c"]
            info["by_status"] = by_status

            mem.close()
        except Exception as e:
            info["db_error"] = str(e)

    if as_json:
        click.echo(json.dumps(info, indent=2))
    else:
        click.echo("agentmem debug-info")
        click.echo(f"{'=' * 50}")
        click.echo(f"  agentmem:  {info['agentmem_version']}")
        click.echo(f"  Python:    {info['python_version']}")
        click.echo(f"  Platform:  {info['platform']}")
        click.echo(f"  DB:        {info['db_path']} ({'exists' if info['db_exists'] else 'NOT FOUND'})")
        click.echo(f"  Project:   {info.get('project', '(none)')}")
        click.echo(f"  MCP:       {'yes' + (' v' + info.get('mcp_version', '?')) if info.get('mcp_installed') else 'not installed'}")
        if info.get("total_memories") is not None:
            click.echo(f"  Memories:  {info['total_memories']} ({info['db_size_kb']} KB)")
            click.echo(f"  Schema:    v{info.get('schema_version', '?')}")
            click.echo(f"  Health:    {info['health_score']:.0f}/100 | Conflicts: {info['conflicts']} | Stale: {info['stale']}")
            if info.get("by_status"):
                parts = [f"{s}: {c}" for s, c in sorted(info["by_status"].items())]
                click.echo(f"  Status:    {', '.join(parts)}")
        if info.get("db_error"):
            click.echo(f"  DB Error:  {info['db_error']}")
        click.echo(f"{'=' * 50}")
        click.echo(f"\n  Paste this into a bug report: {NEW_ISSUE_URL}")


@main.command()
@click.pass_context
def serve(ctx):
    """Start MCP stdio server."""
    try:
        from .mcp_server import run_server
    except ImportError:
        click.echo("MCP support requires: pip install quilmem[mcp]", err=True)
        sys.exit(1)
    run_server(db_path=ctx.obj["db"], project=ctx.obj.get("project", ""))
