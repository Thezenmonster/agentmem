# Release Checklist

Run this before every release. Every item must pass.

## Code Truth

- [ ] `python -m pytest tests/ -v` — all tests pass
- [ ] Every CLI command named in README exists in `cli.py`
- [ ] Every MCP tool named in README exists in `mcp_server.py`
- [ ] Every Python method named in README exists in `core.py`
- [ ] README ranking weights match `search.py` actual weights
- [ ] README memory statuses match `models.py` MEMORY_STATUSES
- [ ] README feature claims match implemented behavior (no aspirational claims)

## Package

- [ ] Version bumped in `pyproject.toml` and `__init__.py`
- [ ] CHANGELOG.md updated with all changes
- [ ] `python -m build` succeeds
- [ ] Clean install test: `pip install dist/*.whl` in fresh venv, run demo

## Smoke Tests

- [ ] `agentmem add --type bug --title "test" "content"` works
- [ ] `agentmem search "test"` returns the added memory
- [ ] `agentmem health` runs without error
- [ ] `agentmem conflicts` runs without error
- [ ] `agentmem stale --days 1` runs without error
- [ ] `agentmem promote <id>` works
- [ ] `agentmem deprecate <id>` works
- [ ] `python examples/governed_memory_demo.py` runs clean

## MCP Smoke Test

- [ ] `agentmem serve` starts without error (Ctrl+C to exit)
- [ ] If MCP client available: `add_memory`, `search_memory`, `memory_health` work

## Publish

- [ ] `python -m twine upload dist/*` to PyPI
- [ ] `git tag v{VERSION}`
- [ ] `git push origin main --tags`
- [ ] GitHub release created with notes from CHANGELOG
- [ ] Verify `pip install quilmem=={VERSION}` pulls the new version
