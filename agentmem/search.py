"""FTS5 search, ranking, and context-budgeted recall."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from .models import MemoryRecord


def _row_to_record(row: sqlite3.Row, rank: float) -> MemoryRecord:
    return MemoryRecord(
        id=row["id"],
        type=row["type"],
        title=row["title"],
        content=row["content"],
        tags=[t.strip() for t in row["tags"].split(",") if t.strip()],
        source=row["source"],
        project=row["project"],
        confidence=row["confidence"],
        supersedes=row["supersedes"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        accessed_at=row["accessed_at"],
        access_count=row["access_count"],
        rank=rank,
    )


def _recency_score(accessed_at: str) -> float:
    """Score 0-1 based on how recently the memory was accessed. 1.0 = now."""
    try:
        ts = datetime.fromisoformat(accessed_at)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        delta = (datetime.now(timezone.utc) - ts).total_seconds()
        # Half-life of 7 days
        return 2.0 ** (-delta / (7 * 86400))
    except (ValueError, TypeError):
        return 0.5


def _frequency_score(access_count: int) -> float:
    """Score 0-1 based on access frequency. Logarithmic scale."""
    if access_count <= 0:
        return 0.0
    import math
    return min(1.0, math.log1p(access_count) / math.log1p(100))


def fts_search(
    conn: sqlite3.Connection,
    query: str,
    type: str | None = None,
    tags: list[str] | None = None,
    project: str = "",
    limit: int = 10,
) -> list[MemoryRecord]:
    """Full-text search with optional filters. Returns ranked results."""
    # Build FTS5 query — split into terms, quote each to avoid operator conflicts
    terms = query.replace('"', '""').split()
    fts_query = " OR ".join(f'"{t}"' for t in terms if t)

    conditions = []
    params = []

    if type:
        conditions.append("m.type = ?")
        params.append(type)
    if project:
        conditions.append("m.project = ?")
        params.append(project)
    if tags:
        for tag in tags:
            conditions.append("m.tags LIKE ?")
            params.append(f"%{tag}%")

    where = f"AND {' AND '.join(conditions)}" if conditions else ""

    sql = f"""
        SELECT m.*, fts.rank as fts_rank
        FROM memories_fts fts
        JOIN memories m ON m.rowid = fts.rowid
        WHERE memories_fts MATCH ?
        {where}
        ORDER BY fts.rank
        LIMIT ?
    """
    params = [fts_query] + params + [limit * 5]  # over-fetch for re-ranking

    try:
        rows = conn.execute(sql, params).fetchall()
    except sqlite3.OperationalError:
        return []

    # Re-rank with composite score
    scored = []
    for row in rows:
        fts_rank = -row["fts_rank"]  # FTS5 rank is negative, lower = better
        recency = _recency_score(row["accessed_at"])
        frequency = _frequency_score(row["access_count"])
        confidence = row["confidence"]

        composite = (
            fts_rank * 0.4
            + recency * 0.2
            + frequency * 0.2
            + confidence * 0.2
        )
        scored.append((row, composite))

    scored.sort(key=lambda x: x[1], reverse=True)

    results = []
    for row, score in scored[:limit]:
        record = _row_to_record(row, rank=round(score, 4))
        results.append(record)

    # Bump access stats for returned results
    now = datetime.now(timezone.utc).isoformat()
    for r in results:
        conn.execute(
            "UPDATE memories SET accessed_at = ?, access_count = access_count + 1 WHERE id = ?",
            (now, r.id),
        )
    conn.commit()

    return results


def recall(
    conn: sqlite3.Connection,
    query: str,
    max_tokens: int = 4000,
    token_counter: callable | None = None,
    project: str = "",
    format: str = "markdown",
) -> str:
    """Context-budgeted retrieval. Returns formatted memories within token limit."""
    counter = token_counter or (lambda text: len(text) // 4)

    # Get a large pool of candidates
    candidates = fts_search(conn, query, project=project, limit=50)
    if not candidates:
        return ""

    # Greedy pack into token budget
    selected = []
    used_tokens = 0

    for record in candidates:
        formatted = _format_record(record, format)
        tokens = counter(formatted)
        if used_tokens + tokens > max_tokens:
            continue
        selected.append(formatted)
        used_tokens += tokens

    if not selected:
        # At minimum, include the top result truncated
        top = _format_record(candidates[0], format)
        return top[:max_tokens * 4]  # rough char limit

    separator = "\n\n---\n\n" if format == "markdown" else "\n\n"
    return separator.join(selected)


def _format_record(record: MemoryRecord, format: str = "markdown") -> str:
    if format == "markdown":
        parts = [f"### [{record.type}] {record.title}"]
        parts.append(record.content)
        if record.tags:
            parts.append(f"*tags: {', '.join(record.tags)}*")
        return "\n".join(parts)
    else:
        return f"[{record.type}] {record.title}\n{record.content}"
