"""Copyright (c) 2026 Achyuth Jayadevan <achyuth@jayadevan.in>
Licensed under the MIT License. See LICENSE file in the project root.

Safe I/O primitives: atomic writes, advisory file locking, and
filesystem event watching.

Atomic writes use a temporary file in the same directory as the target,
then rename on success. This prevents partial writes from corrupting
data if the process is interrupted.

File locking uses fcntl.flock on Unix. On platforms without fcntl,
locking degrades gracefully to a no-op.

Filesystem watching uses watchdog for event-driven notification
instead of polling. Used for active session identification and
auto-export hooks.
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import IO, Any, Iterator

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

try:
    import fcntl

    _HAS_FCNTL = True
except ImportError:
    _HAS_FCNTL = False


@contextmanager
def atomic_write(target: Path, mode: str = "w", encoding: str = "utf-8") -> Iterator[IO]:
    """Context manager that writes to a temp file, then atomically renames.

    If the block raises, the temp file is cleaned up and the target is
    untouched. The temp file is created in the same directory as the
    target to guarantee same-filesystem rename.
    """
    target.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp_path = tempfile.mkstemp(
        dir=target.parent,
        prefix=f".{target.name}.",
        suffix=".tmp",
    )
    try:
        with open(fd, mode, encoding=encoding if "b" not in mode else None) as fh:
            yield fh
        os.replace(tmp_path, target)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def atomic_write_text(target: Path, content: str, encoding: str = "utf-8") -> None:
    """Write text content atomically to a file."""
    with atomic_write(target, encoding=encoding) as fh:
        fh.write(content)


def atomic_write_json(target: Path, data: Any, indent: int = 2) -> None:
    """Write JSON data atomically to a file."""
    with atomic_write(target) as fh:
        json.dump(data, fh, indent=indent, ensure_ascii=False)
        fh.write("\n")


@contextmanager
def locked_open(path: Path, mode: str = "r", encoding: str = "utf-8") -> Iterator[IO]:
    """Open a file with an advisory shared (read) or exclusive (write) lock.

    On platforms without fcntl (Windows), this is equivalent to a plain
    open() -- advisory locking is best-effort, not a hard guarantee.
    """
    lock_exclusive = any(c in mode for c in "wa+")
    fh = open(path, mode, encoding=encoding if "b" not in mode else None)
    try:
        if _HAS_FCNTL:
            op = fcntl.LOCK_EX if lock_exclusive else fcntl.LOCK_SH
            fcntl.flock(fh.fileno(), op)
        try:
            yield fh
        finally:
            if _HAS_FCNTL:
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
    finally:
        fh.close()


class _ModifiedFileHandler(FileSystemEventHandler):
    """Captures the first modified .jsonl file path via a threading event."""

    def __init__(self, candidates: set[str]) -> None:
        super().__init__()
        self.candidates = candidates
        self.matched: str | None = None
        self.event = threading.Event()

    def on_modified(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        src = str(event.src_path)
        if src in self.candidates:
            self.matched = src
            self.event.set()


def watch_for_modification(
    directory: Path,
    candidates: list[Path],
    timeout: float = 0.5,
) -> Path | None:
    """Watch a directory and return the first candidate file that gets modified.

    Uses watchdog's event-driven observer instead of polling. The observer
    runs in a background thread; this function blocks until either a
    candidate is modified or the timeout expires.

    Args:
        directory: Directory to watch.
        candidates: Files within the directory to watch for.
        timeout: Maximum seconds to wait.

    Returns:
        The Path of the first modified candidate, or None on timeout.
    """
    candidate_strs = {str(c) for c in candidates}
    handler = _ModifiedFileHandler(candidate_strs)

    observer = Observer()
    observer.schedule(handler, str(directory), recursive=False)
    observer.start()

    try:
        handler.event.wait(timeout=timeout)
    finally:
        observer.stop()
        observer.join(timeout=2.0)

    return Path(handler.matched) if handler.matched else None


@contextmanager
def watch_directory(
    directory: Path,
    handler: FileSystemEventHandler,
) -> Iterator[Observer]:
    """Context manager that runs a watchdog observer for the given directory.

    Useful for long-running watches like auto-export hooks.

    Usage::

        with watch_directory(session_dir, my_handler) as observer:
            observer.join()  # blocks until stopped
    """
    observer = Observer()
    observer.schedule(handler, str(directory), recursive=False)
    observer.start()
    try:
        yield observer
    finally:
        observer.stop()
        observer.join(timeout=2.0)
