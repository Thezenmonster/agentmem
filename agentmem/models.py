"""Data models for agentmem."""

from __future__ import annotations

from dataclasses import dataclass, field

MEMORY_TYPES = ("setting", "bug", "decision", "procedure", "context", "feedback")


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
    created_at: str = ""
    updated_at: str = ""
    accessed_at: str = ""
    access_count: int = 0
    rank: float | None = None

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v or k in ("access_count", "confidence")}

    def format(self) -> str:
        header = f"[{self.type}] {self.title}"
        parts = [header, self.content]
        if self.tags:
            parts.append(f"tags: {', '.join(self.tags)}")
        return "\n".join(parts)
