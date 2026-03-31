"""Data models for agentmem."""

from __future__ import annotations

from dataclasses import dataclass, field

MEMORY_TYPES = ("setting", "bug", "decision", "procedure", "context", "feedback", "session")

# Truth governance statuses -- lifecycle of a memory
MEMORY_STATUSES = (
    "hypothesis",   # New observation, not yet validated. Enter as this when uncertain.
    "active",       # Default. Currently believed to be true and in use.
    "validated",    # Explicitly confirmed by evidence or user. Highest trust.
    "deprecated",   # Was true, no longer applies. Kept for history. Excluded from recall.
    "superseded",   # Replaced by a newer memory. Points to replacement via superseded_by.
)

# Trust ranking for recall: higher = preferred in retrieval
STATUS_TRUST = {
    "validated": 1.0,
    "active": 0.8,
    "hypothesis": 0.5,
    "deprecated": 0.1,
    "superseded": 0.0,
}


@dataclass
class MemoryRecord:
    id: str
    type: str
    title: str
    content: str
    tags: list[str] = field(default_factory=list)
    source: str = ""
    project: str = ""
    confidence: float = 1.0
    supersedes: str = ""
    status: str = "active"
    source_path: str = ""
    source_section: str = ""
    source_hash: str = ""
    validated_at: str = ""
    deprecated_at: str = ""
    superseded_by: str = ""
    created_at: str = ""
    updated_at: str = ""
    accessed_at: str = ""
    access_count: int = 0
    rank: float | None = None

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v or k in ("access_count", "confidence")}

    def format(self) -> str:
        status_tag = f" ({self.status})" if self.status not in ("active",) else ""
        header = f"[{self.type}] {self.title}{status_tag}"
        parts = [header, self.content]
        if self.tags:
            parts.append(f"tags: {', '.join(self.tags)}")
        return "\n".join(parts)

    @property
    def trust_score(self) -> float:
        """Trust weight based on governance status."""
        return STATUS_TRUST.get(self.status, 0.5)
