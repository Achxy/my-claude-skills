"""Copyright (c) 2026 Achyuth Jayadevan <achyuth@jayadevan.in>
Licensed under the MIT License. See LICENSE file in the project root.

Extended tests for snapshot management, import logging, and last import info.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from ccgraft.snapshot import (
    create_snapshot,
    get_last_import_info,
    get_snapshot_info,
    log_import,
    restore_snapshot,
)
from ccgraft.errors import RestoreError


@pytest.fixture
def mock_storage(tmp_path: Path):
    storage = tmp_path / "storage"
    storage.mkdir()
    with patch("ccgraft.snapshot.get_storage_dir", return_value=storage):
        yield storage


def test_create_snapshot_overwrites_previous(tmp_path: Path, mock_storage: Path):
    target = tmp_path / "target"
    target.mkdir()
    (target / "v1.txt").write_text("version 1")

    create_snapshot(target)
    (target / "v1.txt").write_text("version 2")
    (target / "v2.txt").write_text("new file")

    snap = create_snapshot(target)
    backup = snap / "projects" / target.name
    assert (backup / "v1.txt").read_text() == "version 2"
    assert (backup / "v2.txt").exists()


def test_restore_snapshot_no_backup(tmp_path: Path, mock_storage: Path):
    target = tmp_path / "target"
    create_snapshot(target)

    result = restore_snapshot()
    assert result.restored is True
    assert result.had_backup is False
    assert not target.exists()


def test_restore_snapshot_cleans_up_snapshot_dir(tmp_path: Path, mock_storage: Path):
    target = tmp_path / "target"
    target.mkdir()
    (target / "file.txt").write_text("data")

    create_snapshot(target)
    restore_snapshot()

    snapshot_dir = mock_storage / "pre-import-snapshot"
    assert not snapshot_dir.exists()


def test_restore_snapshot_error_preserves_snapshot(tmp_path: Path, mock_storage: Path):
    target = tmp_path / "target"
    target.mkdir()
    (target / "file.txt").write_text("data")

    create_snapshot(target)

    with patch("ccgraft.snapshot.shutil.copytree", side_effect=OSError("disk full")):
        with pytest.raises(RestoreError, match="disk full"):
            restore_snapshot()

    snapshot_dir = mock_storage / "pre-import-snapshot"
    assert snapshot_dir.exists()


def test_log_import(mock_storage: Path, tmp_path: Path):
    manifest_data = {
        "session_id": "old-sid",
        "export_name": "test-export",
    }
    target_path = tmp_path / "sessions" / "new-sid.jsonl"
    target_path.parent.mkdir(parents=True)
    target_path.touch()

    log_path = log_import(
        manifest_data=manifest_data,
        new_session_id="new-sid",
        target_path=target_path,
        summary={"messages_imported": 42},
    )

    assert log_path.exists()
    log_data = json.loads(log_path.read_text())
    assert log_data["new_session_id"] == "new-sid"
    assert log_data["summary"]["messages_imported"] == 42


def test_log_import_updates_index(mock_storage: Path, tmp_path: Path):
    manifest_data = {"session_id": "sid1", "export_name": "export1"}
    target = tmp_path / "s1.jsonl"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.touch()

    log_import(manifest_data, "new1", target, {})

    index_path = mock_storage / "index.json"
    assert index_path.exists()
    index = json.loads(index_path.read_text())
    assert len(index["imports"]) == 1


def test_log_import_appends_to_index(mock_storage: Path, tmp_path: Path):
    import time
    manifest1 = {"session_id": "sid1", "export_name": "export1"}
    manifest2 = {"session_id": "sid2", "export_name": "export2"}
    t1 = tmp_path / "s1.jsonl"
    t2 = tmp_path / "s2.jsonl"
    t1.parent.mkdir(parents=True, exist_ok=True)
    t1.touch()
    t2.touch()

    log_import(manifest1, "new1", t1, {})
    time.sleep(1.1)
    log_import(manifest2, "new2", t2, {})

    index = json.loads((mock_storage / "index.json").read_text())
    assert len(index["imports"]) == 2


def test_get_last_import_info_none(mock_storage: Path):
    assert get_last_import_info() is None


def test_get_last_import_info_after_log(mock_storage: Path, tmp_path: Path):
    manifest_data = {"session_id": "sid", "export_name": "test"}
    target = tmp_path / "s.jsonl"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.touch()

    log_import(manifest_data, "new-sid", target, {})

    info = get_last_import_info()
    assert info is not None
    assert info["session_name"] == "test"


def test_get_snapshot_info_age_is_positive(tmp_path: Path, mock_storage: Path):
    target = tmp_path / "target"
    target.mkdir()
    create_snapshot(target)

    info = get_snapshot_info()
    assert info.age_hours is not None
    assert info.age_hours >= 0
