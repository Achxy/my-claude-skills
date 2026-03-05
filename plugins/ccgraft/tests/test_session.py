"""Copyright (c) 2026 Achyuth Jayadevan <achyuth@jayadevan.in>
Licensed under the MIT License. See LICENSE file in the project root.

Tests for session reading, writing, and UUID regeneration.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ccgraft.session import (
    read_messages,
    write_messages,
    regenerate_uuids,
    discover_sessions,
    identify_active_session,
)


def test_read_messages(session_jsonl: Path):
    messages = read_messages(session_jsonl)
    assert len(messages) == 2
    assert messages[0]["message"]["role"] == "user"
    assert messages[1]["message"]["role"] == "assistant"


def test_read_messages_skips_blank_lines(tmp_path: Path):
    path = tmp_path / "blank.jsonl"
    path.write_text('{"a": 1}\n\n{"b": 2}\n', encoding="utf-8")
    messages = read_messages(path)
    assert len(messages) == 2


def test_read_messages_skips_malformed_json(tmp_path: Path):
    path = tmp_path / "bad.jsonl"
    path.write_text('{"a": 1}\nnot json\n{"b": 2}\n', encoding="utf-8")
    messages = read_messages(path)
    assert len(messages) == 2


def test_write_messages(tmp_path: Path, sample_messages: list[dict]):
    target = tmp_path / "output.jsonl"
    write_messages(sample_messages, target)
    assert target.exists()

    lines = target.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 2
    parsed = json.loads(lines[0])
    assert parsed["message"]["role"] == "user"


def test_write_messages_refuses_overwrite(tmp_path: Path, sample_messages: list[dict]):
    target = tmp_path / "existing.jsonl"
    target.write_text("existing content", encoding="utf-8")

    with pytest.raises(FileExistsError):
        write_messages(sample_messages, target)


def test_regenerate_uuids(sample_messages: list[dict]):
    new_sid = "new-session-id"
    new_cwd = "/new/project"

    result = regenerate_uuids(sample_messages, new_sid, new_cwd)

    assert len(result) == 2

    for msg in result:
        assert msg["sessionId"] == new_sid
        assert msg["cwd"] == new_cwd

    assert result[0]["uuid"] != sample_messages[0]["uuid"]
    assert result[1]["uuid"] != sample_messages[1]["uuid"]
    assert result[1]["parentUuid"] == result[0]["uuid"]

    assert result[0]["agentId"] == result[1]["agentId"]
    assert result[0]["agentId"] != sample_messages[0]["agentId"]


def test_discover_sessions_skips_agent_files(tmp_path: Path):
    """Agent JSONL files should not appear in discover_sessions results."""
    from unittest.mock import patch

    session_dir = tmp_path / "sessions"
    session_dir.mkdir()
    (session_dir / "abc123.jsonl").write_text('{"sessionId": "abc123"}\n')
    (session_dir / "agent-def4567.jsonl").write_text('{"sessionId": "abc123"}\n')

    with patch("ccgraft.session.get_project_session_dir", return_value=session_dir):
        sessions = discover_sessions(tmp_path)

    assert len(sessions) == 1
    assert sessions[0].session_id == "abc123"
