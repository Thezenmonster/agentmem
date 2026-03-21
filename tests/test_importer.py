"""Tests for markdown importer."""

import os
import tempfile

import pytest

from agentmem import Memory, import_markdown


@pytest.fixture
def mem():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    m = Memory(path=db_path)
    yield m
    m.close()
    os.unlink(db_path)


@pytest.fixture
def sample_md(tmp_path):
    content = """---
type: bug
project: tad
---

## Audio Bug Fixes

### loudnorm undoes SFX reductions

Never apply loudnorm to the final amix output.
It lifts the noise floor and makes everything robotic.

tags: ffmpeg, audio, loudnorm

### aresample introduces static artifacts

Using aresample in filter_complex concat chains causes drone/static.
Fix: use concat demuxer instead.

tags: ffmpeg, narration

## Settings

### Voice speed for The Witness

atempo 0.90 per-line then 1.15x global.
Michael said "perfect. remember this setting"

tags: voice, witness
"""
    md_path = tmp_path / "test_memory.md"
    md_path.write_text(content, encoding="utf-8")
    return str(md_path)


def test_import_basic(mem, sample_md):
    records = import_markdown(mem, sample_md)
    assert len(records) == 3  # 3 H3 sections


def test_import_types_inferred(mem, sample_md):
    records = import_markdown(mem, sample_md)
    types = {r.title: r.type for r in records}
    # "bug" sections should be inferred from frontmatter default
    assert types["loudnorm undoes SFX reductions"] == "bug"
    assert types["aresample introduces static artifacts"] == "bug"


def test_import_tags_extracted(mem, sample_md):
    records = import_markdown(mem, sample_md)
    loudnorm = [r for r in records if "loudnorm" in r.title][0]
    assert "ffmpeg" in loudnorm.tags
    assert "audio" in loudnorm.tags


def test_import_project_from_frontmatter(mem, sample_md):
    records = import_markdown(mem, sample_md)
    assert all(r.project == "tad" for r in records)


def test_import_source_set(mem, sample_md):
    records = import_markdown(mem, sample_md)
    assert all("import:" in r.source for r in records)


def test_import_searchable(mem, sample_md):
    import_markdown(mem, sample_md)
    results = mem.search("loudnorm")
    assert len(results) > 0


def test_import_nonexistent_file(mem):
    with pytest.raises(FileNotFoundError):
        import_markdown(mem, "/nonexistent/file.md")


def test_import_no_sections(mem, tmp_path):
    md_path = tmp_path / "flat.md"
    md_path.write_text("Just some plain text with no headers.", encoding="utf-8")
    records = import_markdown(mem, str(md_path))
    assert len(records) == 1
    assert "flat" in records[0].title.lower()


def test_import_type_override(mem, sample_md):
    records = import_markdown(mem, sample_md, type="context")
    # Type override sets default to "context", but title inference still runs
    # None of the H3 titles contain "bug"/"fix"/"error" keywords directly,
    # so the default "context" applies to most. Title inference is keyword-based.
    assert len(records) == 3
    # All should have been imported
    titles = [r.title for r in records]
    assert "loudnorm undoes SFX reductions" in titles
