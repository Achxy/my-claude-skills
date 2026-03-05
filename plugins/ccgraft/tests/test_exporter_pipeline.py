"""Copyright (c) 2026 Achyuth Jayadevan <achyuth@jayadevan.in>
Licensed under the MIT License. See LICENSE file in the project root.

Tests for the full export pipeline and artifact collection.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from ccgraft.config import ConfigSnapshot
from ccgraft.exporter import (
    ExportResult,
    SessionArtifacts,
    SessionMetadata,
    build_manifest,
    collect_artifacts,
    export_session,
    write_session_dir,
    _resolve_export_dir,
    render_markdown,
    render_xml,
)
from ccgraft.errors import ExportError
from ccgraft.session import SessionInfo


@pytest.fixture
def session_with_file(tmp_path: Path, sample_messages: list[dict]) -> tuple[SessionInfo, Path]:
    session_dir = tmp_path / "sessions"
    session_dir.mkdir()
    session_file = session_dir / "abc123.jsonl"
    with open(session_file, "w", encoding="utf-8") as fh:
        for msg in sample_messages:
            fh.write(json.dumps(msg) + "\n")
    info = SessionInfo(session_id="abc123", path=session_file, slug="test-slug")
    return info, tmp_path


def test_export_session_full_pipeline(session_with_file: tuple[SessionInfo, Path]):
    session, project = session_with_file
    output = project / "export-out"

    with patch("ccgraft.exporter.get_project_session_dir", return_value=session.path.parent):
        result = export_session(
            session=session,
            project_path=project,
            export_name="pipeline-test",
            output_dir=output,
        )

    assert isinstance(result, ExportResult)
    assert result.export_dir.exists()
    assert (result.export_dir / "session" / "main.jsonl").exists()
    assert (result.export_dir / ".ccgraft-manifest.json").exists()
    assert (result.export_dir / "RENDERED.md").exists()
    assert (result.export_dir / "conversation.xml").exists()


def test_export_session_md_only(session_with_file: tuple[SessionInfo, Path]):
    session, project = session_with_file
    output = project / "md-out"

    with patch("ccgraft.exporter.get_project_session_dir", return_value=session.path.parent):
        result = export_session(
            session=session, project_path=project,
            export_name="md-test", output_dir=output, output_format="md",
        )

    assert (result.export_dir / "RENDERED.md").exists()
    assert not (result.export_dir / "conversation.xml").exists()


def test_export_session_xml_only(session_with_file: tuple[SessionInfo, Path]):
    session, project = session_with_file
    output = project / "xml-out"

    with patch("ccgraft.exporter.get_project_session_dir", return_value=session.path.parent):
        result = export_session(
            session=session, project_path=project,
            export_name="xml-test", output_dir=output, output_format="xml",
        )

    assert not (result.export_dir / "RENDERED.md").exists()
    assert (result.export_dir / "conversation.xml").exists()


def test_export_session_empty_messages(tmp_path: Path):
    session_file = tmp_path / "empty.jsonl"
    session_file.write_text("")
    session = SessionInfo(session_id="empty", path=session_file)

    with pytest.raises(ExportError, match="no messages"):
        export_session(
            session=session,
            project_path=tmp_path,
            export_name="empty",
            output_dir=tmp_path / "out",
        )


def test_export_session_anonymized(session_with_file: tuple[SessionInfo, Path]):
    session, project = session_with_file
    output = project / "anon-out"

    with patch("ccgraft.exporter.get_project_session_dir", return_value=session.path.parent):
        result = export_session(
            session=session, project_path=project,
            export_name="anon", output_dir=output, anonymized=True,
        )

    manifest_data = json.loads(
        (result.export_dir / ".ccgraft-manifest.json").read_text()
    )
    assert manifest_data["original_context"]["user"] == ""


def test_resolve_export_dir_output_dir():
    result = _resolve_export_dir(Path("/project"), "name", Path("/custom"), True, "sid")
    assert result == Path("/custom/name")


def test_resolve_export_dir_in_repo():
    result = _resolve_export_dir(Path("/project"), "name", None, True, "sid")
    assert result == Path("/project/.claude-sessions/name")


def test_resolve_export_dir_not_in_repo():
    result = _resolve_export_dir(Path("/project"), "name", None, False, "abcdefgh")
    assert "claude_sessions" in str(result)
    assert "exports" in str(result)


def test_build_manifest():
    meta = SessionMetadata(session_id="sid", slug="my-slug")
    artifacts = SessionArtifacts()
    config = ConfigSnapshot()
    manifest = build_manifest(meta, artifacts, config, "export-1", Path("/project"))
    assert manifest.session_id == "sid"
    assert manifest.session_slug == "my-slug"
    assert manifest.export_name == "export-1"


def test_write_session_dir_with_todos(tmp_path: Path, sample_messages: list[dict]):
    export_dir = tmp_path / "export"
    export_dir.mkdir()

    session_file = tmp_path / "session.jsonl"
    with open(session_file, "w", encoding="utf-8") as fh:
        for msg in sample_messages:
            fh.write(json.dumps(msg) + "\n")

    todos_file = tmp_path / "todos.json"
    todos_file.write_text(json.dumps([{"task": "test"}]))

    artifacts = SessionArtifacts(todos=[todos_file])
    write_session_dir(export_dir, session_file, artifacts)

    assert (export_dir / "session" / "main.jsonl").exists()
    assert (export_dir / "session" / "todos.json").exists()
    todos = json.loads((export_dir / "session" / "todos.json").read_text())
    assert len(todos) == 1


def test_write_session_dir_with_plan(tmp_path: Path, sample_messages: list[dict]):
    export_dir = tmp_path / "export"
    export_dir.mkdir()

    session_file = tmp_path / "session.jsonl"
    with open(session_file, "w", encoding="utf-8") as fh:
        for msg in sample_messages:
            fh.write(json.dumps(msg) + "\n")

    plan_file = tmp_path / "plan.md"
    plan_file.write_text("# Plan\n- Step 1")

    artifacts = SessionArtifacts(plan_file=plan_file)
    write_session_dir(export_dir, session_file, artifacts)

    assert (export_dir / "session" / "plan.md").exists()


def test_render_markdown_with_thinking(sample_messages: list[dict]):
    sample_messages[1]["message"]["content"].append(
        {"type": "thinking", "thinking": "Let me consider..."}
    )
    from ccgraft.exporter import extract_metadata
    from ccgraft.manifest import Manifest

    meta = extract_metadata(sample_messages)
    manifest = Manifest(session_id=meta.session_id, export_name="test")
    md = render_markdown(sample_messages, meta, manifest)
    assert "Internal Reasoning" in md
    assert "Let me consider..." in md


def test_render_markdown_with_tool_result(sample_messages: list[dict]):
    sample_messages[0]["message"]["content"].append(
        {"type": "tool_result", "content": "file contents here"}
    )
    from ccgraft.exporter import extract_metadata
    from ccgraft.manifest import Manifest

    meta = extract_metadata(sample_messages)
    manifest = Manifest(session_id=meta.session_id, export_name="test")
    md = render_markdown(sample_messages, meta, manifest)
    assert "Tool Result" in md


def test_render_xml_with_tool_use(sample_messages: list[dict]):
    from ccgraft.exporter import extract_metadata
    meta = extract_metadata(sample_messages)
    xml_str = render_xml(sample_messages, meta)
    assert "<tool-use" in xml_str
    assert 'name="Read"' in xml_str
