"""Core Memory class — all database operations."""

from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .models import MEMORY_TYPES, MEMORY_STATUSES, MemoryRecord
from .schema import init_db


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_get(row, key, default=""):
    """Safely get a column value, returning default if column doesn't exist."""
    try:
        return row[key]
    except (IndexError, KeyError):
        return default


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
        status=_safe_get(row, "status", "active"),
        source_path=_safe_get(row, "source_path", ""),
        source_section=_safe_get(row, "source_section", ""),
        source_hash=_safe_get(row, "source_hash", ""),
        validated_at=_safe_get(row, "validated_at", ""),
        deprecated_at=_safe_get(row, "deprecated_at", ""),
        superseded_by=_safe_get(row, "superseded_by", ""),
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
        status: str = "active",
        source_path: str = "",
        source_section: str = "",
        source_hash: str = "",
    ) -> MemoryRecord:
        if type not in MEMORY_TYPES:
            raise ValueError(f"Invalid type '{type}'. Must be one of: {MEMORY_TYPES}")
        if status not in MEMORY_STATUSES:
            raise ValueError(f"Invalid status '{status}'. Must be one of: {MEMORY_STATUSES}")

        record_id = str(uuid.uuid4())
        now = _now()
        tags_str = ",".join(tags) if tags else ""
        proj = project if project is not None else self.project
        validated_at = now if status == "validated" else ""

        self._conn.execute(
            """INSERT INTO memories
               (id, type, title, content, tags, source, project, confidence,
                supersedes, status, source_path, source_section, source_hash,
                validated_at, deprecated_at, superseded_by,
                created_at, updated_at, accessed_at, access_count)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '', '', ?, ?, ?, 0)""",
            (record_id, type, title, content, tags_str, source, proj,
             confidence, supersedes, status, source_path, source_section,
             source_hash, validated_at, now, now, now),
        )
        self._conn.commit()

        return MemoryRecord(
            id=record_id, type=type, title=title, content=content,
            tags=tags or [], source=source, project=proj,
            confidence=confidence, supersedes=supersedes,
            status=status, source_path=source_path,
            source_section=source_section, source_hash=source_hash,
            validated_at=validated_at,
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

        allowed = {"title", "content", "tags", "type", "confidence", "project",
                    "supersedes", "status", "source_path", "source_section",
                    "source_hash", "validated_at", "deprecated_at", "superseded_by"}
        updates = {k: v for k, v in kwargs.items() if k in allowed and v is not None}
        if not updates:
            return record

        if "tags" in updates and isinstance(updates["tags"], list):
            updates["tags"] = ",".join(updates["tags"])
        if "type" in updates and updates["type"] not in MEMORY_TYPES:
            raise ValueError(f"Invalid type '{updates['type']}'. Must be one of: {MEMORY_TYPES}")
        if "status" in updates and updates["status"] not in MEMORY_STATUSES:
            raise ValueError(f"Invalid status '{updates['status']}'. Must be one of: {MEMORY_STATUSES}")

        updates["updated_at"] = _now()
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [id]

        self._conn.execute(f"UPDATE memories SET {set_clause} WHERE id = ?", values)
        self._conn.commit()
        return self.get(id)

    # ── Truth governance lifecycle ──────────────────────────────────

    def promote(self, id: str) -> MemoryRecord | None:
        """Promote a memory: hypothesis → active → validated.
        Each call advances one step. Validated is the highest trust level."""
        record = self.get(id)
        if not record:
            return None

        promotions = {"hypothesis": "active", "active": "validated"}
        next_status = promotions.get(record.status)
        if not next_status:
            return record  # Already validated or in a terminal state

        now = _now()
        updates = {"status": next_status, "updated_at": now}
        if next_status == "validated":
            updates["validated_at"] = now

        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [id]
        self._conn.execute(f"UPDATE memories SET {set_clause} WHERE id = ?", values)
        self._conn.commit()
        return self.get(id)

    def deprecate(self, id: str, reason: str = "") -> MemoryRecord | None:
        """Mark a memory as deprecated. Excluded from recall, kept for history."""
        record = self.get(id)
        if not record:
            return None

        now = _now()
        content = record.content
        if reason:
            content = f"{content}\n\n[DEPRECATED {now[:10]}] {reason}"

        self._conn.execute(
            "UPDATE memories SET status = 'deprecated', deprecated_at = ?, "
            "content = ?, updated_at = ? WHERE id = ?",
            (now, content, now, id),
        )
        self._conn.commit()
        return self.get(id)

    def supersede(self, old_id: str, new_id: str) -> tuple[MemoryRecord | None, MemoryRecord | None]:
        """Mark old_id as superseded by new_id. Old memory points to replacement."""
        old = self.get(old_id)
        new = self.get(new_id)
        if not old or not new:
            return (old, new)

        now = _now()
        self._conn.execute(
            "UPDATE memories SET status = 'superseded', superseded_by = ?, "
            "deprecated_at = ?, updated_at = ? WHERE id = ?",
            (new_id, now, now, old_id),
        )
        self._conn.execute(
            "UPDATE memories SET supersedes = ?, updated_at = ? WHERE id = ?",
            (old_id, now, new_id),
        )
        self._conn.commit()
        return (self.get(old_id), self.get(new_id))

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

    def save_session(self, summary: str, tags: list[str] | None = None) -> MemoryRecord:
        """Save current session state. Supersedes any previous session for this project.

        Call this before a conversation ends or when context is about to compress.
        The summary should capture: what's in progress, what's blocked, what's done,
        and any decisions made this session.
        """
        # Find previous active session
        prev = self._conn.execute(
            "SELECT id FROM memories WHERE type = 'session' AND project = ? "
            "AND COALESCE(status, 'active') = 'active' "
            "ORDER BY created_at DESC LIMIT 1",
            (self.project,),
        ).fetchone()

        prev_id = prev["id"] if prev else ""

        # Create new session
        new_record = self.add(
            type="session",
            title=f"Session state — {self.project or 'default'}",
            content=summary,
            tags=tags or ["session", "state"],
            source="session",
            supersedes=prev_id,
        )

        # Actually supersede the old session using the governance lifecycle
        if prev_id:
            self.supersede(prev_id, new_record.id)

        return new_record

    def load_session(self) -> MemoryRecord | None:
        """Load the most recent session state for this project.

        Call this at the start of a conversation to pick up where the last instance left off.
        """
        row = self._conn.execute(
            "SELECT * FROM memories WHERE type = 'session' AND project = ? "
            "ORDER BY created_at DESC LIMIT 1",
            (self.project,),
        ).fetchone()
        if not row:
            return None

        self._conn.execute(
            "UPDATE memories SET accessed_at = ?, access_count = access_count + 1 WHERE id = ?",
            (_now(), row["id"]),
        )
        self._conn.commit()
        return _row_to_record(row)

    def close(self):
        self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
