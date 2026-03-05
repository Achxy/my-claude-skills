"""Copyright (c) 2026 Achyuth Jayadevan <achyuth@jayadevan.in>
Licensed under the MIT License. See LICENSE file in the project root.

Shared fixtures for ccgraft tests.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest


@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    """Create a minimal project directory with a .claude/ structure."""
    project = tmp_path / "my-project"
    project.mkdir()
    claude_dir = project / ".claude"
    claude_dir.mkdir()
    (claude_dir / "settings.json").write_text('{"key": "value"}', encoding="utf-8")
    (project / "CLAUDE.md").write_text("# Project\n", encoding="utf-8")
    return project


@pytest.fixture
def sample_messages() -> list[dict]:
    """Return a minimal list of session messages for testing."""
    sid = str(uuid.uuid4())
    msg_uuid1 = str(uuid.uuid4())
    msg_uuid2 = str(uuid.uuid4())
    return [
        {
            "sessionId": sid,
            "uuid": msg_uuid1,
            "parentUuid": None,
            "agentId": "abc1234",
            "cwd": "/tmp/test-project",
            "timestamp": "2026-01-01T00:00:00Z",
            "version": "1.2.3",
            "slug": "test-session",
            "type": "human",
            "message": {
                "role": "user",
                "content": [{"type": "text", "text": "Hello"}],
            },
        },
        {
            "sessionId": sid,
            "uuid": msg_uuid2,
            "parentUuid": msg_uuid1,
            "agentId": "abc1234",
            "cwd": "/tmp/test-project",
            "timestamp": "2026-01-01T00:00:01Z",
            "type": "assistant",
            "message": {
                "role": "assistant",
                "model": "claude-opus-4-6",
                "content": [
                    {"type": "text", "text": "Hi there!"},
                    {
                        "type": "tool_use",
                        "id": "toolu_123",
                        "name": "Read",
                        "input": {"file_path": "/tmp/test.py"},
                    },
                ],
                "usage": {
                    "input_tokens": 100,
                    "output_tokens": 50,
                },
            },
        },
    ]


@pytest.fixture
def session_jsonl(tmp_path: Path, sample_messages: list[dict]) -> Path:
    """Write sample messages to a JSONL file and return its path."""
    path = tmp_path / "session.jsonl"
    with open(path, "w", encoding="utf-8") as fh:
        for msg in sample_messages:
            fh.write(json.dumps(msg) + "\n")
    return path
