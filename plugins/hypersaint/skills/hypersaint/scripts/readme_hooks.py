"""Hypersaint README Hooks — Top-Down README Integrity Updater.

Given a set of changed files, determines ALL directories whose README.md integrity
blocks need updating, collects them top-down, and updates them in the correct order
(leaf-first, then propagate upward to root).

When running in ``--changed`` mode, the script also checks whether any changed file
is a soft reference target in another atom's ``[references]`` table and emits a
warning so the referencing atom can be reviewed for content accuracy.

Usage:
    python readme_hooks.py <repo_root> --changed <file1> [file2 ...]
    python readme_hooks.py <repo_root> --directory <dir1> [dir2 ...]
    python readme_hooks.py <repo_root> --all
    python readme_hooks.py <repo_root> --all --dry-run

Arguments:
    repo_root       Path to the repository root.
    --changed       List of changed file paths (relative to repo_root). The script
                    determines which directories are affected and updates their READMEs.
    --directory     Directly specify directories to update.
    --all           Update ALL READMEs in the entire repository.
    --dry-run       Print what would be updated without writing changes.

Strategy:
    1. COLLECT: From the changed files, determine all directories that need updates.
       A directory needs an update if:
       - Any of its direct children (files or subdirectories) were modified.
       - Any of its subdirectories had their index.toml or README.md modified
         (because the parent hashes subdirectories via their index.toml).

    2. SORT: Topologically sort directories leaf-first (deepest first). This ensures
       that when we update a parent's hashes, the children's index.toml files are
       already up to date.

    3. UPDATE: For each directory (leaf to root):
       a. Recompute SHA-256 hashes of all sibling files (excluding README.md itself).
       b. Parse the existing README.md to find the <!-- @hs:integrity --> block.
       c. Replace the integrity block content with updated hashes.
       d. Write the updated README.md.

    4. ALSO UPDATE index.toml: After updating README.md, the README.md hash in
       index.toml is now stale. Re-run index_toml_generator in --update mode for
       each affected directory.

    5. SOFT REFERENCE WARNINGS: In --changed mode, after updating directories, scan
       all index.toml [references] tables to find entries whose path matches a changed
       file. Emit a warning for each match so referencing atoms can be reviewed.

Exit Codes:
    0  Success (or dry-run)
    1  Invalid arguments
    2  Repository root not found
    3  A directory is missing README.md or index.toml
"""

from __future__ import annotations

import hashlib
import os
import re
import sys
from pathlib import Path
from typing import Final

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore[no-redef]

