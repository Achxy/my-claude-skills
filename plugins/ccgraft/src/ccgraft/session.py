"""Copyright (c) 2026 Achyuth Jayadevan <achyuth@jayadevan.in>
Licensed under the MIT License. See LICENSE file in the project root.

Session discovery, reading, writing, and UUID regeneration.

Handles Claude Code session JSONL files: finding the active session,
parsing messages, writing processed sessions, and regenerating UUIDs
for portable imports.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from ._io import atomic_write, locked_open, watch_for_modification
from .paths import get_project_session_dir

log = logging.getLogger("ccgraft")


@dataclass(frozen=True)
class SessionInfo:
    """Lightweight reference to a discovered session."""

    session_id: str
    path: Path
    slug: str = ""


def discover_sessions(project_path: Path) -> list[SessionInfo]:
    """Find all session JSONL files for a project.

    Returns:
        List of SessionInfo sorted by modification time (newest first).
    """
    session_dir = get_project_session_dir(project_path)
    if not session_dir.exists():
        return []

    sessions = []
    for jsonl_file in session_dir.glob("*.jsonl"):
        if jsonl_file.stem.startswith("agent-"):
            continue
        session_id = jsonl_file.stem
        slug = _extract_slug(jsonl_file)
        sessions.append(SessionInfo(session_id=session_id, path=jsonl_file, slug=slug))

    sessions.sort(key=lambda s: s.path.stat().st_mtime, reverse=True)
    return sessions


def find_most_recent_session(
    project_path: Path, max_age_seconds: int | None = None
) -> SessionInfo | None:
    """Find the most recently modified session for a project."""
    sessions = discover_sessions(project_path)
    if not sessions:
        return None

    if max_age_seconds is not None:
        cutoff = time.time() - max_age_seconds
        sessions = [s for s in sessions if s.path.stat().st_mtime >= cutoff]

    return sessions[0] if sessions else None


def identify_active_session(
    project_path: Path,
    timeout: float = 0.5,
) -> SessionInfo | None:
    """Identify the currently active session using filesystem events.

    Uses watchdog to listen for file modification events on the session
    directory. The first JSONL file that gets written to is the active
    session. Falls back to most-recent-by-mtime on timeout.

    Args:
        project_path: Absolute path to the project directory.
        timeout: Maximum seconds to wait for a write event.

    Returns:
        The active SessionInfo, or None if no sessions exist.
    """
    sessions = discover_sessions(project_path)
    if not sessions:
        return None

    if len(sessions) == 1:
        return sessions[0]

    session_dir = get_project_session_dir(project_path)
    modified = watch_for_modification(
        directory=session_dir,
        candidates=[s.path for s in sessions],
        timeout=timeout,
    )

    if modified is not None:
        for session in sessions:
            if session.path == modified:
                log.debug("Watchdog identified active session: %s", session.session_id[:8])
                return session

    log.debug("No write events within %.1fs, falling back to most recent", timeout)
    return sessions[0]


def read_messages(session_path: Path) -> list[dict]:
    """Read all messages from a session JSONL file with a shared lock.

    Silently skips blank lines and malformed JSON lines.
    """
    messages = []
    with locked_open(session_path, "r") as fh:
        for line in fh:
            stripped = line.strip()
            if not stripped:
                continue
            try:
                messages.append(json.loads(stripped))
            except json.JSONDecodeError:
                log.debug("Skipping malformed JSON line in %s", session_path.name)
                continue
    return messages


def write_messages(messages: list[dict], target_path: Path) -> None:
    """Write messages atomically to a JSONL file.

    Raises:
        FileExistsError: If the target file already exists.
    """
    if target_path.exists():
        raise FileExistsError(
            f"Session file already exists: {target_path}. "
            "Import aborted to prevent data loss."
        )

    target_path.parent.mkdir(parents=True, exist_ok=True)
    with atomic_write(target_path) as fh:
        for msg in messages:
            fh.write(json.dumps(msg, ensure_ascii=False) + "\n")


def regenerate_uuids(
    messages: list[dict],
    new_session_id: str,
    new_cwd: str,
) -> list[dict]:
    """Regenerate local identifiers while preserving Anthropic-tied fields.

    Regenerated: sessionId, uuid, parentUuid, agentId, cwd.
    Preserved: message.id, requestId, thinking signatures, tool_use.id, timestamps.
    """
    uuid_map: dict[str, str] = {}
    new_agent_id = uuid.uuid4().hex[:7]

    for msg in messages:
        old_uuid = msg.get("uuid")
        if old_uuid and old_uuid not in uuid_map:
            uuid_map[old_uuid] = str(uuid.uuid4())

    result = []
    for msg in messages:
        updated = msg.copy()

        if "sessionId" in updated:
            updated["sessionId"] = new_session_id
        if "uuid" in updated:
            updated["uuid"] = uuid_map.get(updated["uuid"], updated["uuid"])
        if "parentUuid" in updated and updated["parentUuid"]:
            updated["parentUuid"] = uuid_map.get(
                updated["parentUuid"], updated["parentUuid"]
            )
        if "agentId" in updated:
            updated["agentId"] = new_agent_id
        if "cwd" in updated:
            updated["cwd"] = new_cwd

        result.append(updated)

    return result


def _extract_slug(session_path: Path) -> str:
    """Extract the session slug from the first message in a JSONL file."""
    try:
        with open(session_path, "r", encoding="utf-8") as fh:
            for line in fh:
                stripped = line.strip()
                if not stripped:
                    continue
                msg = json.loads(stripped)
                slug = msg.get("slug", "")
                if slug:
                    return slug
                break
    except (json.JSONDecodeError, OSError):
        pass
    return ""
