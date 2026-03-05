"""Copyright (c) 2026 Achyuth Jayadevan <achyuth@jayadevan.in>
Licensed under the MIT License. See LICENSE file in the project root.

Session import orchestration.

Handles importing an exported session into the local Claude Code
environment, including UUID regeneration, artifact placement,
snapshot creation, and import logging.
"""

from __future__ import annotations

import logging
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path

from .manifest import Manifest, load_manifest
from .paths import get_project_session_dir
from .session import read_messages, regenerate_uuids, write_messages
from .snapshot import create_snapshot, log_import

log = logging.getLogger("ccgraft")


@dataclass
class ImportResult:
    """Summary of a completed import operation."""

    session_id: str
    session_path: Path
    messages_imported: int
    file_history_count: int
    todos_imported: bool
    plan_imported: bool
    config_imported: bool
    log_path: Path | None = None


def import_session(
    export_path: Path,
    target_project: Path | None = None,
    skip_config: bool = False,
    skip_snapshot: bool = False,
) -> ImportResult:
    """Import an exported session into the local Claude Code environment.

    Raises:
        ManifestError: If the export manifest is invalid.
        FileNotFoundError: If required session files are missing.
    """
    manifest = load_manifest(export_path)
    target_project = target_project or Path.cwd()
    target_dir = get_project_session_dir(target_project)

    if not skip_snapshot:
        log.info("Creating pre-import snapshot...")
        create_snapshot(target_dir, import_source=manifest.export_name)

    new_session_id = str(uuid.uuid4())
    session_path = target_dir / f"{new_session_id}.jsonl"

    messages = _import_main_session(export_path, manifest, session_path, new_session_id, target_project)
    fh_count = _import_file_history(export_path, manifest, new_session_id)
    todos_ok = _import_todos(export_path, manifest, new_session_id)
    plan_ok = _import_plan(export_path, manifest)
    config_ok = _import_config(export_path, manifest, target_project) if not skip_config else False

    summary = {
        "messages_imported": len(messages),
        "file_history_count": fh_count,
        "todos_imported": todos_ok,
        "plan_imported": plan_ok,
        "config_imported": config_ok,
    }

    log_path = log_import(manifest.to_dict(), new_session_id, session_path, summary)

    return ImportResult(
        session_id=new_session_id,
        session_path=session_path,
        messages_imported=len(messages),
        file_history_count=fh_count,
        todos_imported=todos_ok,
        plan_imported=plan_ok,
        config_imported=config_ok,
        log_path=log_path,
    )


def _import_main_session(
    export_path: Path,
    manifest: Manifest,
    target_path: Path,
    new_session_id: str,
    target_project: Path,
) -> list[dict]:
    """Read, transform, and write the main session file."""
    source = export_path / manifest.session_data.main_session
    if not source.exists():
        raise FileNotFoundError(
            f"Main session file not found: {source}. "
            "The export may be incomplete."
        )

    messages = read_messages(source)
    transformed = regenerate_uuids(messages, new_session_id, str(target_project))
    write_messages(transformed, target_path)
    return transformed


def _import_file_history(
    export_path: Path,
    manifest: Manifest,
    new_session_id: str,
) -> int:
    """Import file history snapshots into the local file-history directory."""
    if not manifest.session_data.file_history:
        return 0

    target_dir = Path.home() / ".claude" / "file-history" / new_session_id
    target_dir.mkdir(parents=True, exist_ok=True)

    count = 0
    for rel_path in manifest.session_data.file_history:
        source = export_path / rel_path
        if source.exists():
            shutil.copy2(source, target_dir / source.name)
            count += 1
        else:
            log.warning("File history missing: %s", rel_path)

    return count


def _import_todos(
    export_path: Path,
    manifest: Manifest,
    new_session_id: str,
) -> bool:
    """Import todos into the local todos directory."""
    if not manifest.session_data.todos:
        return False

    source = export_path / manifest.session_data.todos
    if not source.exists():
        log.warning("Todos file missing: %s", manifest.session_data.todos)
        return False

    todos_dir = Path.home() / ".claude" / "todos"
    todos_dir.mkdir(parents=True, exist_ok=True)

    target = todos_dir / f"{new_session_id}-imported.json"
    shutil.copy2(source, target)
    return True


def _import_plan(export_path: Path, manifest: Manifest) -> bool:
    """Import the plan file into the local plans directory."""
    if not manifest.session_data.plan_file:
        return False

    source = export_path / manifest.session_data.plan_file
    if not source.exists():
        log.warning("Plan file missing: %s", manifest.session_data.plan_file)
        return False

    plans_dir = Path.home() / ".claude" / "plans"
    plans_dir.mkdir(parents=True, exist_ok=True)

    slug = manifest.session_slug or manifest.session_id[:8]
    target = plans_dir / f"{slug}.md"
    if not target.exists():
        shutil.copy2(source, target)
    return True


def _import_config(
    export_path: Path,
    manifest: Manifest,
    target_project: Path,
) -> bool:
    """Import config snapshot into the target project's .claude/ directory."""
    config_raw = manifest.config_snapshot
    if not config_raw:
        return False

    claude_dir = target_project / ".claude"
    imported_anything = False

    for category in ("commands", "skills", "hooks", "agents", "rules"):
        rel_paths = config_raw.get(category, [])
        if not rel_paths:
            continue

        target_dir = claude_dir / category
        target_dir.mkdir(parents=True, exist_ok=True)

        for rel_path in rel_paths:
            source = export_path / rel_path
            if source.exists():
                dest = target_dir / source.name
                if not dest.exists():
                    shutil.copy2(source, dest)
                    imported_anything = True
                else:
                    log.debug("Skipping existing: %s", dest)

    settings_rel = config_raw.get("settings")
    if settings_rel:
        source = export_path / settings_rel
        dest = claude_dir / "settings.json"
        if source.exists() and not dest.exists():
            claude_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, dest)
            imported_anything = True

    claude_md_rel = config_raw.get("claude_md")
    if claude_md_rel:
        source = export_path / claude_md_rel
        dest = target_project / "CLAUDE.md"
        if source.exists() and not dest.exists():
            shutil.copy2(source, dest)
            imported_anything = True

    return imported_anything
