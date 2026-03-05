"""Copyright (c) 2026 Achyuth Jayadevan <achyuth@jayadevan.in>
Licensed under the MIT License. See LICENSE file in the project root.

Tests for session import orchestration.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from ccgraft.importer import import_session
from ccgraft.manifest import Manifest, SessionData, OriginalContext


@pytest.fixture
def export_dir(tmp_path: Path, sample_messages: list[dict]) -> Path:
    """Create a minimal export directory with manifest and session file."""
    export = tmp_path / "export"
    export.mkdir()

    session_dir = export / "session"
    session_dir.mkdir()
    session_file = session_dir / "main.jsonl"
    with open(session_file, "w", encoding="utf-8") as fh:
        for msg in sample_messages:
            fh.write(json.dumps(msg) + "\n")

    manifest = Manifest(
        session_id=sample_messages[0]["sessionId"],
        export_name="test-import",
        session_data=SessionData(main_session="session/main.jsonl"),
        original_context=OriginalContext(user="tester"),
    )
    manifest.write(export)

    return export


@pytest.fixture
def mock_storage(tmp_path: Path):
    """Redirect snapshot and import log storage to tmp."""
    storage = tmp_path / "import-storage"
    storage.mkdir()
    with patch("ccgraft.snapshot.get_storage_dir", return_value=storage):
        yield storage


def test_import_session_basic(
    export_dir: Path, tmp_path: Path, mock_storage: Path
):
    target_project = tmp_path / "target-project"
    target_project.mkdir()

    with patch("ccgraft.importer.get_project_session_dir") as mock_dir:
        session_target = tmp_path / "sessions"
        mock_dir.return_value = session_target

        result = import_session(
            export_path=export_dir,
            target_project=target_project,
        )

    assert result.messages_imported == 2
    assert result.session_path.exists()
    assert result.session_id != ""


def test_import_session_skip_snapshot(
    export_dir: Path, tmp_path: Path, mock_storage: Path
):
    target_project = tmp_path / "target"
    target_project.mkdir()

    with patch("ccgraft.importer.get_project_session_dir") as mock_dir:
        session_target = tmp_path / "sessions2"
        mock_dir.return_value = session_target

        result = import_session(
            export_path=export_dir,
            target_project=target_project,
            skip_snapshot=True,
        )

    assert result.messages_imported == 2
    snapshot_dir = mock_storage / "pre-import-snapshot"
    assert not snapshot_dir.exists()


def test_import_session_invalid_manifest(tmp_path: Path):
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()

    from ccgraft.errors import ManifestError

    with pytest.raises(ManifestError):
        import_session(export_path=empty_dir)
