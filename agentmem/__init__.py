"""agentmem -- Trusted memory for long-lived coding agents. SQLite + FTS5. No infrastructure."""

from .core import Memory
from .governance import detect_conflicts, detect_stale, health_check, hash_content, hash_file_section
from .importer import import_markdown
from .models import MEMORY_TYPES, MEMORY_STATUSES, MemoryRecord

__version__ = "0.2.0"
__all__ = [
    "Memory", "MemoryRecord", "MEMORY_TYPES", "MEMORY_STATUSES",
    "import_markdown",
    "detect_conflicts", "detect_stale", "health_check",
    "hash_content", "hash_file_section",
]
