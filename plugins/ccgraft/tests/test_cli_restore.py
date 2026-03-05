"""Copyright (c) 2026 Achyuth Jayadevan <achyuth@jayadevan.in>
Licensed under the MIT License. See LICENSE file in the project root.

Tests for the restore CLI entry point.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from ccgraft.cli.restore import main
from ccgraft.errors import RestoreError
from ccgraft.snapshot import SnapshotInfo, RestoreResult, create_snapshot


@pytest.fixture
def mock_restore_storage(tmp_path: Path):
    storage = tmp_path / "storage"
    storage.mkdir()
    with patch("ccgraft.snapshot.get_storage_dir", return_value=storage):
        yield storage


def test_main_no_snapshot():
    with patch("ccgraft.cli.restore.get_snapshot_info", side_effect=FileNotFoundError("No pre-import snapshot")):
        code = main(["--info"])
    assert code == 1


def test_main_info_mode(mock_restore_storage: Path, tmp_path: Path):
    target = tmp_path / "target"
    target.mkdir()
    (target / "file.txt").write_text("data")
    create_snapshot(target)

    code = main(["--info"])
    assert code == 0


def test_main_restore_with_force(mock_restore_storage: Path, tmp_path: Path):
    target = tmp_path / "target"
    target.mkdir()
    (target / "original.txt").write_text("original")
    create_snapshot(target)

    (target / "original.txt").write_text("modified")

    code = main(["--force"])
    assert code == 0
    assert (target / "original.txt").read_text() == "original"


def test_main_restore_aborted(mock_restore_storage: Path, tmp_path: Path):
    target = tmp_path / "target"
    target.mkdir()
    create_snapshot(target)

    with patch("builtins.input", return_value="n"):
        code = main([])
    assert code == 1


def test_main_restore_confirmed(mock_restore_storage: Path, tmp_path: Path):
    target = tmp_path / "target"
    target.mkdir()
    (target / "file.txt").write_text("data")
    create_snapshot(target)

    with patch("builtins.input", return_value="y"):
        code = main([])
    assert code == 0


def test_main_restore_error(mock_restore_storage: Path, tmp_path: Path):
    target = tmp_path / "target"
    target.mkdir()
    create_snapshot(target)

    with patch("ccgraft.cli.restore.restore_snapshot", side_effect=RestoreError("boom")):
        code = main(["--force"])
    assert code == 1


def test_main_info_with_verbose(mock_restore_storage: Path, tmp_path: Path):
    target = tmp_path / "target"
    target.mkdir()
    (target / "file.txt").write_text("data")
    create_snapshot(target)

    code = main(["--info", "-v"])
    assert code == 0
