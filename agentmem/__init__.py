"""agentmem — Production-ready agent memory. SQLite + FTS5. No infrastructure."""

from .core import Memory
from .importer import import_markdown
from .models import MEMORY_TYPES, MemoryRecord

__version__ = "0.1.0"
__all__ = ["Memory", "MemoryRecord", "MEMORY_TYPES", "import_markdown"]
