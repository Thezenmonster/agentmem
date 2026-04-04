"""Truth governance -- conflict detection, staleness detection, health checks.

This module is the core differentiator. It answers:
- What memories contradict each other?
- What memories reference things that may no longer be true?
- What is the overall health of the memory system?
"""

from __future__ import annotations

import hashlib
import re
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path

from .models import MemoryRecord, MEMORY_STATUSES


def _safe_get(row, key, default=""):
    try:
        return row[key]
    except (IndexError, KeyError):
        return default


def _row_to_record(row: sqlite3.Row) -> MemoryRecord:
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
    )


@dataclass
class Conflict:
    """Two memories that may contradict each other."""
    memory_a: MemoryRecord
    memory_b: MemoryRecord
    reason: str
    severity: str = "warning"  # "warning" or "critical"
    kind: str = "contradiction"  # "contradiction" or "duplicate"


@dataclass
class StaleMemory:
    """A memory that may no longer be current."""
    memory: MemoryRecord
    reason: str
    days_since_update: int = 0


@dataclass
class HealthReport:
    """Overall health of the memory system."""
    total_memories: int = 0
    by_status: dict = field(default_factory=dict)
    conflicts: list[Conflict] = field(default_factory=list)
    stale: list[StaleMemory] = field(default_factory=list)
    orphaned_supersedes: list[MemoryRecord] = field(default_factory=list)
    never_accessed: int = 0
    health_score: float = 0.0  # 0-100

    def summary(self) -> str:
        lines = [
            f"Memory Health: {self.health_score:.0f}/100",
            f"Total: {self.total_memories}",
            f"By status: {self.by_status}",
            f"Conflicts: {len(self.conflicts)}",
            f"Stale: {len(self.stale)}",
            f"Orphaned supersedes: {len(self.orphaned_supersedes)}",
            f"Never accessed: {self.never_accessed}",
        ]
        return "\n".join(lines)


# -- Conflict Detection ------------------------------------------

# Negation patterns that signal potential contradictions
_NEGATION_PAIRS = [
    (r'\bNO\b', r'\balways\b'),
    (r'\bNEVER\b', r'\balways\b'),
    (r'\bdo not\b', r'\bmust\b'),
    (r'\bdon\'t\b', r'\bmust\b'),
    (r'\bbanned\b', r'\ballowed\b'),
    (r'\bdisabled\b', r'\benabled\b'),
    (r'\bremoved\b', r'\badded\b'),
    (r'\bdeprecated\b', r'\buse\b'),
]


def _extract_key_terms(text: str) -> set[str]:
    """Extract significant terms from memory content for overlap detection."""
    # Remove common words, keep domain-specific terms
    stop = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'could', 'should', 'may', 'might', 'shall', 'can', 'to', 'of',
            'in', 'for', 'on', 'with', 'at', 'by', 'from', 'as', 'into',
            'through', 'during', 'before', 'after', 'above', 'below',
            'between', 'and', 'but', 'or', 'nor', 'not', 'so', 'yet',
            'both', 'either', 'neither', 'each', 'every', 'all', 'any',
            'few', 'more', 'most', 'other', 'some', 'such', 'than', 'too',
            'very', 'just', 'also', 'now', 'then', 'here', 'there', 'when',
            'where', 'why', 'how', 'what', 'which', 'who', 'whom', 'this',
            'that', 'these', 'those', 'it', 'its', 'if', 'no', 'yes'}
    words = re.findall(r'\b[a-z_]{3,}\b', text.lower())
    return {w for w in words if w not in stop}


