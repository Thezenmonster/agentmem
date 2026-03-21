"""Core Memory class — all database operations."""

from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .models import MEMORY_TYPES, MemoryRecord
from .schema import init_db


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row_to_record(row: sqlite3.Row, rank: float | None = None) -> MemoryRecord:
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


class Memory:
    """Production-ready agent memory backed by SQLite + FTS5.

    Usage:
        mem = Memory("./memory.db")
        mem.add(type="bug", title="loudnorm undoes SFX", content="...")
        results = mem.search("audio mixing")
        context = mem.recall("building narration", max_tokens=2000)
    """

    def __init__(
        self,
        path: str = "./memory.db",
        project: str = "",
        token_counter: callable | None = None,
    ):
        self.path = Path(path)
        self.project = project
        self._token_counter = token_counter or (lambda text: len(text) // 4)
        self._conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        init_db(self._conn)

    def add(
        self,
        type: str,
        title: str,
        content: str,
        tags: list[str] | None = None,
        source: str = "api",
        project: str | None = None,
        confidence: float = 1.0,
        supersedes: str = "",
    ) -> MemoryRecord:
        if type not in MEMORY_TYPES:
            raise ValueError(f"Invalid type '{type}'. Must be one of: {MEMORY_TYPES}")

        record_id = str(uuid.uuid4())
        now = _now()
        tags_str = ",".join(tags) if tags else ""
        proj = project if project is not None else self.project

        self._conn.execute(
            """INSERT INTO memories
               (id, type, title, content, tags, source, project, confidence,
                supersedes, created_at, updated_at, accessed_at, access_count)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)""",
            (record_id, type, title, content, tags_str, source, proj,
             confidence, supersedes, now, now, now),
        )
        self._conn.commit()

        return MemoryRecord(
            id=record_id, type=type, title=title, content=content,
            tags=tags or [], source=source, project=proj,
            confidence=confidence, supersedes=supersedes,
            created_at=now, updated_at=now, accessed_at=now, access_count=0,
        )

    def get(self, id: str) -> MemoryRecord | None:
        row = self._conn.execute(
            "SELECT * FROM memories WHERE id = ?", (id,)
        ).fetchone()
        if not row:
            return None

        self._conn.execute(
            "UPDATE memories SET accessed_at = ?, access_count = access_count + 1 WHERE id = ?",
            (_now(), id),
        )
        self._conn.commit()
        return _row_to_record(row)

    def update(self, id: str, **kwargs) -> MemoryRecord | None:
        record = self.get(id)
        if not record:
            return None

        allowed = {"title", "content", "tags", "type", "confidence", "project", "supersedes"}
        updates = {k: v for k, v in kwargs.items() if k in allowed and v is not None}
        if not updates:
            return record

        if "tags" in updates and isinstance(updates["tags"], list):
            updates["tags"] = ",".join(updates["tags"])
        if "type" in updates and updates["type"] not in MEMORY_TYPES:
            raise ValueError(f"Invalid type '{updates['type']}'. Must be one of: {MEMORY_TYPES}")

        updates["updated_at"] = _now()
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [id]

        self._conn.execute(f"UPDATE memories SET {set_clause} WHERE id = ?", values)
        self._conn.commit()
        return self.get(id)

    def delete(self, id: str) -> bool:
        cur = self._conn.execute("DELETE FROM memories WHERE id = ?", (id,))
        self._conn.commit()
        return cur.rowcount > 0

    def list(
        self,
        type: str | None = None,
        project: str | None = None,
        since: str | None = None,
        limit: int = 50,
    ) -> list[MemoryRecord]:
        conditions = []
        params = []

        if type:
            conditions.append("type = ?")
            params.append(type)
        if project is not None:
            conditions.append("project = ?")
            params.append(project)
        elif self.project:
            conditions.append("project = ?")
            params.append(self.project)
        if since:
            conditions.append("created_at >= ?")
            params.append(since)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        params.append(limit)

        rows = self._conn.execute(
            f"SELECT * FROM memories {where} ORDER BY updated_at DESC LIMIT ?",
            params,
        ).fetchall()
        return [_row_to_record(r) for r in rows]

    def search(
        self,
        query: str,
        type: str | None = None,
        tags: list[str] | None = None,
        project: str | None = None,
        limit: int = 10,
    ) -> list[MemoryRecord]:
        from .search import fts_search
        return fts_search(self._conn, query, type=type, tags=tags,
                          project=project or self.project, limit=limit)

    def recall(
        self,
        query: str,
        max_tokens: int = 4000,
        format: str = "markdown",
    ) -> str:
        from .search import recall
        return recall(self._conn, query, max_tokens=max_tokens,
                      token_counter=self._token_counter,
                      project=self.project, format=format)

    def stats(self) -> dict:
        total = self._conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
        by_type = {}
        for row in self._conn.execute("SELECT type, COUNT(*) as c FROM memories GROUP BY type"):
            by_type[row["type"]] = row["c"]

        db_size = self.path.stat().st_size if self.path.exists() else 0
        return {
            "total": total,
            "by_type": by_type,
            "db_size_kb": round(db_size / 1024, 1),
        }

    def close(self):
        self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
