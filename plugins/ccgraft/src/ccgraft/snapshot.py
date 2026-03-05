"""Copyright (c) 2026 Achyuth Jayadevan <achyuth@jayadevan.in>
Licensed under the MIT License. See LICENSE file in the project root.

Pre-import snapshot management.

Creates safety snapshots before import operations so that the user
can roll back if the import produces undesired results.
"""

from __future__ import annotations

import json
import logging
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from ._io import atomic_write_json
from .errors import RestoreError

log = logging.getLogger("ccgraft")

STORAGE_DIR_NAME = ".claude-session-imports"


def get_storage_dir() -> Path:
    """Return the base directory for import metadata and snapshots."""
    return Path.home() / STORAGE_DIR_NAME


def get_snapshot_dir() -> Path:
    """Return the pre-import snapshot directory."""
    return get_storage_dir() / "pre-import-snapshot"


@dataclass
class SnapshotInfo:
    """Describes an existing pre-import snapshot."""

    timestamp: str
    target_directory: str
    backup_exists: bool
    backup_path: str | None
    age_hours: float | None
    import_source: str = ""


def create_snapshot(target_dir: Path, import_source: str = "") -> Path:
    """Create a pre-import snapshot of the target session directory.

    Overwrites any previous snapshot. The snapshot captures the full
    contents of the target directory so it can be restored later.

    Args:
        target_dir: The session directory to snapshot.
        import_source: Human-readable name of the export being imported
            (e.g. the export_name from the manifest). Stored in the
            snapshot info so --info can show what was imported.
    """
    snapshot_dir = get_snapshot_dir()
    if snapshot_dir.exists():
        shutil.rmtree(snapshot_dir)

    snapshot_dir.mkdir(parents=True, exist_ok=True)

    if target_dir.exists():
        backup_dest = snapshot_dir / "projects" / target_dir.name
        backup_dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(target_dir, backup_dest)
        log.debug("Snapshot created: %s -> %s", target_dir, backup_dest)

    info = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "target_directory": str(target_dir),
        "backup_exists": target_dir.exists(),
        "import_source": import_source,
    }
    atomic_write_json(snapshot_dir / "snapshot_info.json", info)

    return snapshot_dir


def get_snapshot_info() -> SnapshotInfo:
    """Retrieve information about the current pre-import snapshot.

    Raises:
        FileNotFoundError: If no snapshot exists.
    """
    info_path = get_snapshot_dir() / "snapshot_info.json"
    if not info_path.exists():
        raise FileNotFoundError(
            "No pre-import snapshot found. "
            "A snapshot is only created when you run an import."
        )

    raw = json.loads(info_path.read_text(encoding="utf-8"))

    age_hours: float | None = None
    try:
        ts = datetime.fromisoformat(raw["timestamp"])
        now = datetime.now(ts.tzinfo or timezone.utc)
        age_hours = (now - ts).total_seconds() / 3600
    except (ValueError, TypeError, KeyError):
        pass

    backup_path: str | None = None
    if raw.get("backup_exists"):
        candidate = get_snapshot_dir() / "projects" / Path(raw["target_directory"]).name
        if candidate.exists():
            backup_path = str(candidate)

    return SnapshotInfo(
        timestamp=raw.get("timestamp", ""),
        target_directory=raw.get("target_directory", ""),
        backup_exists=raw.get("backup_exists", False),
        backup_path=backup_path,
        age_hours=age_hours,
        import_source=raw.get("import_source", ""),
    )


@dataclass
class RestoreResult:
    """Summary of a completed restore operation."""

    restored: bool
    target_directory: str
    had_backup: bool


def restore_snapshot() -> RestoreResult:
    """Restore the target directory from the pre-import snapshot.

    Raises:
        FileNotFoundError: If no snapshot exists.
        RestoreError: If the restore operation fails.
    """
    info = get_snapshot_info()
    target_dir = Path(info.target_directory)
    snapshot_dir = get_snapshot_dir()

    try:
        if info.backup_exists and info.backup_path:
            backup = Path(info.backup_path)
            if target_dir.exists():
                shutil.rmtree(target_dir)
            shutil.copytree(backup, target_dir)
        else:
            if target_dir.exists():
                shutil.rmtree(target_dir)

        if snapshot_dir.exists():
            shutil.rmtree(snapshot_dir)

        return RestoreResult(
            restored=True,
            target_directory=str(target_dir),
            had_backup=info.backup_exists,
        )
    except Exception as exc:
        raise RestoreError(
            f"Restore failed: {exc}. "
            f"The snapshot has NOT been deleted. Manual recovery: {snapshot_dir}"
        ) from exc


def get_last_import_info() -> dict | None:
    """Retrieve the most recent import log entry."""
    index_path = get_storage_dir() / "index.json"
    if not index_path.exists():
        return None

    raw = json.loads(index_path.read_text(encoding="utf-8"))
    imports = raw.get("imports", {})
    if not imports:
        return None

    latest_key = max(imports.keys())
    entry = imports[latest_key]
    return {
        "import_id": latest_key,
        "session_name": entry.get("session_name"),
        "source_path": entry.get("source_path"),
        "imported_at": entry.get("imported_at"),
    }


def log_import(
    manifest_data: dict,
    new_session_id: str,
    target_path: Path,
    summary: dict,
) -> Path:
    """Record an import operation for audit and recovery."""
    storage = get_storage_dir()
    storage.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
    log_dir = storage / timestamp
    log_dir.mkdir(parents=True, exist_ok=True)

    log_content = {
        "import_timestamp": datetime.now(timezone.utc).isoformat(),
        "original_session_id": manifest_data.get("session_id"),
        "new_session_id": new_session_id,
        "original_export_name": manifest_data.get("export_name"),
        "target_session_file": str(target_path),
        "summary": summary,
    }

    log_path = log_dir / "import.log"
    atomic_write_json(log_path, log_content)

    index_path = storage / "index.json"
    if index_path.exists():
        index = json.loads(index_path.read_text(encoding="utf-8"))
    else:
        index = {"last_snapshot_taken": None, "imports": {}}

    index["imports"][timestamp] = {
        "session_name": manifest_data.get("export_name"),
        "source_path": str(target_path.parent),
        "imported_at": log_content["import_timestamp"],
    }
    index["last_snapshot_taken"] = datetime.now(timezone.utc).isoformat()
    atomic_write_json(index_path, index)

    return log_path