def detect_conflicts(
    conn: sqlite3.Connection,
    project: str = "",
) -> list[Conflict]:
    """Find memories that may contradict each other.

    Strategy:
    1. Find pairs with high term overlap (same topic)
    2. Check if one negates what the other asserts
    3. Flag when both are active/validated (critical) or one is deprecated (warning)
    """
    conditions = ["status NOT IN ('superseded', 'deprecated')"]
    params = []
    if project:
        conditions.append("project = ?")
        params.append(project)

    where = f"WHERE {' AND '.join(conditions)}"
    rows = conn.execute(
        f"SELECT * FROM memories {where} ORDER BY created_at DESC",
        params,
    ).fetchall()

    records = [_row_to_record(r) for r in rows]
    conflicts = []

    # Build term index for overlap detection
    term_cache = {}
    for r in records:
        term_cache[r.id] = _extract_key_terms(f"{r.title} {r.content}")

    # Compare all pairs
    # Phase 1: detect duplicates (same/near-identical content)
    # Phase 2: detect contradictions (only on non-duplicate pairs)
    seen_pairs = set()
    content_hashes = {}
    for r in records:
        content_hashes[r.id] = hash_content(f"{r.title} {r.content}")

    for i, a in enumerate(records):
        for b in records[i + 1:]:
            pair_key = tuple(sorted([a.id, b.id]))
            if pair_key in seen_pairs:
                continue

            terms_a = term_cache[a.id]
            terms_b = term_cache[b.id]

            if not terms_a or not terms_b:
                continue

            overlap = terms_a & terms_b
            union = terms_a | terms_b
            jaccard = len(overlap) / len(union) if union else 0

            # Skip pairs with insufficient overlap
            if jaccard < 0.25 or len(overlap) < 5:
                continue

            seen_pairs.add(pair_key)
            shared = ", ".join(sorted(list(overlap)[:5]))
            both_active = a.status in ('active', 'validated') and b.status in ('active', 'validated')

            # Phase 1: Duplicate detection
            # Same title or same content hash = duplicate, not contradiction
            if a.title == b.title or content_hashes[a.id] == content_hashes[b.id] or jaccard > 0.70:
                severity = "warning" if both_active else "info"
                conflicts.append(Conflict(
                    memory_a=a,
                    memory_b=b,
                    reason=f"Duplicate: {jaccard:.0%} overlap on ({shared}). "
                           f"Same content stored twice -- supersede the older one.",
                    severity=severity,
                    kind="duplicate",
                ))
                continue

            # Phase 2: Contradiction detection (sentence-level)
            # Split content into sentences, check for negation near shared terms
            text_a = f"{a.title}. {a.content}"
            text_b = f"{b.title}. {b.content}"

            # Find sentences containing shared topic terms
            def sentences_with_overlap(text, overlap_terms):
                sents = re.split(r'[.!?\n]+', text)
                return [s for s in sents if any(t in s.lower() for t in overlap_terms)]

            overlap_lower = {t.lower() for t in overlap}
            sents_a = sentences_with_overlap(text_a, overlap_lower)
            sents_b = sentences_with_overlap(text_b, overlap_lower)

            if not sents_a or not sents_b:
                continue

            # Check negation only in sentences about the shared topic
            found_contradiction = False
            for neg_pattern, assert_pattern in _NEGATION_PAIRS:
                a_neg_in_topic = any(re.search(neg_pattern, s, re.IGNORECASE) for s in sents_a)
                b_assert_in_topic = any(re.search(assert_pattern, s, re.IGNORECASE) for s in sents_b)
                b_neg_in_topic = any(re.search(neg_pattern, s, re.IGNORECASE) for s in sents_b)
                a_assert_in_topic = any(re.search(assert_pattern, s, re.IGNORECASE) for s in sents_a)

                if (a_neg_in_topic and b_assert_in_topic) or (b_neg_in_topic and a_assert_in_topic):
                    found_contradiction = True
                    break

            if not found_contradiction:
                continue

            severity = "critical" if both_active else "warning"
            conflicts.append(Conflict(
                memory_a=a,
                memory_b=b,
                reason=f"Contradiction on shared topic ({shared}). "
                       f"Jaccard: {jaccard:.0%}. Sentences about this topic assert vs negate.",
                severity=severity,
                kind="contradiction",
            ))

    return conflicts


# -- Staleness Detection ------------------------------------------

def detect_stale(
    conn: sqlite3.Connection,
    project: str = "",
    stale_days: int = 30,
) -> list[StaleMemory]:
    """Find memories that may be outdated.

    A memory is stale if ANY of:
    1. Status is active/hypothesis and updated_at > stale_days ago
    2. It references a source file that no longer exists
    3. Its source_hash doesn't match the current file content (source drifted)

    Checks 2 and 3 run on ALL active/hypothesis memories regardless of age --
    a source file that changed yesterday means the memory is stale NOW.
    """
    conditions = ["COALESCE(status, 'active') IN ('active', 'hypothesis')"]
    params = []
    if project:
        conditions.append("project = ?")
        params.append(project)

    where = f"WHERE {' AND '.join(conditions)}"
    rows = conn.execute(
        f"SELECT * FROM memories {where} ORDER BY updated_at ASC",
        params,
    ).fetchall()

    stale = []
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=stale_days)

    for row in rows:
        record = _row_to_record(row)
        updated = datetime.fromisoformat(record.updated_at)
        if updated.tzinfo is None:
            updated = updated.replace(tzinfo=timezone.utc)
        days = (now - updated).days

        reasons = []

        # Check age (only flags if old enough)
        is_old = updated < cutoff

        # Check source provenance (runs regardless of age)
        if record.source_path:
            path = Path(record.source_path)
            if not path.exists():
                reasons.append(f"Source file missing: {record.source_path}")
            elif record.source_hash:
                current_hash = hash_file_section(str(path), record.source_section)
                if current_hash != record.source_hash:
                    reasons.append(f"Source changed since import (hash mismatch)")

        if is_old:
            reasons.append(f"Not updated in {days} days")

        # Only report if there's at least one reason
        if reasons:
            stale.append(StaleMemory(
                memory=record,
                reason="; ".join(reasons),
                days_since_update=days,
            ))

    return stale


