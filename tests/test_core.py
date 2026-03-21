"""Tests for core Memory operations."""

import os
import tempfile

import pytest

from agentmem import Memory, MemoryRecord


@pytest.fixture
def mem():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    m = Memory(path=db_path)
    yield m
    m.close()
    os.unlink(db_path)


def test_add_and_get(mem):
    record = mem.add(type="bug", title="Test bug", content="Something broke")
    assert record.id
    assert record.type == "bug"
    assert record.title == "Test bug"

    fetched = mem.get(record.id)
    assert fetched is not None
    assert fetched.title == "Test bug"
    assert fetched.access_count == 0  # get bumps it, but row was read before bump


def test_add_invalid_type(mem):
    with pytest.raises(ValueError, match="Invalid type"):
        mem.add(type="invalid", title="Bad", content="Nope")


def test_add_with_tags(mem):
    record = mem.add(type="setting", title="Voice speed", content="0.90",
                     tags=["voice", "audio"])
    assert record.tags == ["voice", "audio"]


def test_update(mem):
    record = mem.add(type="setting", title="Old title", content="Old content")
    updated = mem.update(record.id, title="New title", content="New content")
    assert updated.title == "New title"
    assert updated.content == "New content"


def test_update_nonexistent(mem):
    result = mem.update("nonexistent-id", title="Nope")
    assert result is None


def test_delete(mem):
    record = mem.add(type="context", title="Delete me", content="Gone")
    assert mem.delete(record.id) is True
    assert mem.get(record.id) is None


def test_delete_nonexistent(mem):
    assert mem.delete("nonexistent-id") is False


def test_list(mem):
    mem.add(type="bug", title="Bug 1", content="A")
    mem.add(type="bug", title="Bug 2", content="B")
    mem.add(type="setting", title="Setting 1", content="C")

    all_records = mem.list()
    assert len(all_records) == 3

    bugs = mem.list(type="bug")
    assert len(bugs) == 2

    settings = mem.list(type="setting")
    assert len(settings) == 1


def test_list_with_limit(mem):
    for i in range(10):
        mem.add(type="context", title=f"Item {i}", content=f"Content {i}")

    limited = mem.list(limit=5)
    assert len(limited) == 5


def test_stats(mem):
    mem.add(type="bug", title="Bug", content="X")
    mem.add(type="setting", title="Set", content="Y")
    s = mem.stats()
    assert s["total"] == 2
    assert s["by_type"]["bug"] == 1
    assert s["by_type"]["setting"] == 1
    assert s["db_size_kb"] > 0


def test_context_manager():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        with Memory(path=db_path) as mem:
            mem.add(type="context", title="Test", content="Works")
            assert mem.stats()["total"] == 1
    finally:
        os.unlink(db_path)


def test_project_scoping():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        mem1 = Memory(path=db_path, project="alpha")
        mem2 = Memory(path=db_path, project="beta")

        mem1.add(type="context", title="Alpha item", content="A")
        mem2.add(type="context", title="Beta item", content="B")

        assert len(mem1.list()) == 1
        assert len(mem2.list()) == 1
        assert mem1.list()[0].title == "Alpha item"
        assert mem2.list()[0].title == "Beta item"

        mem1.close()
        mem2.close()
    finally:
        os.unlink(db_path)
