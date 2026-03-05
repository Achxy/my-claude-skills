"""Copyright (c) 2026 Achyuth Jayadevan <achyuth@jayadevan.in>
Licensed under the MIT License. See LICENSE file in the project root.

CLI entry point for exporting Claude Code sessions.
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

from ccgraft import configure_logging
from ccgraft.errors import CcgraftError
from ccgraft.exporter import ExportResult, export_session
from ccgraft.session import SessionInfo, discover_sessions, find_most_recent_session, identify_active_session

log = logging.getLogger("ccgraft")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Export a Claude Code session to a portable directory."
    )
    parser.add_argument("--session-id", help="Specific session ID to export")
    parser.add_argument("--output-dir", help="Custom output directory")
    parser.add_argument(
        "--format",
        choices=["md", "xml", "all"],
        default="all",
        help="Output format (default: all)",
    )
    parser.add_argument("--export-name", help="Name for the export folder")
    parser.add_argument(
        "--max-age",
        type=int,
        default=300,
        help="Max session age in seconds (default: 300)",
    )
    parser.add_argument(
        "--anonymize",
        action="store_true",
        help="Exclude user info from export",
    )
    parser.add_argument(
        "--no-in-repo",
        action="store_true",
        help="Export to ~/claude_sessions/ instead of project .claude-sessions/",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args(argv)
    configure_logging(verbose=args.verbose)
    project_path = Path.cwd()

    try:
        session = _resolve_session(project_path, args)
    except CcgraftError as exc:
        log.error("%s", exc)
        return 1

    if session is None:
        log.error("No Claude Code sessions found for this project.")
        return 1

    export_name = args.export_name or datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_dir = Path(args.output_dir) if args.output_dir else None

    try:
        result: ExportResult = export_session(
            session=session,
            project_path=project_path,
            export_name=export_name,
            output_dir=output_dir,
            output_format=args.format,
            anonymized=args.anonymize,
            in_repo=not args.no_in_repo,
        )
    except CcgraftError as exc:
        log.error("Export failed: %s", exc)
        return 1

    try:
        display_path = result.export_dir.relative_to(project_path)
    except ValueError:
        display_path = result.export_dir

    if result.meta.slug:
        session_label = f"{result.meta.slug} ({result.meta.session_id[:8]})"
    else:
        session_label = result.meta.session_id

    log.info("Export complete: %s", display_path)
    log.info("  Session: %s", session_label)
    log.info("  Messages: %d | Tool uses: %d", result.meta.total_messages, result.meta.tool_uses)
    log.info("  Rendered: %s/RENDERED.md", display_path)
    return 0


def _resolve_session(project_path: Path, args: argparse.Namespace) -> SessionInfo | None:
    if args.session_id:
        sessions = discover_sessions(project_path)
        match = [s for s in sessions if s.session_id == args.session_id]
        if not match:
            log.error("Session %s not found.", args.session_id)
            return None
        return match[0]

    session = identify_active_session(project_path)
    if session is not None:
        return session

    session = find_most_recent_session(project_path, max_age_seconds=args.max_age)
    if session is None:
        session = find_most_recent_session(project_path)
    return session


def cli() -> None:
    sys.exit(main())
