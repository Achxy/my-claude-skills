"""Copyright (c) 2026 Achyuth Jayadevan <achyuth@jayadevan.in>
Licensed under the MIT License. See LICENSE file in the project root.

Extended tests for importer sub-functions.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from unittest.mock import patch

import pytest

from ccgraft.importer import import_session
from ccgraft.manifest import Manifest, SessionData, OriginalContext


@pytest.fixture
def mock_import_storage(tmp_path: Path):
    storage = tmp_path / "import-storage"
    storage.mkdir()
    with patch("ccgraft.snapshot.get_storage_dir", return_value=storage):
        yield storage


def _make_export(
    tmp_path: Path,
    sample_messages: list[dict],
    *,
    include_file_history: bool = False,
    include_todos: bool = False,
    include_plan: bool = False,
    include_config: bool = False,
) -> Path:
    export = tmp_path / "export"
    export.mkdir()

    session_dir = export / "session"
    session_dir.mkdir()
    with open(session_dir / "main.jsonl", "w", encoding="utf-8") as fh:
        for msg in sample_messages:
            fh.write(json.dumps(msg) + "\n")

    file_history_paths = []
    if include_file_history:
        fh_dir = session_dir / "file-history"
        fh_dir.mkdir()
        for name in ("snapshot1.txt", "snapshot2.txt"):
            f = fh_dir / name
            f.write_text(f"content of {name}")
            file_history_paths.append(f"session/file-history/{name}")

    todos_path = ""
    if include_todos:
        todos = session_dir / "todos.json"
        todos.write_text(json.dumps([{"task": "do stuff"}]))
        todos_path = "session/todos.json"

    plan_path = ""
    if include_plan:
        plan = session_dir / "plan.md"
        plan.write_text("# Plan\n- Step 1")
        plan_path = "session/plan.md"

    config_snapshot = {}
    if include_config:
        config_dir = export / "config"
        cmd_dir = config_dir / "commands"
        cmd_dir.mkdir(parents=True)
        (cmd_dir / "test.md").write_text("# Test command")
        config_snapshot = {"commands": ["config/commands/test.md"]}

    manifest = Manifest(
        session_id=sample_messages[0]["sessionId"],
        session_slug="test-slug",
        export_name="test-import",
        session_data=SessionData(
            main_session="session/main.jsonl",
            file_history=file_history_paths,
            todos=todos_path,
            plan_file=plan_path,
        ),
        original_context=OriginalContext(user="tester"),
        config_snapshot=config_snapshot,
    )
    manifest.write(export)
    return export


def test_import_with_file_history(
    tmp_path: Path, sample_messages: list[dict], mock_import_storage: Path
):
    export = _make_export(tmp_path, sample_messages, include_file_history=True)
    target = tmp_path / "project"
    target.mkdir()

    mock_home = tmp_path / "home"
    mock_claude = mock_home / ".claude"

    with patch("ccgraft.importer.get_project_session_dir") as mock_dir, \
         patch("ccgraft.importer.Path") as MockPath:
        mock_dir.return_value = tmp_path / "sessions"
        MockPath.home.return_value = mock_home
        MockPath.cwd.return_value = target
        MockPath.side_effect = Path

        result = import_session(export_path=export, target_project=target)

    assert result.file_history_count == 2


def test_import_with_todos(
    tmp_path: Path, sample_messages: list[dict], mock_import_storage: Path
):
    export = _make_export(tmp_path, sample_messages, include_todos=True)
    target = tmp_path / "project"
    target.mkdir()

    with patch("ccgraft.importer.get_project_session_dir") as mock_dir:
        mock_dir.return_value = tmp_path / "sessions"
        result = import_session(export_path=export, target_project=target)

    assert result.todos_imported is True


def test_import_with_plan(
    tmp_path: Path, sample_messages: list[dict], mock_import_storage: Path
):
    export = _make_export(tmp_path, sample_messages, include_plan=True)
    target = tmp_path / "project"
    target.mkdir()

    with patch("ccgraft.importer.get_project_session_dir") as mock_dir:
        mock_dir.return_value = tmp_path / "sessions"
        result = import_session(export_path=export, target_project=target)

    assert result.plan_imported is True


def test_import_with_config(
    tmp_path: Path, sample_messages: list[dict], mock_import_storage: Path
):
    export = _make_export(tmp_path, sample_messages, include_config=True)
    target = tmp_path / "project"
    target.mkdir()

    with patch("ccgraft.importer.get_project_session_dir") as mock_dir:
        mock_dir.return_value = tmp_path / "sessions"
        result = import_session(export_path=export, target_project=target)

    assert result.config_imported is True
    assert (target / ".claude" / "commands" / "test.md").exists()


def test_import_config_does_not_overwrite_existing(
    tmp_path: Path, sample_messages: list[dict], mock_import_storage: Path
):
    export = _make_export(tmp_path, sample_messages, include_config=True)
    target = tmp_path / "project"
    target.mkdir()
    cmd_dir = target / ".claude" / "commands"
    cmd_dir.mkdir(parents=True)
    (cmd_dir / "test.md").write_text("# Existing command - should not be overwritten")

    with patch("ccgraft.importer.get_project_session_dir") as mock_dir:
        mock_dir.return_value = tmp_path / "sessions"
        result = import_session(export_path=export, target_project=target)

    assert (cmd_dir / "test.md").read_text() == "# Existing command - should not be overwritten"


def test_import_missing_main_session(
    tmp_path: Path, mock_import_storage: Path
):
    export = tmp_path / "bad-export"
    export.mkdir()

    manifest = Manifest(
        session_id="sid",
        export_name="bad",
        session_data=SessionData(main_session="session/main.jsonl"),
    )
    manifest.write(export)

    with patch("ccgraft.importer.get_project_session_dir") as mock_dir:
        mock_dir.return_value = tmp_path / "sessions"
        with pytest.raises(FileNotFoundError, match="Main session file not found"):
            import_session(export_path=export)
