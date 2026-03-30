"""Tests for FTS5 search and recall."""

import os
import tempfile

import pytest

from agentmem import Memory


@pytest.fixture
def mem():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    m = Memory(path=db_path)
    # Seed some memories
    m.add(type="bug", title="loudnorm undoes SFX reductions",
          content="Never apply loudnorm to final amix output. It lifts noise floor.",
          tags=["ffmpeg", "audio"])
    m.add(type="setting", title="Witness voice speed",
          content="atempo 0.90 per-line then 1.15x global. Perfect setting per Michael.",
          tags=["voice", "speed"])
    m.add(type="bug", title="aresample introduces artifacts",
          content="Using aresample in filter_complex concat chains introduces drone/static.",
          tags=["ffmpeg", "audio", "narration"])
    m.add(type="decision", title="3rd person clinical is BANNED",
          content="Average 25 views. Every time, without exception. Use 1st person witness.",
          tags=["scripting", "pov"])
    m.add(type="procedure", title="Voice generation chain",
          content="raw TTS → atempo={speed} → 48kHz stereo. NO loudnorm. NO global atempo.",
          tags=["voice", "pipeline"])
    yield m
    m.close()
    os.unlink(db_path)


def test_basic_search(mem):
    results = mem.search("loudnorm")
    assert len(results) > 0
    assert any("loudnorm" in r.title.lower() for r in results)


def test_search_returns_ranked(mem):
    results = mem.search("audio")
    assert len(results) > 0
    assert all(r.rank is not None for r in results)


def test_search_with_type_filter(mem):
    results = mem.search("audio", type="bug")
    assert all(r.type == "bug" for r in results)


def test_search_with_tag_filter(mem):
    results = mem.search("audio", tags=["narration"])
    assert len(results) >= 1
    assert any("aresample" in r.title.lower() for r in results)


def test_search_no_results(mem):
    results = mem.search("xylophone quantum entanglement")
    assert len(results) == 0


def test_recall_returns_string(mem):
    context = mem.recall("voice settings and audio bugs")
    assert isinstance(context, str)
    assert len(context) > 0


def test_recall_respects_token_budget(mem):
    # With a very small budget, should get truncated results
    context = mem.recall("audio", max_tokens=50)
    assert len(context) > 0
    # Rough check: 50 tokens ≈ 200 chars
    assert len(context) < 1000


def test_recall_empty_query(mem):
    # FTS5 may return nothing for empty-like queries
    context = mem.recall("zzzznonexistent")
    assert context == "" or isinstance(context, str)


def test_search_does_not_bump_access_count(mem):
    """Search should NOT bump access_count — prevents self-reinforcing popularity bias.
    Only explicit get() or confirmed use should increment access."""
    results = mem.search("loudnorm")
    assert len(results) > 0
    record_id = results[0].id

    # Search again — access count should NOT increase from search alone
    mem.search("loudnorm")
    record = mem.get(record_id)
    # get() itself bumps by 1, but the two searches should add 0
    assert record.access_count <= 1


def test_recall_markdown_format(mem):
    context = mem.recall("voice speed", format="markdown")
    assert "###" in context  # markdown headers
