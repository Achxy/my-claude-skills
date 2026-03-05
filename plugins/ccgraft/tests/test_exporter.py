"""Copyright (c) 2026 Achyuth Jayadevan <achyuth@jayadevan.in>
Licensed under the MIT License. See LICENSE file in the project root.

Tests for session export orchestration.
"""

from __future__ import annotations

from ccgraft.exporter import (
    SessionMetadata,
    extract_metadata,
    compute_duration_seconds,
    render_markdown,
    render_xml,
    _format_message_md,
    _format_duration,
    _clean_xml_text,
)
from ccgraft.manifest import Manifest


def test_extract_metadata(sample_messages: list[dict]):
    meta = extract_metadata(sample_messages)
    assert meta.session_id == sample_messages[0]["sessionId"]
    assert meta.user_messages == 1
    assert meta.assistant_messages == 1
    assert meta.tool_uses == 1
    assert meta.total_messages == 2
    assert "claude-opus-4-6" in meta.models_used
    assert meta.claude_code_version == "1.2.3"
    assert meta.slug == "test-session"


def test_compute_duration_seconds():
    meta = SessionMetadata(
        start_time="2026-01-01T00:00:00Z",
        end_time="2026-01-01T01:30:00Z",
    )
    assert compute_duration_seconds(meta) == 5400


def test_compute_duration_seconds_no_times():
    meta = SessionMetadata()
    assert compute_duration_seconds(meta) is None


def test_format_duration():
    assert _format_duration(30) == "30s"
    assert _format_duration(90) == "1m 30s"
    assert _format_duration(3661) == "1h 1m"


def test_format_message_md_user(sample_messages: list[dict]):
    result = _format_message_md(sample_messages[0])
    assert "### User" in result
    assert "Hello" in result


def test_format_message_md_assistant(sample_messages: list[dict]):
    result = _format_message_md(sample_messages[1])
    assert "### Assistant" in result
    assert "Hi there!" in result
    assert "Tool Use: Read" in result


def test_format_message_md_no_message():
    assert _format_message_md({"uuid": "x"}) == ""


def test_clean_xml_text():
    assert _clean_xml_text("hello\x00world") == "helloworld"
    assert _clean_xml_text("normal text") == "normal text"
    assert _clean_xml_text("") == ""


def test_render_markdown(sample_messages: list[dict]):
    meta = extract_metadata(sample_messages)
    manifest = Manifest(
        session_id=meta.session_id,
        export_name="test-export",
    )
    md = render_markdown(sample_messages, meta, manifest)
    assert "# Claude Code Session: test-export" in md
    assert "## Conversation" in md
    assert "Hello" in md


def test_render_xml(sample_messages: list[dict]):
    meta = extract_metadata(sample_messages)
    xml_str = render_xml(sample_messages, meta)
    assert "<claude-session>" in xml_str
    assert "<session-id>" in xml_str
    assert "<messages>" in xml_str
