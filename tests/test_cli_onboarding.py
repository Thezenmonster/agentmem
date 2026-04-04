"""Tests for init and doctor CLI commands — core activation path."""

import os
import tempfile

import pytest
from click.testing import CliRunner

from agentmem.cli import main


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def fresh_db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    # Delete the file so init creates it fresh
    os.unlink(db_path)
    yield db_path
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def existing_db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    # Create a DB with some content
    from agentmem import Memory
    mem = Memory(path=db_path, project="test")
    mem.add(type="decision", title="Existing rule", content="Already here")
    mem.close()
    yield db_path
    if os.path.exists(db_path):
        os.unlink(db_path)


# ── init tests ──────────────────────────────────────────────

class TestInit:

    def test_init_creates_db(self, runner, fresh_db):
        result = runner.invoke(main, ["--db", fresh_db, "init", "--project", "myapp"])
        assert result.exit_code == 0
        assert os.path.exists(fresh_db)
        assert "Created database" in result.output

    def test_init_adds_starter_memory(self, runner, fresh_db):
        result = runner.invoke(main, ["--db", fresh_db, "init", "--project", "myapp"])
        assert result.exit_code == 0
        assert "Added starter memory" in result.output

        # Verify the memory exists
        from agentmem import Memory
        mem = Memory(path=fresh_db, project="myapp")
        assert mem.stats()["total"] == 1
        records = mem.list()
        assert records[0].title == "Project: myapp"
        mem.close()

    def test_init_skips_starter_on_existing_db(self, runner, existing_db):
        result = runner.invoke(main, ["--db", existing_db, "--project", "test", "init"])
        assert result.exit_code == 0
        assert "Skipped starter memory" in result.output

    def test_init_runs_health_check(self, runner, fresh_db):
        result = runner.invoke(main, ["--db", fresh_db, "init", "--project", "test"])
        assert result.exit_code == 0
        assert "Health:" in result.output

    def test_init_shows_next_steps(self, runner, fresh_db):
        result = runner.invoke(main, ["--db", fresh_db, "init", "--project", "test"])
        assert result.exit_code == 0
        assert "Try the differentiators:" in result.output
        assert "agentmem add" in result.output
        assert "agentmem health" in result.output
        assert "save-session" in result.output
        assert "load-session" in result.output

    def test_init_claude_config(self, runner, fresh_db):
        result = runner.invoke(main, ["--db", fresh_db, "init", "--tool", "claude", "--project", "app"])
        assert result.exit_code == 0
        assert "mcpServers" in result.output
        assert '"type": "stdio"' in result.output
        assert "agentmem" in result.output
        assert ".claude/settings.json" in result.output

    def test_init_cursor_config(self, runner, fresh_db):
        result = runner.invoke(main, ["--db", fresh_db, "init", "--tool", "cursor", "--project", "app"])
        assert result.exit_code == 0
        assert "mcpServers" in result.output
        assert ".cursor/mcp.json" in result.output

    def test_init_codex_config(self, runner, fresh_db):
        result = runner.invoke(main, ["--db", fresh_db, "init", "--tool", "codex", "--project", "app"])
        assert result.exit_code == 0
        assert "[mcp_servers.agentmem]" in result.output
        assert "config.toml" in result.output

    def test_init_windsurf_config(self, runner, fresh_db):
        result = runner.invoke(main, ["--db", fresh_db, "init", "--tool", "windsurf", "--project", "app"])
        assert result.exit_code == 0
        assert ".windsurf/mcp.json" in result.output

    def test_init_no_tool_skips_config(self, runner, fresh_db):
        result = runner.invoke(main, ["--db", fresh_db, "init", "--project", "test"])
        assert result.exit_code == 0
        assert "Skipped MCP config" in result.output
        assert "--tool claude" in result.output

    def test_init_uses_cwd_as_default_project(self, runner, fresh_db):
        result = runner.invoke(main, ["--db", fresh_db, "init"])
        assert result.exit_code == 0
        # Should use the current directory name as project
        assert "Project:" in result.output


# ── doctor tests ──────────────────────────────────────────────

class TestDoctor:

    def test_doctor_healthy_db(self, runner, existing_db):
        result = runner.invoke(main, ["--db", existing_db, "--project", "test", "doctor"])
        assert result.exit_code == 0
        assert "[OK] Database:" in result.output
        assert "[OK] Schema version: 2" in result.output

    def test_doctor_missing_db(self, runner, fresh_db):
        result = runner.invoke(main, ["--db", fresh_db, "doctor"])
        assert result.exit_code == 0
        assert "[FAIL] Database not found" in result.output
        assert "agentmem init" in result.output

    def test_doctor_checks_mcp(self, runner, existing_db):
        result = runner.invoke(main, ["--db", existing_db, "doctor"])
        assert result.exit_code == 0
        # Should have either [OK] or [WARN] for MCP
        assert "MCP package" in result.output

    def test_doctor_checks_health(self, runner, existing_db):
        result = runner.invoke(main, ["--db", existing_db, "--project", "test", "doctor"])
        assert result.exit_code == 0
        assert "Health:" in result.output

    def test_doctor_warns_no_project(self, runner, existing_db):
        result = runner.invoke(main, ["--db", existing_db, "doctor"])
        assert result.exit_code == 0
        assert "No project scope" in result.output or "[OK] Project:" in result.output

    def test_doctor_warns_no_validated(self, runner, existing_db):
        result = runner.invoke(main, ["--db", existing_db, "--project", "test", "doctor"])
        assert result.exit_code == 0
        assert "No validated memories" in result.output or "Validated memories:" in result.output

    def test_doctor_reports_all_passed(self, runner, existing_db):
        result = runner.invoke(main, ["--db", existing_db, "--project", "test", "doctor"])
        assert result.exit_code == 0
        assert "All checks passed" in result.output or "Some checks failed" in result.output