# -- Source Hashing ----------------------------------------------

def hash_content(content: str) -> str:
    """Hash content for change detection. Returns first 16 chars of SHA-256."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


def hash_file_section(filepath: str, section: str = "") -> str:
    """Hash a specific section of a file, or the whole file if no section specified.

    Section is identified by heading text (e.g., '### Step 4: Video Segments').
    """
    path = Path(filepath)
    if not path.exists():
        return ""

    content = path.read_text(encoding="utf-8")

    if section:
        # Find the section by heading
        lines = content.split("\n")
        section_lines = []
        in_section = False
        section_level = 0

        for line in lines:
            heading_match = re.match(r'^(#{1,6})\s+(.+)', line)
            if heading_match:
                level = len(heading_match.group(1))
                title = heading_match.group(2).strip()
                if title == section or section in title:
                    in_section = True
                    section_level = level
                    section_lines.append(line)
                    continue
                elif in_section and level <= section_level:
                    break  # Next section at same or higher level
            if in_section:
                section_lines.append(line)

        if section_lines:
            content = "\n".join(section_lines)
        # If section not found, hash the whole file

    return hash_content(content)


# -- Health Check ----------------------------------------------

def health_check(
    conn: sqlite3.Connection,
    project: str = "",
    stale_days: int = 30,
) -> HealthReport:
    """Run a full health check on the memory system."""

    # Total and by-status counts
    conditions = []
    params = []
    if project:
        conditions.append("project = ?")
        params.append(project)
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    total = conn.execute(f"SELECT COUNT(*) FROM memories {where}", params).fetchone()[0]

    by_status = {}
    for row in conn.execute(
        f"SELECT COALESCE(status, 'active') as status, COUNT(*) as c FROM memories {where} GROUP BY status",
        params,
    ):
        by_status[row["status"] or "active"] = row["c"]

    # Never accessed
    never_params = list(params)
    never_where = f"{where} {'AND' if where else 'WHERE'} access_count = 0"
    never = conn.execute(
        f"SELECT COUNT(*) FROM memories {never_where}",
        never_params,
    ).fetchone()[0]

    # Orphaned supersedes (points to ID that doesn't exist)
    orphan_where = "WHERE supersedes != '' AND supersedes NOT IN (SELECT id FROM memories)"
    orphan_params = []
    if project:
        orphan_where += " AND project = ?"
        orphan_params.append(project)
    rows = conn.execute(
        f"SELECT * FROM memories {orphan_where}",
        orphan_params,
    ).fetchall()
    orphaned = [_row_to_record(r) for r in rows]

    # Detect conflicts and stale
    conflicts = detect_conflicts(conn, project=project)
    stale = detect_stale(conn, project=project, stale_days=stale_days)

    # Calculate health score (0-100)
    score = 100.0
    if total > 0:
        # Deductions
        score -= min(30, len(conflicts) * 10)  # Conflicts: -10 each, max -30
        stale_pct = len(stale) / total * 100
        score -= min(20, stale_pct)  # Stale: up to -20 based on percentage
        score -= min(10, len(orphaned) * 5)  # Orphaned: -5 each, max -10
        deprecated_pct = by_status.get("deprecated", 0) / total * 100
        if deprecated_pct > 30:
            score -= 10  # Too much dead weight
        if by_status.get("validated", 0) == 0:
            score -= 10  # No validated memories = no explicit trust
    else:
        score = 0

    return HealthReport(
        total_memories=total,
        by_status=by_status,
        conflicts=conflicts,
        stale=stale,
        orphaned_supersedes=orphaned,
        never_accessed=never,
        health_score=max(0, min(100, score)),
    )
