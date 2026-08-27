"""Tests for helpers/pipeline/file_helpers.py -- atomic writes, content hashing, directory management."""

import pytest
import yaml
from pathlib import Path

from helpers.pipeline.file_helpers import (
    atomic_write,
    atomic_write_yaml,
    content_hash,
    ensure_directory,
    has_content_changed,
    list_yaml_files,
    safe_read_yaml,
)


# ---------------------------------------------------------------------------
# atomic_write
# ---------------------------------------------------------------------------

class TestAtomicWrite:
    def test_creates_file(self, tmp_path):
        target = tmp_path / "out.txt"
        atomic_write(target, "hello")
        assert target.read_text() == "hello"

    def test_creates_parent_directories(self, tmp_path):
        target = tmp_path / "a" / "b" / "c" / "out.txt"
        atomic_write(target, "deep")
        assert target.read_text() == "deep"

    def test_overwrites_existing(self, tmp_path):
        target = tmp_path / "out.txt"
        target.write_text("old")
        atomic_write(target, "new")
        assert target.read_text() == "new"

    def test_accepts_string_path(self, tmp_path):
        target = str(tmp_path / "str_path.txt")
        atomic_write(target, "string path")
        assert Path(target).read_text() == "string path"

    def test_no_temp_file_left_on_success(self, tmp_path):
        target = tmp_path / "clean.txt"
        atomic_write(target, "clean")
        tmp_files = list(tmp_path.glob("*.tmp"))
        assert tmp_files == []

    def test_no_temp_file_left_on_error(self, tmp_path, monkeypatch):
        """If os.replace fails, temp file should be cleaned up."""
        import os
        original_replace = os.replace

        def bad_replace(src, dst):
            raise OSError("simulated replace failure")

        monkeypatch.setattr(os, "replace", bad_replace)
        target = tmp_path / "fail.txt"
        with pytest.raises(OSError, match="simulated"):
            atomic_write(target, "should fail")
        tmp_files = list(tmp_path.glob("*.tmp"))
        assert tmp_files == []


# ---------------------------------------------------------------------------
# atomic_write_yaml
# ---------------------------------------------------------------------------

class TestAtomicWriteYaml:
    def test_writes_valid_yaml(self, tmp_path):
        target = tmp_path / "data.yaml"
        data = {"name": "test", "items": [1, 2, 3]}
        atomic_write_yaml(target, data)
        loaded = yaml.safe_load(target.read_text())
        assert loaded == data

    def test_preserves_key_order(self, tmp_path):
        target = tmp_path / "ordered.yaml"
        data = {"z_last": 1, "a_first": 2, "m_middle": 3}
        atomic_write_yaml(target, data)
        lines = target.read_text().strip().split("\n")
        keys = [line.split(":")[0] for line in lines]
        assert keys == ["z_last", "a_first", "m_middle"]

    def test_handles_unicode(self, tmp_path):
        target = tmp_path / "unicode.yaml"
        data = {"emoji": "hello world", "japanese": "テスト"}
        atomic_write_yaml(target, data)
        loaded = yaml.safe_load(target.read_text())
        assert loaded["japanese"] == "テスト"


# ---------------------------------------------------------------------------
# content_hash
# ---------------------------------------------------------------------------

class TestContentHash:
    def test_deterministic(self):
        assert content_hash("hello") == content_hash("hello")

    def test_different_content_different_hash(self):
        assert content_hash("hello") != content_hash("world")

    def test_returns_16_hex_chars(self):
        h = content_hash("test")
        assert len(h) == 16
        assert all(c in "0123456789abcdef" for c in h)

    def test_empty_string(self):
        h = content_hash("")
        assert len(h) == 16


# ---------------------------------------------------------------------------
# has_content_changed
# ---------------------------------------------------------------------------

class TestHasContentChanged:
    def test_returns_true_for_nonexistent_file(self, tmp_path):
        assert has_content_changed(tmp_path / "nope.txt", "anything") is True

    def test_returns_false_for_same_content(self, tmp_path):
        target = tmp_path / "same.txt"
        target.write_text("hello")
        assert has_content_changed(target, "hello") is False

    def test_returns_true_for_different_content(self, tmp_path):
        target = tmp_path / "diff.txt"
        target.write_text("old")
        assert has_content_changed(target, "new") is True


# ---------------------------------------------------------------------------
# ensure_directory
# ---------------------------------------------------------------------------

class TestEnsureDirectory:
    def test_creates_directory(self, tmp_path):
        target = tmp_path / "new_dir"
        result = ensure_directory(target)
        assert target.is_dir()
        assert result == target

    def test_creates_nested(self, tmp_path):
        target = tmp_path / "a" / "b" / "c"
        ensure_directory(target)
        assert target.is_dir()

    def test_idempotent(self, tmp_path):
        target = tmp_path / "exists"
        target.mkdir()
        result = ensure_directory(target)
        assert result == target


# ---------------------------------------------------------------------------
# list_yaml_files
# ---------------------------------------------------------------------------

class TestListYamlFiles:
    def test_finds_yaml_and_yml(self, tmp_path):
        (tmp_path / "a.yaml").write_text("a: 1")
        (tmp_path / "b.yml").write_text("b: 2")
        (tmp_path / "c.txt").write_text("not yaml")
        result = list_yaml_files(tmp_path)
        names = [p.name for p in result]
        assert names == ["a.yaml", "b.yml"]

    def test_sorted_by_name(self, tmp_path):
        (tmp_path / "z.yaml").write_text("z: 1")
        (tmp_path / "a.yaml").write_text("a: 1")
        (tmp_path / "m.yaml").write_text("m: 1")
        result = list_yaml_files(tmp_path)
        names = [p.name for p in result]
        assert names == ["a.yaml", "m.yaml", "z.yaml"]

    def test_empty_for_nonexistent_dir(self, tmp_path):
        assert list_yaml_files(tmp_path / "nonexistent") == []

    def test_empty_for_no_yaml(self, tmp_path):
        (tmp_path / "readme.txt").write_text("hi")
        assert list_yaml_files(tmp_path) == []


# ---------------------------------------------------------------------------
# safe_read_yaml
# ---------------------------------------------------------------------------

class TestSafeReadYaml:
    def test_reads_valid_yaml(self, tmp_path):
        target = tmp_path / "valid.yaml"
        target.write_text("key: value\nlist:\n  - 1\n  - 2\n")
        result = safe_read_yaml(target)
        assert result == {"key": "value", "list": [1, 2]}

    def test_returns_none_for_nonexistent(self, tmp_path):
        assert safe_read_yaml(tmp_path / "nope.yaml") is None

    def test_returns_none_for_invalid_yaml(self, tmp_path):
        target = tmp_path / "bad.yaml"
        target.write_text("{{invalid yaml: [")
        assert safe_read_yaml(target) is None

    def test_returns_empty_dict_for_empty_file(self, tmp_path):
        target = tmp_path / "empty.yaml"
        target.write_text("")
        assert safe_read_yaml(target) == {}
