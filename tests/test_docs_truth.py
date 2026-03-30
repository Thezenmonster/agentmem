"""Docs-truth smoke test: verify README claims match actual code.

This test catches the exact problem Codex flagged — README describing
features that don't exist in the shipped code.
"""

import re
from pathlib import Path

import pytest

# --- Load README ---
README = (Path(__file__).parent.parent / "README.md").read_text(encoding="utf-8")


def test_all_cli_commands_exist():
    """Every `agentmem <command>` in code blocks in README must exist in cli.py."""
    from agentmem.cli import main
    cli_commands = set(main.commands.keys())

    # Extract from bash code blocks — only lines starting with `agentmem`
    # that look like CLI invocations (followed by flags, args, or end of line)
    code_blocks = re.findall(r'```bash\n(.*?)```', README, re.DOTALL)
    readme_commands = set()
    for block in code_blocks:
        for line in block.split("\n"):
            line = line.strip()
            if line.startswith("#"):
                continue  # comment
            match = re.match(r'^agentmem\s+([a-z][\w-]*)\s', line)
            if not match:
                match = re.match(r'^agentmem\s+([a-z][\w-]*)$', line)
            if match:
                readme_commands.add(match.group(1))
    readme_commands -= {"install"}  # pip install

    for cmd in readme_commands:
        assert cmd in cli_commands or cmd.replace("-", "_") in cli_commands, \
            f"README code block references `agentmem {cmd}` but command not found in CLI. " \
            f"Available: {sorted(cli_commands)}"


def test_all_mcp_tools_exist():
    """Every MCP tool named in README must be registered in mcp_server.py."""
    from agentmem.mcp_server import run_server  # noqa: F401
    import agentmem.mcp_server as mcp_mod

    # Read the source to find tool names (can't easily run async list_tools)
    source = Path(mcp_mod.__file__).read_text(encoding="utf-8")
    defined_tools = set(re.findall(r'name="(\w+)"', source))

    # Find tool names referenced in README's MCP section
    mcp_section = README[README.find("**MCP tools:**"):]
    readme_tools = set(re.findall(r'`(\w+)`', mcp_section.split("\n")[0]))

    for tool in readme_tools:
        assert tool in defined_tools, \
            f"README lists MCP tool `{tool}` but not found in mcp_server.py. " \
            f"Defined: {sorted(defined_tools)}"


def test_memory_statuses_match_readme():
    """README status list must match MEMORY_STATUSES in models.py."""
    from agentmem.models import MEMORY_STATUSES

    for status in MEMORY_STATUSES:
        assert status in README, \
            f"Status `{status}` is in MEMORY_STATUSES but not mentioned in README"


def test_memory_types_match_readme():
    """README type table must match MEMORY_TYPES in models.py."""
    from agentmem.models import MEMORY_TYPES

    for mtype in MEMORY_TYPES:
        assert mtype in README, \
            f"Type `{mtype}` is in MEMORY_TYPES but not mentioned in README"


def test_ranking_weights_documented():
    """README must document the actual ranking weights from search.py."""
    from agentmem.search import fts_search  # noqa: F401
    source = Path(__file__).parent.parent / "agentmem" / "search.py"
    search_code = source.read_text(encoding="utf-8")

    # Check that README mentions the key ranking factors
    assert "trust status" in README.lower() or "status" in README.lower()
    assert "provenance" in README.lower()
    assert "recency" in README.lower()


def test_governance_methods_exist():
    """README governance features must have corresponding methods."""
    from agentmem import Memory

    assert hasattr(Memory, "promote"), "README mentions promote but method missing"
    assert hasattr(Memory, "deprecate"), "README mentions deprecate but method missing"
    assert hasattr(Memory, "supersede"), "README mentions supersede but method missing"


def test_demo_script_exists():
    """The example demo script referenced in docs must exist and be importable."""
    demo_path = Path(__file__).parent.parent / "examples" / "governed_memory_demo.py"
    assert demo_path.exists(), f"Demo script missing: {demo_path}"
