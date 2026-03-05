"""Copyright (c) 2026 Achyuth Jayadevan <achyuth@jayadevan.in>
Licensed under the MIT License. See LICENSE file in the project root.

Manifest creation and validation for ccgraft exports.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

from . import __version__
from ._io import atomic_write_text
from .errors import ManifestError


MANIFEST_FILENAME = ".ccgraft-manifest.json"

REQUIRED_FIELDS = ("ccgraft_version", "session_id", "session_data")


@dataclass
class OriginalContext:
    """Metadata about the environment where the session was created."""

    user: str = ""
    platform: str = ""
    repo_path: str = ""


@dataclass
class SessionData:
    """Pointers to session artifacts within the export directory."""

    main_session: str = ""
    file_history: list[str] = field(default_factory=list)
    todos: str = ""
    plan_file: str = ""

    def __post_init__(self) -> None:
        if self.main_session and not self.main_session.endswith(".jsonl"):
            raise ManifestError(
                f"main_session must be a .jsonl path, got: {self.main_session}"
            )


@dataclass
class Manifest:
    """The ccgraft export manifest.

    Stored as .ccgraft-manifest.json at the root of every export.
    Contains enough metadata for validation, compatibility checking,
    and targeted import of session artifacts.
    """

    ccgraft_version: str = __version__
    session_id: str = ""
    session_slug: str = ""
    export_name: str = ""
    export_timestamp: str = ""
    claude_code_version: str = ""
    session_data: SessionData = field(default_factory=SessionData)
    original_context: OriginalContext = field(default_factory=OriginalContext)
    config_snapshot: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dictionary suitable for JSON output."""
        return asdict(self)

    def write(self, directory: Path) -> Path:
        """Write the manifest atomically to a directory."""
        path = directory / MANIFEST_FILENAME
        atomic_write_text(
            path,
            json.dumps(self.to_dict(), indent=2, ensure_ascii=False),
        )
        return path


def load_manifest(export_path: Path) -> Manifest:
    """Load and validate a manifest from an export directory.

    Raises:
        ManifestError: If the manifest is missing, malformed,
            or lacks required fields.
    """
    manifest_path = export_path / MANIFEST_FILENAME
    if not manifest_path.exists():
        raise ManifestError(
            f"No {MANIFEST_FILENAME} found in {export_path}. "
            "This does not appear to be a valid ccgraft export."
        )

    try:
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ManifestError(f"Invalid manifest JSON: {exc}") from exc

    missing = [f for f in REQUIRED_FIELDS if f not in raw]
    if missing:
        raise ManifestError(
            f"Manifest missing required fields: {', '.join(missing)}. "
            "The export may be corrupted or manually modified."
        )

    session_data_raw = raw.get("session_data", {})
    session_data = SessionData(
        main_session=session_data_raw.get("main_session", ""),
        file_history=session_data_raw.get("file_history", []),
        todos=session_data_raw.get("todos", ""),
        plan_file=session_data_raw.get("plan_file", ""),
    )

    context_raw = raw.get("original_context", {})
    original_context = OriginalContext(
        user=context_raw.get("user", ""),
        platform=context_raw.get("platform", ""),
        repo_path=context_raw.get("repo_path", ""),
    )

    return Manifest(
        ccgraft_version=raw.get("ccgraft_version", ""),
        session_id=raw.get("session_id", ""),
        session_slug=raw.get("session_slug", ""),
        export_name=raw.get("export_name", ""),
        export_timestamp=raw.get("export_timestamp", ""),
        claude_code_version=raw.get("claude_code_version", ""),
        session_data=session_data,
        original_context=original_context,
        config_snapshot=raw.get("config_snapshot", {}),
    )
