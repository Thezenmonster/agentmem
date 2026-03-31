"""CLI interface for agentmem."""

from __future__ import annotations

import json
import sys

import click

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
@click.option("--tags", default="", help="Comma-separated tags.")
@click.argument("content")
@click.pass_context
def add(ctx, mem_type, title, tags, content):
    """Add a memory."""
    mem = _get_mem(ctx)
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    record = mem.add(type=mem_type, title=title, content=content, tags=tag_list, source="cli")
    click.echo(f"Added: {record.id}")
    click.echo(f"  [{record.type}] {record.title}")
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

    click.echo(f"\n{'=' * 50}")
    mem.close()


@main.command()
@click.pass_context
def serve(ctx):
    """Start MCP stdio server."""
    try:
        from .mcp_server import run_server
    except ImportError:
        click.echo("MCP support requires: pip install agentmem[mcp]", err=True)
        sys.exit(1)
    run_server(db_path=ctx.obj["db"], project=ctx.obj.get("project", ""))
