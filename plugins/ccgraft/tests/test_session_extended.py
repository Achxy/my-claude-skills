"""Copyright (c) 2026 Achyuth Jayadevan <achyuth@jayadevan.in>
Licensed under the MIT License. See LICENSE file in the project root.

Extended tests for session discovery and slug extraction.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import patch

from ccgraft.session import (
    _extract_slug,
    discover_sessions,
    find_most_recent_session,
    identify_active_session,
)


def test_extract_slug_from_first_message(tmp_path: Path):
    path = tmp_path / "session.jsonl"
    path.write_text(json.dumps({"slug": "my-session-name"}) + "\n")
    assert _extract_slug(path) == "my-session-name"


def test_extract_slug_empty_file(tmp_path: Path):
    path = tmp_path / "session.jsonl"
    path.write_text("")
    assert _extract_slug(path) == ""


def test_extract_slug_no_slug_field(tmp_path: Path):
    path = tmp_path / "session.jsonl"
    path.write_text(json.dumps({"sessionId": "abc"}) + "\n")
    assert _extract_slug(path) == ""


def test_extract_slug_malformed_json(tmp_path: Path):
    path = tmp_path / "session.jsonl"
    path.write_text("not json\n")
    assert _extract_slug(path) == ""


def test_find_most_recent_session_no_sessions(tmp_path: Path):
    with patch("ccgraft.session.get_project_session_dir", return_value=tmp_path / "nonexistent"):
        assert find_most_recent_session(tmp_path) is None


def test_find_most_recent_session_with_age_filter(tmp_path: Path):
    session_dir = tmp_path / "sessions"
    session_dir.mkdir()
    old = session_dir / "old.jsonl"
    old.write_text(json.dumps({"sessionId": "old"}) + "\n")

    import os
    old_time = time.time() - 1000
    os.utime(old, (old_time, old_time))

    with patch("ccgraft.session.get_project_session_dir", return_value=session_dir):
        result = find_most_recent_session(tmp_path, max_age_seconds=60)
    assert result is None


def test_find_most_recent_session_returns_newest(tmp_path: Path):
    session_dir = tmp_path / "sessions"
    session_dir.mkdir()

    import os
    s1 = session_dir / "s1.jsonl"
    s1.write_text(json.dumps({"sessionId": "s1"}) + "\n")
    os.utime(s1, (time.time() - 100, time.time() - 100))

    s2 = session_dir / "s2.jsonl"
    s2.write_text(json.dumps({"sessionId": "s2"}) + "\n")

    with patch("ccgraft.session.get_project_session_dir", return_value=session_dir):
        result = find_most_recent_session(tmp_path)
    assert result is not None
    assert result.session_id == "s2"


def test_identify_active_session_single(tmp_path: Path):
    session_dir = tmp_path / "sessions"
    session_dir.mkdir()
    (session_dir / "only.jsonl").write_text(json.dumps({"sessionId": "only"}) + "\n")

    with patch("ccgraft.session.get_project_session_dir", return_value=session_dir):
        result = identify_active_session(tmp_path)
    assert result is not None
    assert result.session_id == "only"


def test_identify_active_session_no_sessions(tmp_path: Path):
    with patch("ccgraft.session.get_project_session_dir", return_value=tmp_path / "nonexistent"):
        assert identify_active_session(tmp_path) is None


def test_discover_sessions_empty_dir(tmp_path: Path):
    session_dir = tmp_path / "sessions"
    session_dir.mkdir()
    with patch("ccgraft.session.get_project_session_dir", return_value=session_dir):
        assert discover_sessions(tmp_path) == []
