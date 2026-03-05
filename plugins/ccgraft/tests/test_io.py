"""Copyright (c) 2026 Achyuth Jayadevan <achyuth@jayadevan.in>
Licensed under the MIT License. See LICENSE file in the project root.

Tests for safe I/O primitives.
"""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path

import pytest

from ccgraft._io import (
    atomic_write,
    atomic_write_text,
    atomic_write_json,
    watch_for_modification,
)


def test_atomic_write_creates_file(tmp_path: Path):
    target = tmp_path / "out.txt"
    with atomic_write(target) as fh:
        fh.write("hello")
    assert target.read_text() == "hello"


def test_atomic_write_no_partial_on_error(tmp_path: Path):
    target = tmp_path / "out.txt"
    with pytest.raises(ValueError):
        with atomic_write(target) as fh:
            fh.write("partial")
            raise ValueError("boom")
    assert not target.exists()


def test_atomic_write_overwrites_existing(tmp_path: Path):
    target = tmp_path / "out.txt"
    target.write_text("old")
    with atomic_write(target) as fh:
        fh.write("new")
    assert target.read_text() == "new"


def test_atomic_write_creates_parent_dirs(tmp_path: Path):
    target = tmp_path / "a" / "b" / "c.txt"
    atomic_write_text(target, "deep")
    assert target.read_text() == "deep"


def test_atomic_write_json(tmp_path: Path):
    target = tmp_path / "data.json"
    atomic_write_json(target, {"key": "value"})
    data = json.loads(target.read_text())
    assert data["key"] == "value"


def test_atomic_write_no_temp_file_left_on_success(tmp_path: Path):
    target = tmp_path / "clean.txt"
    atomic_write_text(target, "done")
    files = list(tmp_path.iterdir())
    assert files == [target]


def test_watch_for_modification_detects_write(tmp_path: Path):
    candidate = tmp_path / "session.jsonl"
    candidate.write_text("initial\n")

    def delayed_write():
        time.sleep(0.1)
        candidate.write_text("modified\n")

    writer = threading.Thread(target=delayed_write)
    writer.start()

    result = watch_for_modification(tmp_path, [candidate], timeout=2.0)
    writer.join()

    assert result == candidate


def test_watch_for_modification_returns_none_on_timeout(tmp_path: Path):
    candidate = tmp_path / "untouched.jsonl"
    candidate.write_text("static\n")
    # Let FSEvents settle after file creation so the observer
    # doesn't pick up the initial write as a modification event.
    time.sleep(0.3)

    result = watch_for_modification(tmp_path, [candidate], timeout=0.3)
    assert result is None


def test_watch_for_modification_ignores_non_candidates(tmp_path: Path):
    candidate = tmp_path / "target.jsonl"
    candidate.write_text("initial\n")
    other = tmp_path / "other.jsonl"
    other.write_text("initial\n")
    # Let FSEvents settle after file creation.
    time.sleep(0.3)

    def delayed_write():
        time.sleep(0.15)
        other.write_text("changed\n")

    writer = threading.Thread(target=delayed_write)
    writer.start()

    result = watch_for_modification(tmp_path, [candidate], timeout=0.5)
    writer.join()

    assert result is None
