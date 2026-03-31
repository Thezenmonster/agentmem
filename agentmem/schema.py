"""Database schema and migrations for agentmem."""

SCHEMA_VERSION = 2

SCHEMA_V1_SQL = """
CREATE TABLE IF NOT EXISTS memories (
    id           TEXT PRIMARY KEY,
    type         TEXT NOT NULL,
    title        TEXT NOT NULL,
    content      TEXT NOT NULL,
    tags         TEXT DEFAULT '',
    source       TEXT DEFAULT '',
    project      TEXT DEFAULT '',
    confidence   REAL DEFAULT 1.0,
    supersedes   TEXT DEFAULT '',
    created_at   TEXT NOT NULL,
    updated_at   TEXT NOT NULL,
    accessed_at  TEXT NOT NULL,
    access_count INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(type);
CREATE INDEX IF NOT EXISTS idx_memories_project ON memories(project);
CREATE INDEX IF NOT EXISTS idx_memories_created ON memories(created_at);

CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
    title,
    content,
    tags,
    content=memories,
    content_rowid=rowid,
    tokenize='porter unicode61'
);

CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
    INSERT INTO memories_fts(rowid, title, content, tags)
    VALUES (new.rowid, new.title, new.content, new.tags);
END;

CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
    INSERT INTO memories_fts(memories_fts, rowid, title, content, tags)
    VALUES ('delete', old.rowid, old.title, old.content, old.tags);
END;

CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories BEGIN
    INSERT INTO memories_fts(memories_fts, rowid, title, content, tags)
    VALUES ('delete', old.rowid, old.title, old.content, old.tags);
    INSERT INTO memories_fts(rowid, title, content, tags)
    VALUES (new.rowid, new.title, new.content, new.tags);
END;

CREATE TABLE IF NOT EXISTS schema_version (
    version    INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);
"""

# v2: Truth governance -- memory states, provenance, lifecycle
MIGRATION_V2_SQL = """
ALTER TABLE memories ADD COLUMN status TEXT DEFAULT 'active';
ALTER TABLE memories ADD COLUMN source_path TEXT DEFAULT '';
ALTER TABLE memories ADD COLUMN source_section TEXT DEFAULT '';
ALTER TABLE memories ADD COLUMN source_hash TEXT DEFAULT '';
ALTER TABLE memories ADD COLUMN validated_at TEXT DEFAULT '';
ALTER TABLE memories ADD COLUMN deprecated_at TEXT DEFAULT '';
ALTER TABLE memories ADD COLUMN superseded_by TEXT DEFAULT '';

CREATE INDEX IF NOT EXISTS idx_memories_status ON memories(status);
CREATE INDEX IF NOT EXISTS idx_memories_source_path ON memories(source_path);
CREATE INDEX IF NOT EXISTS idx_memories_source_hash ON memories(source_hash);
"""


def init_db(conn):
    """Initialize the database schema. Safe to call multiple times."""
    cur = conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL")

    current_version = 0
    try:
        row = cur.execute("SELECT MAX(version) FROM schema_version").fetchone()
        if row and row[0]:
            current_version = row[0]
    except Exception:
        pass

    if current_version >= SCHEMA_VERSION:
        return

    if current_version < 1:
        cur.executescript(SCHEMA_V1_SQL)
        cur.execute(
            "INSERT OR REPLACE INTO schema_version (version, applied_at) VALUES (?, datetime('now'))",
            (1,),
        )
        conn.commit()
        current_version = 1

    if current_version < 2:
        # Run v2 migration -- add governance columns
        for stmt in MIGRATION_V2_SQL.strip().split(";"):
            stmt = stmt.strip()
            if not stmt:
                continue
            try:
                cur.execute(stmt)
            except Exception:
                # Column may already exist if partial migration ran
                pass
        cur.execute(
            "INSERT OR REPLACE INTO schema_version (version, applied_at) VALUES (?, datetime('now'))",
            (2,),
        )
        conn.commit()
