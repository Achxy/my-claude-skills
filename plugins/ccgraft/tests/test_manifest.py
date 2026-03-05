"""Copyright (c) 2026 Achyuth Jayadevan <achyuth@jayadevan.in>
Licensed under the MIT License. See LICENSE file in the project root.

Tests for manifest creation and validation.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ccgraft.errors import ManifestError
from ccgraft.manifest import (
    Manifest,
    SessionData,
    OriginalContext,
    load_manifest,
    MANIFEST_FILENAME,
)


def test_manifest_to_dict():
    m = Manifest(session_id="abc", export_name="test")
    d = m.to_dict()
    assert d["session_id"] == "abc"
    assert d["export_name"] == "test"
    assert "session_data" in d
    assert "original_context" in d


def test_manifest_write_and_load(tmp_path: Path):
    m = Manifest(
        session_id="test-id",
        export_name="my-export",
        session_data=SessionData(main_session="session/main.jsonl"),
        original_context=OriginalContext(user="tester", platform="darwin"),
    )

    m.write(tmp_path)
    assert (tmp_path / MANIFEST_FILENAME).exists()

    loaded = load_manifest(tmp_path)
    assert loaded.session_id == "test-id"
    assert loaded.export_name == "my-export"
    assert loaded.session_data.main_session == "session/main.jsonl"
    assert loaded.original_context.user == "tester"


def test_load_manifest_missing_file(tmp_path: Path):
    with pytest.raises(ManifestError, match="No .ccgraft-manifest.json"):
        load_manifest(tmp_path)


def test_load_manifest_invalid_json(tmp_path: Path):
    (tmp_path / MANIFEST_FILENAME).write_text("not json", encoding="utf-8")
    with pytest.raises(ManifestError, match="Invalid manifest JSON"):
        load_manifest(tmp_path)


def test_load_manifest_missing_required_fields(tmp_path: Path):
    (tmp_path / MANIFEST_FILENAME).write_text(
        json.dumps({"ccgraft_version": "1.0.0"}), encoding="utf-8"
    )
    with pytest.raises(ManifestError, match="missing required fields"):
        load_manifest(tmp_path)


def test_session_data_validates_main_session():
    SessionData(main_session="session/main.jsonl")  # ok
    SessionData(main_session="")  # ok (empty means not set)
    with pytest.raises(ManifestError, match="must be a .jsonl path"):
        SessionData(main_session="session/main.txt")
