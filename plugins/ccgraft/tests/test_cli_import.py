"""Copyright (c) 2026 Achyuth Jayadevan <achyuth@jayadevan.in>
Licensed under the MIT License. See LICENSE file in the project root.

Tests for the import CLI entry point.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from ccgraft.cli.import_ import main
from ccgraft.errors import ManifestError
from ccgraft.manifest import Manifest, SessionData, OriginalContext


@pytest.fixture
def cli_export_dir(tmp_path: Path, sample_messages: list[dict]) -> Path:
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
def mock_import_storage(tmp_path: Path):
    storage = tmp_path / "import-storage"
    storage.mkdir()
    with patch("ccgraft.snapshot.get_storage_dir", return_value=storage):
        yield storage


def test_main_missing_export_path():
    with pytest.raises(SystemExit) as exc_info:
        main([])
    assert exc_info.value.code == 2


def test_main_nonexistent_path(tmp_path: Path):
    code = main([str(tmp_path / "no-such-dir")])
    assert code == 1


def test_main_successful_import(
    cli_export_dir: Path, tmp_path: Path, mock_import_storage: Path
):
    target = tmp_path / "project"
    target.mkdir()

    with patch("ccgraft.importer.get_project_session_dir") as mock_dir:
        mock_dir.return_value = tmp_path / "sessions"
        code = main([str(cli_export_dir), "--target-project", str(target)])

    assert code == 0


def test_main_import_with_skip_flags(
    cli_export_dir: Path, tmp_path: Path, mock_import_storage: Path
):
    target = tmp_path / "project"
    target.mkdir()

    with patch("ccgraft.importer.get_project_session_dir") as mock_dir:
        mock_dir.return_value = tmp_path / "sessions2"
        code = main([
            str(cli_export_dir),
            "--target-project", str(target),
            "--skip-config",
            "--skip-snapshot",
        ])

    assert code == 0


def test_main_manifest_error(tmp_path: Path):
    empty = tmp_path / "empty"
    empty.mkdir()
    code = main([str(empty)])
    assert code == 1


def test_main_verbose_import(
    cli_export_dir: Path, tmp_path: Path, mock_import_storage: Path
):
    target = tmp_path / "project"
    target.mkdir()

    with patch("ccgraft.importer.get_project_session_dir") as mock_dir:
        mock_dir.return_value = tmp_path / "sessions3"
        code = main([str(cli_export_dir), "--target-project", str(target), "-v"])

    assert code == 0
