"""Copyright (c) 2026 Achyuth Jayadevan <achyuth@jayadevan.in>
Licensed under the MIT License. See LICENSE file in the project root.

Path normalization for Claude Code project directories.

Claude Code stores session data in ~/.claude/projects/<normalized-path>/
where the normalized path replaces special characters with hyphens.
"""

from __future__ import annotations

import os
from pathlib import Path


def normalize_project_path(project_path: str | Path) -> str:
    """Normalize a project path to Claude Code's internal directory name.

    Claude Code converts special characters (/, \\, :, ., _) to hyphens.
    On Unix, the result is prefixed with a hyphen.

    Args:
        project_path: Absolute path to the project directory.

    Returns:
        The normalized directory name used by Claude Code.
    """
    raw = str(project_path)

    if os.name == "nt":
        normalized = raw.replace("\\", "-").replace(":", "-")
    else:
        normalized = raw.replace("\\", "/").replace("/", "-")

    normalized = normalized.replace(".", "-").replace("_", "-")

    if normalized.startswith("-"):
        normalized = normalized[1:]

    return f"-{normalized}" if os.name != "nt" else normalized


def get_projects_dir() -> Path:
    """Return the Claude Code projects directory (~/.claude/projects/)."""
    return Path.home() / ".claude" / "projects"


def get_project_session_dir(project_path: str | Path) -> Path:
    """Return the session storage directory for a given project.

    Args:
        project_path: Absolute path to the project directory.

    Returns:
        Path to ~/.claude/projects/<normalized-path>/
    """
    return get_projects_dir() / normalize_project_path(project_path)
