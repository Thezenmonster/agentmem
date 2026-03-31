"""Import memories from markdown files."""

from __future__ import annotations

import re
from pathlib import Path


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """Extract YAML-like frontmatter from markdown. Returns (metadata, body)."""
    if not text.startswith("---"):
        return {}, text

    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text

    meta = {}
    for line in parts[1].strip().splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            meta[key.strip()] = value.strip()

    return meta, parts[2].strip()


def _split_sections(text: str) -> list[tuple[str, str]]:
    """Split markdown by H2/H3 headers. Returns [(title, body), ...]."""
    sections = []
    current_title = ""
    current_body = []

    for line in text.splitlines():
        match = re.match(r"^#{2,3}\s+(.+)", line)
        if match:
            if current_title or current_body:
                sections.append((current_title, "\n".join(current_body).strip()))
            current_title = match.group(1).strip()
            current_body = []
        else:
            current_body.append(line)

    if current_title or current_body:
        sections.append((current_title, "\n".join(current_body).strip()))

    return [(t, b) for t, b in sections if b]


def _extract_tags(text: str) -> list[str]:
    """Extract inline tags from text. Looks for `tags: x, y, z` patterns."""
    match = re.search(r"tags?:\s*(.+)", text, re.IGNORECASE)
    if match:
        return [t.strip().lower() for t in match.group(1).split(",") if t.strip()]
    return []


def import_markdown(
    memory,
    path: str,
    type: str | None = None,
    project: str = "",
    source: str | None = None,
) -> list:
    """Import a markdown file into memory. Each H2/H3 section becomes a memory.

    Args:
        memory: Memory instance
        path: Path to markdown file
        type: Memory type override (if not set, uses frontmatter or 'context')
        project: Project scope
        source: Source identifier (defaults to filename)

    Returns:
        List of created MemoryRecord objects
    """
    filepath = Path(path)
    if not filepath.exists():
        raise FileNotFoundError(f"File not found: {path}")

    text = filepath.read_text(encoding="utf-8")
    meta, body = _parse_frontmatter(text)

    default_type = type or meta.get("type", "context")
    default_project = project or meta.get("project", "")
    src = source or f"import:{filepath.name}"

    sections = _split_sections(body)
    if not sections:
        # No sections -- treat entire body as one memory
        sections = [(filepath.stem.replace("_", " ").replace("-", " ").title(), body)]

    # Fill in empty titles from filename
    sections = [
        (t if t else filepath.stem.replace("_", " ").replace("-", " ").title(), b)
        for t, b in sections
    ]

    records = []
    for title, content in sections:
        tags = _extract_tags(content)

        # Try to infer type from title keywords
        mem_type = default_type
        title_lower = title.lower()
        if any(w in title_lower for w in ("bug", "fix", "error", "issue")):
            mem_type = "bug"
        elif any(w in title_lower for w in ("setting", "config", "profile")):
            mem_type = "setting"
        elif any(w in title_lower for w in ("decision", "rule", "policy", "ban")):
            mem_type = "decision"
        elif any(w in title_lower for w in ("step", "pipeline", "workflow", "procedure")):
            mem_type = "procedure"
        elif any(w in title_lower for w in ("feedback", "preference", "correction")):
            mem_type = "feedback"

        record = memory.add(
            type=mem_type,
            title=title,
            content=content,
            tags=tags,
            source=src,
            project=default_project,
        )
        records.append(record)

    return records