__all__: list[str] = [
    "sha256_file",
    "sha256_directory",
    "should_ignore",
    "compute_integrity_entries",
    "format_integrity_block",
    "update_readme_integrity",
    "find_affected_directories",
    "find_all_directories",
    "topological_sort_leaf_first",
    "update_directory",
    "check_soft_reference_targets",
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
    ".github",
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

INTEGRITY_START: Final[str] = "<!-- @hs:integrity -->"
INTEGRITY_END: Final[str] = "<!-- @/hs:integrity -->"


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
    """Compute hash of a directory via its index.toml.

    Args:
        path: Path to the directory.

    Returns:
        SHA-256 digest of the directory's index.toml, or a sentinel string if missing.
    """
    index_path = path / "index.toml"
    if not index_path.exists():
        return "MISSING_INDEX_TOML"
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


def compute_integrity_entries(directory: Path) -> dict[str, str]:
    """Compute hashes for all siblings of README.md in a directory (excluding README.md).

    Args:
        directory: Path to the directory to scan.

    Returns:
        Dictionary mapping filenames to SHA-256 hashes.
    """
    entries: dict[str, str] = {}

    for item in sorted(directory.iterdir()):
        name = item.name

        if name == "README.md":
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


def format_integrity_block(entries: dict[str, str]) -> str:
    """Format entries as a markdown integrity table.

    Args:
        entries: Dictionary mapping filenames to SHA-256 hashes.

    Returns:
        Formatted markdown integrity block string.
    """
    lines: list[str] = [
        INTEGRITY_START,
        "## Integrity",
        "",
        "| File | SHA-256 |",
        "|------|---------|",
    ]

    for name, hash_val in sorted(entries.items()):
        lines.append(f"| {name} | {hash_val} |")

    lines.append(INTEGRITY_END)
    return "\n".join(lines)


def update_readme_integrity(readme_path: Path, entries: dict[str, str]) -> bool:
    """Update the integrity block in a README.md.

    Args:
        readme_path: Path to the README.md file.
        entries: Dictionary mapping filenames to SHA-256 hashes.

    Returns:
        True if the file was changed.
    """
    if not readme_path.exists():
        return False

    content = readme_path.read_text(encoding="utf-8")
    new_block = format_integrity_block(entries)

    # Find existing integrity block
    pattern = re.compile(
        re.escape(INTEGRITY_START) + r".*?" + re.escape(INTEGRITY_END),
        re.DOTALL,
    )

    match = pattern.search(content)
    if match:
        new_content = content[: match.start()] + new_block + content[match.end() :]
    else:
        # No existing integrity block — append at end
        new_content = content.rstrip() + "\n\n" + new_block + "\n"

    if new_content == content:
        return False

    readme_path.write_text(new_content, encoding="utf-8")
    return True


def find_affected_directories(
    repo_root: Path,
    changed_files: list[Path],
) -> set[Path]:
    """Determine all directories needing README/index.toml updates.

    A directory is affected if:
    1. It directly contains a changed file.
    2. Any of its child directories were affected (propagation upward).

    Args:
        repo_root: Path to the repository root.
        changed_files: List of absolute paths to changed files.

    Returns:
        Set of directory paths that need updating.
    """
    affected: set[Path] = set()

    for changed_file in changed_files:
        # The directory containing the changed file
        parent = changed_file.parent
        if parent.is_relative_to(repo_root):
            affected.add(parent)

            # Propagate upward: every ancestor up to repo_root is affected
            # because their integrity hash of the child directory changes
            current = parent.parent
            while current >= repo_root:
                affected.add(current)
                if current == repo_root:
                    break
                current = current.parent

    return affected


def find_all_directories(repo_root: Path) -> set[Path]:
    """Find all Hypersaint-managed directories (those with README.md or index.toml).

    Args:
        repo_root: Path to the repository root.

    Returns:
        Set of managed directory paths.
    """
    result: set[Path] = set()

    for dirpath, dirnames, _filenames in os.walk(repo_root):
        # Filter ignored directories in-place to prevent os.walk from descending
        dirnames[:] = [
            d for d in dirnames if not should_ignore(d, is_dir=True)
        ]

        path = Path(dirpath)
        if (path / "README.md").exists() or (path / "index.toml").exists():
            result.add(path)

    return result


def topological_sort_leaf_first(directories: set[Path]) -> list[Path]:
    """Sort directories deepest-first so leaf updates happen before parent updates.

    Args:
        directories: Set of directory paths.

    Returns:
        Sorted list of directory paths, deepest first.
    """
    return sorted(directories, key=lambda p: len(p.parts), reverse=True)


def update_directory(directory: Path, *, dry_run: bool = False) -> tuple[bool, bool]:
    """Update README.md and index.toml integrity for a single directory.

    Args:
        directory: Path to the directory to update.
        dry_run: If True, only print what would be done without writing.

    Returns:
        Tuple of (readme_changed, index_changed).
    """
    readme_path = directory / "README.md"
    index_path = directory / "index.toml"

    if not readme_path.exists():
        print(f"  SKIP {directory} — no README.md", file=sys.stderr)
        return False, False

    # Compute integrity entries for README (excludes README.md itself)
    readme_entries = compute_integrity_entries(directory)

    if dry_run:
        print(f"  WOULD UPDATE: {readme_path}")
        print(f"    Entries: {len(readme_entries)}")
        return True, True

    # Update README integrity block
    readme_changed = update_readme_integrity(readme_path, readme_entries)

    # Now update index.toml (which needs the hash of the updated README.md)
    index_changed = False
    if index_path.exists():
        # Re-run the index.toml generator in update mode
        # Import and call directly to avoid subprocess overhead
        from index_toml_generator import generate_index_toml

        generate_index_toml(directory, update=True)
        index_changed = True

    return readme_changed, index_changed


def check_soft_reference_targets(
    repo_root: Path,
    changed_files: list[Path],
    managed_dirs: set[Path],
) -> None:
    """Check if changed files are soft reference targets and emit warnings.

    Parses all index.toml files in managed directories looking for ``[references]``
    entries whose ``path`` matches a changed file. For each match, prints a warning
    so the referencing atom can be reviewed for content accuracy.

    Args:
        repo_root: Path to the repository root.
        changed_files: List of absolute paths to changed files.
        managed_dirs: Set of all managed directory paths.
    """
    # Build set of changed relative paths for fast lookup
    changed_rel: set[str] = set()
    for cf in changed_files:
        try:
            changed_rel.add(str(cf.relative_to(repo_root)))
        except ValueError:
            continue

    if not changed_rel:
        return

    for directory in managed_dirs:
        index_path = directory / "index.toml"
        if not index_path.exists():
            continue

        try:
            with index_path.open("rb") as f:
                data = tomllib.load(f)
        except Exception:
            continue

        references = data.get("references", {})
        if not isinstance(references, dict) or not references:
            continue

        referencing_rel = str(index_path.relative_to(repo_root))

        for _ref_name, ref_data in references.items():
            if not isinstance(ref_data, dict):
                continue

            ref_path = ref_data.get("path", "")
            if ref_path and ref_path in changed_rel:
                print(
                    f"SOFT_REFERENCE_TARGET_CHANGED: {referencing_rel} references "
                    f"{ref_path} which was modified. Review {referencing_rel} "
                    f"for content accuracy."
                )


def main() -> None:
    """Entry point for the README hooks updater."""
    if len(sys.argv) < 3:
        print(
            "Usage:\n"
            "  python readme_hooks.py <repo_root> --changed <file1> [file2 ...]\n"
            "  python readme_hooks.py <repo_root> --directory <dir1> [dir2 ...]\n"
            "  python readme_hooks.py <repo_root> --all\n"
            "  Add --dry-run to preview changes.",
            file=sys.stderr,
        )
        sys.exit(1)

    repo_root = Path(sys.argv[1]).resolve()
    if not repo_root.is_dir():
        print(f"ERROR: '{repo_root}' is not a directory.", file=sys.stderr)
        sys.exit(2)

    dry_run = "--dry-run" in sys.argv
    args = [a for a in sys.argv[2:] if a != "--dry-run"]

    changed_paths: list[Path] = []

    if "--all" in args:
        directories = find_all_directories(repo_root)
    elif "--changed" in args:
        idx = args.index("--changed")
        changed_paths = [
            (repo_root / p).resolve() for p in args[idx + 1 :] if not p.startswith("--")
        ]
        directories = find_affected_directories(repo_root, changed_paths)
    elif "--directory" in args:
        idx = args.index("--directory")
        directories = {
            (repo_root / p).resolve() for p in args[idx + 1 :] if not p.startswith("--")
        }
    else:
        print("ERROR: Must specify --changed, --directory, or --all.", file=sys.stderr)
        sys.exit(1)

    if not directories:
        print("No directories to update.")
        return

    # Sort leaf-first for correct propagation order
    sorted_dirs = topological_sort_leaf_first(directories)

    print(f"Updating {len(sorted_dirs)} directories ({'DRY RUN' if dry_run else 'LIVE'}):")
    print()

    readme_count = 0
    index_count = 0

    for directory in sorted_dirs:
        rel = directory.relative_to(repo_root)
        print(f"  Processing: {rel}/")

        readme_changed, index_changed = update_directory(directory, dry_run=dry_run)

        if readme_changed:
            readme_count += 1
        if index_changed:
            index_count += 1

    # Soft reference target warnings (only in --changed mode)
    if changed_paths:
        check_soft_reference_targets(repo_root, changed_paths, directories)

    print()
    print(f"Summary: {readme_count} READMEs updated, {index_count} index.toml files updated.")


if __name__ == "__main__":
    main()
