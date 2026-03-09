"""Hypersaint index.toml Generator.

Generates or updates the index.toml manifest for a target directory.
Computes SHA-256 hashes of all sibling files and directories, and writes
a valid Hypersaint index.toml with the [integrity] table populated.

Usage:
    python index_toml_generator.py <target_dir> [--update]

Arguments:
    target_dir  Path to the directory to generate index.toml for.
    --update    If set, preserve existing [exports], [dependencies], [circular],
                [children], [references], and description fields. Only regenerate
                [integrity].
                If not set, generate a skeleton index.toml with empty tables.

Behavior:
    - Scans all files and directories in target_dir (excluding index.toml itself
      and ignored patterns).
    - Computes SHA-256 hash of each file.
    - For subdirectories, computes SHA-256 of their index.toml (errors if missing).
    - Writes index.toml with sorted [integrity] entries.
    - In --update mode: reads existing index.toml, preserves non-integrity tables
      (including [references]), replaces [integrity] with freshly computed hashes.

Ignored Patterns:
    .git, __pycache__, node_modules, .mypy_cache, .ruff_cache, .pytest_cache,
    dist, build, .DS_Store, *.pyc, *.pyo

Exit Codes:
    0  Success
    1  Target directory does not exist
    2  A subdirectory is missing its index.toml (cannot compute directory hash)
    3  Write error
"""

from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path
from typing import Final

__all__: list[str] = [
    "sha256_file",
    "sha256_directory",
    "should_ignore",
    "collect_entries",
    "read_existing_toml",
    "format_toml",
    "generate_index_toml",
    "main",
]

IGNORE_DIRS: Final[frozenset[str]] = frozenset({
    ".git",
    "__pycache__",
    "node_modules",
    ".mypy_cache",
    ".ruff_cache",
    ".pytest_cache",
    "dist",
    "build",
    ".venv",
    "venv",
    ".tox",
    ".nox",
    ".eggs",
    "*.egg-info",
})

IGNORE_FILES: Final[frozenset[str]] = frozenset({
    ".DS_Store",
    "Thumbs.db",
})

IGNORE_EXTENSIONS: Final[frozenset[str]] = frozenset({
    ".pyc",
    ".pyo",
    ".pyd",
    ".so",
    ".dylib",
})


def sha256_file(path: Path) -> str:
    """Compute SHA-256 hex digest of a file's raw bytes.

    Args:
        path: Path to the file.

    Returns:
        Hex-encoded SHA-256 digest.
    """
    sha = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha.update(chunk)
    return sha.hexdigest()


def sha256_directory(path: Path) -> str:
    """Compute hash of a directory by hashing its index.toml content.

    Args:
        path: Path to the directory.

    Returns:
        SHA-256 digest of the directory's index.toml.

    Raises:
        SystemExit: If the directory is missing its index.toml.
    """
    index_path = path / "index.toml"
    if not index_path.exists():
        print(
            f"ERROR: Subdirectory '{path}' is missing index.toml. "
            "Cannot compute directory hash. Create index.toml first.",
            file=sys.stderr,
        )
        sys.exit(2)
    return sha256_file(index_path)


def should_ignore(name: str, is_dir: bool) -> bool:
    """Check if a file or directory should be ignored.

    Args:
        name: Name of the file or directory.
        is_dir: Whether the entry is a directory.

    Returns:
        True if the entry should be ignored.
    """
    if is_dir:
        return name in IGNORE_DIRS or name.endswith(".egg-info")
    if name in IGNORE_FILES:
        return True
    return Path(name).suffix in IGNORE_EXTENSIONS


def collect_entries(target_dir: Path) -> dict[str, str]:
    """Collect all sibling files/dirs and their hashes, excluding index.toml itself.

    Args:
        target_dir: Path to the directory to scan.

    Returns:
        Dictionary mapping filenames to SHA-256 hashes.
    """
    entries: dict[str, str] = {}

    for item in sorted(target_dir.iterdir()):
        name = item.name

        if name == "index.toml":
            continue

        if item.is_dir():
            if should_ignore(name, is_dir=True):
                continue
            entries[name] = sha256_directory(item)
        elif item.is_file():
            if should_ignore(name, is_dir=False):
                continue
            entries[name] = sha256_file(item)

    return entries


