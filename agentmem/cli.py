"""CLI interface for agentmem."""

from __future__ import annotations

import json
import sys

import click

from .core import Memory
from .models import MEMORY_TYPES


def _get_mem(ctx: click.Context) -> Memory:
    return Memory(path=ctx.obj["db"], project=ctx.obj.get("project", ""))


@click.group()
@click.option("--db", default="./memory.db", envvar="AGENTMEM_DB", help="Database path.")
@click.option("--project", default="", help="Project scope.")
@click.pass_context
def main(ctx, db, project):
    """agentmem — Production-ready agent memory."""
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
