"""Copyright (c) 2026 Achyuth Jayadevan <achyuth@jayadevan.in>
Licensed under the MIT License. See LICENSE file in the project root.

CLI entry point for restoring pre-import snapshots.
"""

from __future__ import annotations

import argparse
import logging
import sys

from ccgraft import configure_logging
from ccgraft.errors import CcgraftError
from ccgraft.snapshot import get_snapshot_info, restore_snapshot

log = logging.getLogger("ccgraft")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Restore a pre-import snapshot of Claude Code session data."
    )
    parser.add_argument(
        "--info",
        action="store_true",
        help="Show snapshot info without restoring",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Skip confirmation prompt",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args(argv)
    configure_logging(verbose=args.verbose)

    try:
        info = get_snapshot_info()
    except FileNotFoundError as exc:
        log.error("%s", exc)
        return 1

    if args.info:
        log.info("Snapshot age: %.1f hours", info.age_hours if info.age_hours is not None else 0)
        log.info("Snapshot timestamp: %s", info.timestamp)
        if info.import_source:
            log.info("Import source: %s", info.import_source)
        log.info("Target directory: %s", info.target_directory)
        if info.backup_exists:
            log.info("Prior state saved: Yes  (restore will revert to pre-import state)")
        else:
            log.info("Prior state saved: No   (restore will clear the imported session data)")
        if args.verbose and info.backup_path:
            log.info("Backup path: %s", info.backup_path)
        return 0

    if not args.force:
        print(f"This will restore: {info.target_directory}")
        print(f"Snapshot taken: {info.timestamp}")
        if info.age_hours is not None:
            print(f"Snapshot age: {info.age_hours:.1f} hours")
        response = input("Proceed? [y/N] ").strip().lower()
        if response != "y":
            print("Aborted.")
            return 1

    try:
        result = restore_snapshot()
    except CcgraftError as exc:
        log.error("Restore failed: %s", exc)
        return 1

    status = "restored from backup" if result.had_backup else "cleared (no prior data)"
    log.info("Restore completed: %s %s", result.target_directory, status)
    return 0


def cli() -> None:
    sys.exit(main())
