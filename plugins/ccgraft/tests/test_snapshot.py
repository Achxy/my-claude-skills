"""Copyright (c) 2026 Achyuth Jayadevan <achyuth@jayadevan.in>
Licensed under the MIT License. See LICENSE file in the project root.

Tests for snapshot creation and restoration.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from ccgraft.snapshot import (
    create_snapshot,
    get_snapshot_info,
    restore_snapshot,
)


@pytest.fixture
def mock_storage_dir(tmp_path: Path):
    """Redirect snapshot storage to a temp directory."""
    storage = tmp_path / "storage"
    storage.mkdir()
    with patch("ccgraft.snapshot.get_storage_dir", return_value=storage):
        yield storage


def test_create_snapshot_of_existing_dir(tmp_path: Path, mock_storage_dir: Path):
    target = tmp_path / "target"
    target.mkdir()
    (target / "data.txt").write_text("hello", encoding="utf-8")

    snapshot_dir = create_snapshot(target)
    assert snapshot_dir.exists()
    assert (snapshot_dir / "snapshot_info.json").exists()

    info = json.loads((snapshot_dir / "snapshot_info.json").read_text())
    assert info["backup_exists"] is True
    assert info["target_directory"] == str(target)


def test_create_snapshot_of_nonexistent_dir(tmp_path: Path, mock_storage_dir: Path):
    target = tmp_path / "nonexistent"
    snapshot_dir = create_snapshot(target)
    info = json.loads((snapshot_dir / "snapshot_info.json").read_text())
    assert info["backup_exists"] is False


def test_get_snapshot_info_no_snapshot(mock_storage_dir: Path):
    with pytest.raises(FileNotFoundError, match="No pre-import snapshot"):
        get_snapshot_info()


def test_get_snapshot_info_after_create(tmp_path: Path, mock_storage_dir: Path):
    target = tmp_path / "target"
    target.mkdir()
    (target / "file.txt").write_text("content", encoding="utf-8")

    create_snapshot(target)
    info = get_snapshot_info()
    assert info.backup_exists is True
    assert info.target_directory == str(target)
    assert info.age_hours is not None


def test_restore_snapshot(tmp_path: Path, mock_storage_dir: Path):
    target = tmp_path / "target"
    target.mkdir()
    (target / "original.txt").write_text("original", encoding="utf-8")

    create_snapshot(target)

    (target / "original.txt").write_text("modified", encoding="utf-8")
    (target / "new.txt").write_text("new", encoding="utf-8")

    result = restore_snapshot()
    assert result.restored is True

    assert (target / "original.txt").read_text() == "original"
    assert not (target / "new.txt").exists()
