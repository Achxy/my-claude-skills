"""Hypersaint README Hooks — Top-Down README Integrity Updater.

Given a set of changed files, determines ALL directories whose README.md integrity
blocks need updating, collects them top-down, and updates them in the correct order
(leaf-first, then propagate upward to root).

Usage:
    python readme_hooks.py <repo_root> --changed <file1> [file2 ...]
    python readme_hooks.py <repo_root> --directory <dir1> [dir2 ...]
    python readme_hooks.py <repo_root> --all

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

IGNORE_DIRS: frozenset[str] = frozenset({
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

IGNORE_FILES: frozenset[str] = frozenset({
    ".DS_Store",
    "Thumbs.db",
})

IGNORE_EXTENSIONS: frozenset[str] = frozenset({
    ".pyc",
    ".pyo",
    ".pyd",
    ".so",
    ".dylib",
})

INTEGRITY_START = "<!-- @hs:integrity -->"
INTEGRITY_END = "<!-- @/hs:integrity -->"


def sha256_file(path: Path) -> str:
    """Compute SHA-256 hex digest of a file's raw bytes."""
    sha = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha.update(chunk)
    return sha.hexdigest()


def sha256_directory(path: Path) -> str:
    """Compute hash of a directory via its index.toml."""
    index_path = path / "index.toml"
    if not index_path.exists():
        return "MISSING_INDEX_TOML"
    return sha256_file(index_path)


def should_ignore(name: str, is_dir: bool) -> bool:
    """Check if a file or directory should be ignored."""
    if is_dir:
        return name in IGNORE_DIRS or name.endswith(".egg-info")
    if name in IGNORE_FILES:
        return True
    return Path(name).suffix in IGNORE_EXTENSIONS


def compute_integrity_entries(directory: Path) -> dict[str, str]:
    """Compute hashes for all siblings of README.md in a directory (excluding README.md)."""
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
    """Format entries as a markdown integrity table."""
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
    """Update the integrity block in a README.md. Returns True if changed."""
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
    """Find all Hypersaint-managed directories (those with README.md or index.toml)."""
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
    """Sort directories deepest-first so leaf updates happen before parent updates."""
    return sorted(directories, key=lambda p: len(p.parts), reverse=True)


def update_directory(directory: Path, *, dry_run: bool = False) -> tuple[bool, bool]:
    """Update README.md and index.toml integrity for a single directory.

    Returns (readme_changed, index_changed).
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


def main() -> None:
    """Entry point."""
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

    print()
    print(f"Summary: {readme_count} READMEs updated, {index_count} index.toml files updated.")


if __name__ == "__main__":
    main()
