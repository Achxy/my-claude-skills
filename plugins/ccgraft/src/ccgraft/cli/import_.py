"""Copyright (c) 2026 Achyuth Jayadevan <achyuth@jayadevan.in>
Licensed under the MIT License. See LICENSE file in the project root.

CLI entry point for importing Claude Code sessions.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from ccgraft import configure_logging
from ccgraft.errors import CcgraftError
from ccgraft.importer import ImportResult, import_session

log = logging.getLogger("ccgraft")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Import an exported Claude Code session."
    )
    parser.add_argument(
        "export_path",
        help="Path to the export directory containing .ccgraft-manifest.json",
    )
    parser.add_argument(
        "--target-project",
        help="Target project directory (default: current directory)",
    )
    parser.add_argument(
        "--skip-config",
        action="store_true",
        help="Do not import config files",
    )
    parser.add_argument(
        "--skip-snapshot",
        action="store_true",
        help="Do not create a pre-import backup snapshot",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args(argv)
    configure_logging(verbose=args.verbose)
    export_path = Path(args.export_path)

    if not export_path.is_dir():
        log.error("Export path is not a directory: %s", export_path)
        return 1

    target = Path(args.target_project) if args.target_project else None

    try:
        result: ImportResult = import_session(
            export_path=export_path,
            target_project=target,
            skip_config=args.skip_config,
            skip_snapshot=args.skip_snapshot,
        )
    except CcgraftError as exc:
        log.error("Import failed: %s", exc)
        return 1
    except FileNotFoundError as exc:
        log.error("Missing file: %s", exc)
        return 1

    log.info("Import complete: %d messages", result.messages_imported)
    log.info("  Session: %s", result.session_id)
    log.info("  File history: %d snapshots", result.file_history_count)
    log.info(
        "  Extras: todos=%s plan=%s config=%s",
        "yes" if result.todos_imported else "no",
        "yes" if result.plan_imported else "no",
        "yes" if result.config_imported else "no",
    )
    log.info("To continue this session: claude --continue")
    return 0


def cli() -> None:
    sys.exit(main())
