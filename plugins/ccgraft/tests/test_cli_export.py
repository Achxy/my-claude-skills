"""Copyright (c) 2026 Achyuth Jayadevan <achyuth@jayadevan.in>
Licensed under the MIT License. See LICENSE file in the project root.

Tests for the export CLI entry point.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from ccgraft.cli.export import main
from ccgraft.errors import ExportError
from ccgraft.session import SessionInfo


@pytest.fixture
def fake_session(tmp_path: Path, sample_messages: list[dict]) -> SessionInfo:
    session_file = tmp_path / "sessions" / "abc123.jsonl"
    session_file.parent.mkdir(parents=True)
    with open(session_file, "w", encoding="utf-8") as fh:
        for msg in sample_messages:
            fh.write(json.dumps(msg) + "\n")
    return SessionInfo(session_id="abc123", path=session_file, slug="test-session")


def test_main_no_sessions():
    with patch("ccgraft.cli.export.identify_active_session", return_value=None), \
         patch("ccgraft.cli.export.find_most_recent_session", return_value=None):
        assert main([]) == 1


def test_main_exports_session(tmp_path: Path, fake_session: SessionInfo):
    output = tmp_path / "output"
    old_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        with patch("ccgraft.cli.export.identify_active_session", return_value=fake_session):
            code = main(["--output-dir", str(output), "--export-name", "test"])
    finally:
        os.chdir(old_cwd)
    assert code == 0
    assert (output / "test").exists()


def test_main_with_session_id(tmp_path: Path, fake_session: SessionInfo):
    output = tmp_path / "output"
    old_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        with patch("ccgraft.cli.export.discover_sessions", return_value=[fake_session]):
            code = main(["--session-id", "abc123", "--output-dir", str(output), "--export-name", "by-id"])
    finally:
        os.chdir(old_cwd)
    assert code == 0


def test_main_session_id_not_found():
    with patch("ccgraft.cli.export.discover_sessions", return_value=[]):
        code = main(["--session-id", "nonexistent"])
    assert code == 1


def test_main_export_error(tmp_path: Path, fake_session: SessionInfo):
    with patch("ccgraft.cli.export.identify_active_session", return_value=fake_session), \
         patch("ccgraft.cli.export.export_session", side_effect=ExportError("boom")):
        code = main([])
    assert code == 1


def test_main_verbose(tmp_path: Path, fake_session: SessionInfo):
    output = tmp_path / "output"
    old_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        with patch("ccgraft.cli.export.identify_active_session", return_value=fake_session):
            code = main(["-v", "--output-dir", str(output), "--export-name", "verbose-test"])
    finally:
        os.chdir(old_cwd)
    assert code == 0


def test_main_fallback_to_most_recent(tmp_path: Path, fake_session: SessionInfo):
    output = tmp_path / "output"
    old_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        with patch("ccgraft.cli.export.identify_active_session", return_value=None), \
             patch("ccgraft.cli.export.find_most_recent_session", side_effect=[None, fake_session]):
            code = main(["--output-dir", str(output), "--export-name", "fallback"])
    finally:
        os.chdir(old_cwd)
    assert code == 0
