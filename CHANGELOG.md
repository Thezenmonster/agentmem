# Changelog

All notable changes to agentmem will be documented in this file.

## [0.2.0] - 2026-03-30

### Added
- **Truth governance engine** — memory lifecycle states: `hypothesis -> active -> validated -> deprecated -> superseded`
- **Provenance tracking** — `source_path`, `source_section`, `source_hash` fields on every memory
- **Conflict detection** — finds contradictions between active memories, separates duplicates from real contradictions, sentence-level negation matching
- **Staleness detection** — flags memories by age, missing source files, or hash drift (source content changed)
- **Health check** — scores memory system 0-100 based on conflicts, stale %, orphaned references, validated count
- **Trust-ranked recall** — validated memories rank above active, which rank above hypothesis; provenance-weighted (canonical > unprovenanced)
- **Lifecycle methods** — `promote()`, `deprecate()`, `supersede()` on Memory class
- **Session governance** — `save_session()` now properly supersedes previous sessions
- **MCP governance tools** — `promote_memory`, `deprecate_memory`, `supersede_memory`, `memory_health`, `memory_conflicts`
- **CLI governance commands** — `health`, `conflicts`, `stale`, `promote`, `deprecate`
- **28 governance tests** — lifecycle, conflicts, staleness, hashing, search trust ranking
- Schema v2 migration (backward-compatible from v1)

### Changed
- Search no longer bumps `access_count` on returned candidates (fixes self-reinforcing popularity bias)
- Deprecated and superseded memories excluded from search results entirely
- Recall ranking reweighted: FTS 25%, trust status 20%, provenance 20%, recency 15%, frequency 10%, confidence 10%
- README rewritten around "governed memory for long-lived coding agents"
- Package description updated

### Fixed
- Resurrected sections: if a canonical section is removed (deprecated) then restored, sync reactivates it
- Source priority: provenance-tracked canonical memories now rank above unprovenanced imports
- Session lifecycle: old sessions properly superseded, no more orphaned chains

## [0.1.0] - 2026-03-21

### Added
- Core Memory class with CRUD operations
- FTS5 full-text search with porter stemming
- Context-budgeted `recall()` with token limits
- Seven memory types: setting, bug, decision, procedure, context, feedback, session
- Project scoping (multiple agents, one DB)
- Session persistence (`save_session`, `load_session`)
- Markdown importer with frontmatter and type inference
- CLI with full CRUD, search, recall, import, stats
- MCP server with 8 tools
- SQLite + WAL mode, thread-safe
- 31 tests across core, search, and importer
- Published to PyPI as `quilmem`
