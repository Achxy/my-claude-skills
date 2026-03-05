"""Copyright (c) 2026 Achyuth Jayadevan <achyuth@jayadevan.in>
Licensed under the MIT License. See LICENSE file in the project root.

ccgraft - Claude Code session export, import, and restore.
"""

from __future__ import annotations

import logging

__version__ = "1.0.0"

log = logging.getLogger("ccgraft")


def configure_logging(verbose: bool = False) -> None:
    """Set up ccgraft's logger. Call once from CLI entry points."""
    level = logging.DEBUG if verbose else logging.INFO
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    log.addHandler(handler)
    log.setLevel(level)