def read_existing_toml(path: Path) -> dict[str, object]:
    """Read existing index.toml and return parsed tables (excluding [integrity]).

    Args:
        path: Path to the existing index.toml file.

    Returns:
        Parsed TOML data with the integrity table removed.
    """
    if not path.exists():
        return {}

    try:
        import tomllib
    except ImportError:
        import tomli as tomllib  # type: ignore[no-redef]

    with path.open("rb") as f:
        data = tomllib.load(f)

    data.pop("integrity", None)
    return data


def format_toml(data: dict[str, object], integrity: dict[str, str]) -> str:
    """Format a complete index.toml string from data tables and integrity hashes.

    Args:
        data: Dictionary of non-integrity tables to serialize.
        integrity: Dictionary mapping filenames to SHA-256 hashes.

    Returns:
        Formatted TOML string.
    """
    lines: list[str] = []

    # Top-level description (optional)
    if "description" in data:
        desc = data["description"]
        lines.append(f'description = "{desc}"')
        lines.append("")

    # [exports]
    exports = data.get("exports", {"symbols": []})
    lines.append("[exports]")
    symbols = exports.get("symbols", []) if isinstance(exports, dict) else []
    symbols_str = ", ".join(f'"{s}"' for s in symbols)
    lines.append(f"symbols = [{symbols_str}]")
    lines.append("")

    # [dependencies]
    deps = data.get("dependencies", {})
    lines.append("[dependencies]")
    if isinstance(deps, dict) and deps:
        for dep_path, syms in sorted(deps.items()):
            if isinstance(syms, list):
                syms_str = ", ".join(f'"{s}"' for s in syms)
                lines.append(f'"{dep_path}" = [{syms_str}]')
    lines.append("")

    # [circular] (only if present)
    circular = data.get("circular", {})
    if isinstance(circular, dict) and circular:
        lines.append("[circular]")
        for circ_path, justification in sorted(circular.items()):
            lines.append(f'"{circ_path}" = "{justification}"')
        lines.append("")

    # [children] (only if present)
    children = data.get("children", {})
    if isinstance(children, dict) and children:
        lines.append("[children]")
        for name, desc in sorted(children.items()):
            lines.append(f'{name} = "{desc}"')
        lines.append("")

    # [references] (only if present)
    references = data.get("references", {})
    if isinstance(references, dict) and references:
        for ref_name, ref_data in sorted(references.items()):
            lines.append(f"[references.{ref_name}]")
            if isinstance(ref_data, dict):
                for key, val in sorted(ref_data.items()):
                    lines.append(f'{key} = "{val}"')
            lines.append("")

    # [integrity]
    lines.append("[integrity]")
    for name, hash_val in sorted(integrity.items()):
        lines.append(f'"{name}" = "{hash_val}"')
    lines.append("")

    return "\n".join(lines)


def generate_index_toml(target_dir: Path, *, update: bool = False) -> None:
    """Generate or update index.toml for the target directory.

    Args:
        target_dir: Path to the directory.
        update: If True, preserve existing non-integrity tables.
    """
    index_path = target_dir / "index.toml"

    # Collect integrity hashes
    entries = collect_entries(target_dir)

    if update and index_path.exists():
        # Preserve existing non-integrity data
        existing = read_existing_toml(index_path)
    else:
        # Generate skeleton
        existing = {}

    content = format_toml(existing, entries)

    try:
        index_path.write_text(content, encoding="utf-8")
    except OSError as e:
        print(f"ERROR: Failed to write {index_path}: {e}", file=sys.stderr)
        sys.exit(3)

    print(f"{'Updated' if update else 'Generated'}: {index_path}")
    print(f"  Entries: {len(entries)}")


def main() -> None:
    """Entry point for the index.toml generator."""
    if len(sys.argv) < 2:
        print("Usage: python index_toml_generator.py <target_dir> [--update]", file=sys.stderr)
        sys.exit(1)

    target = Path(sys.argv[1]).resolve()
    update = "--update" in sys.argv

    if not target.is_dir():
        print(f"ERROR: '{target}' is not a directory.", file=sys.stderr)
        sys.exit(1)

    generate_index_toml(target, update=update)


if __name__ == "__main__":
    main()
