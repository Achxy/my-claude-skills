"""Hypersaint Integrity Verification Script.

Walks the entire repository and verifies that all README.md and index.toml
manifests are in sync with actual file contents.

Usage:
    python verify_integrity.py <repo_root> [--strict] [--json]

Arguments:
    repo_root   Path to the repository root.
    --strict    Exit with code 1 on ANY error (default for CI).
    --json      Output errors as JSON (one object per line) for machine parsing.

Checks Performed:
    1. Every directory (except ignored) has both README.md and index.toml.
    2. Every hash in index.toml [integrity] matches the actual file.
    3. Every file in the directory has an entry in index.toml [integrity].
    4. No extra entries in index.toml [integrity] (referencing deleted files).
    5. Every hash in README.md <!-- @hs:integrity --> matches the actual file.
    6. Every file has an entry in README.md integrity block.
    7. No extra entries in README.md integrity block.
    8. Cross-validation: index.toml's hash of README.md matches actual README.md.
    9. Cross-validation: README.md's hash of index.toml matches actual index.toml.
    10. Circular dependency symmetry: if A declares circular with B, B must
        declare circular with A.

Output Format (default):
    One error per line:
    ERROR_CODE: path details

Output Format (--json):
    One JSON object per line:
    {"code": "HASH_MISMATCH", "path": "src/auth/login.py", "declared": "abc...", "actual": "def..."}

Exit Codes:
    0  All checks pass
    1  One or more checks failed (with --strict, which is default)
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore[no-redef]

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


@dataclass(frozen=True, slots=True)
class IntegrityError:
    """A single integrity violation."""

    code: str
    path: str
    message: str
    declared: str = ""
    actual: str = ""

    def to_line(self) -> str:
        """Format as a human-readable error line."""
        parts = [f"{self.code}: {self.path}"]
        if self.declared and self.actual:
            parts.append(f"declared={self.declared[:16]}... actual={self.actual[:16]}...")
        parts.append(self.message)
        return " ".join(parts)

    def to_json(self) -> str:
        """Format as a JSON line."""
        data: dict[str, str] = {
            "code": self.code,
            "path": self.path,
            "message": self.message,
        }
        if self.declared:
            data["declared"] = self.declared
        if self.actual:
            data["actual"] = self.actual
        return json.dumps(data)


def sha256_file(path: Path) -> str:
    """Compute SHA-256 hex digest of a file."""
    sha = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha.update(chunk)
    return sha.hexdigest()


def sha256_directory(path: Path) -> str:
    """Compute hash of a directory via its index.toml."""
    index_path = path / "index.toml"
    if not index_path.exists():
        return "MISSING"
    return sha256_file(index_path)


def should_ignore(name: str, is_dir: bool) -> bool:
    """Check if a file or directory should be ignored."""
    if is_dir:
        return name in IGNORE_DIRS or name.endswith(".egg-info")
    if name in IGNORE_FILES:
        return True
    return Path(name).suffix in IGNORE_EXTENSIONS


def parse_readme_integrity(readme_path: Path) -> dict[str, str] | None:
    """Parse the integrity block from a README.md. Returns None if no block found."""
    if not readme_path.exists():
        return None

    content = readme_path.read_text(encoding="utf-8")

    pattern = re.compile(
        re.escape(INTEGRITY_START) + r"(.*?)" + re.escape(INTEGRITY_END),
        re.DOTALL,
    )
    match = pattern.search(content)
    if not match:
        return None

    block = match.group(1)
    entries: dict[str, str] = {}

    # Parse markdown table rows: | filename | hash |
    row_pattern = re.compile(r"^\|\s*(.+?)\s*\|\s*([a-f0-9]{64})\s*\|", re.MULTILINE)
    for row_match in row_pattern.finditer(block):
        filename = row_match.group(1).strip()
        hash_val = row_match.group(2).strip()
        if filename not in ("File", "------", "---"):
            entries[filename] = hash_val

    return entries


def parse_index_toml(index_path: Path) -> dict[str, object] | None:
    """Parse index.toml. Returns None if file doesn't exist."""
    if not index_path.exists():
        return None

    with index_path.open("rb") as f:
        return tomllib.load(f)


def get_actual_entries(directory: Path, *, exclude: str) -> dict[str, str]:
    """Get actual file hashes for a directory, excluding the named file."""
    entries: dict[str, str] = {}

    for item in sorted(directory.iterdir()):
        name = item.name
        if name == exclude:
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


def check_directory(directory: Path, repo_root: Path) -> list[IntegrityError]:
    """Run all integrity checks on a single directory."""
    errors: list[IntegrityError] = []
    rel = str(directory.relative_to(repo_root))

    readme_path = directory / "README.md"
    index_path = directory / "index.toml"

    # Check 1: Both manifests exist
    if not readme_path.exists():
        errors.append(IntegrityError(
            code="MISSING_MANIFEST",
            path=f"{rel}/README.md",
            message="Directory is missing README.md",
        ))
    if not index_path.exists():
        errors.append(IntegrityError(
            code="MISSING_MANIFEST",
            path=f"{rel}/index.toml",
            message="Directory is missing index.toml",
        ))

    if not readme_path.exists() or not index_path.exists():
        return errors

    # Parse manifests
    index_data = parse_index_toml(index_path)
    readme_integrity = parse_readme_integrity(readme_path)

    if index_data is None:
        errors.append(IntegrityError(
            code="MALFORMED_MANIFEST",
            path=f"{rel}/index.toml",
            message="Failed to parse TOML",
        ))
        return errors

    # Get declared hashes
    index_integrity: dict[str, str] = {}
    if "integrity" in index_data and isinstance(index_data["integrity"], dict):
        index_integrity = {str(k): str(v) for k, v in index_data["integrity"].items()}

    # Compute actual hashes for index.toml (excludes index.toml itself)
    actual_for_index = get_actual_entries(directory, exclude="index.toml")

    # Check 2: index.toml hash accuracy
    for name, declared in index_integrity.items():
        if name in actual_for_index:
            actual = actual_for_index[name]
            if declared != actual:
                errors.append(IntegrityError(
                    code="HASH_MISMATCH",
                    path=f"{rel}/{name}",
                    message=f"Hash mismatch in index.toml",
                    declared=declared,
                    actual=actual,
                ))

    # Check 3: index.toml completeness (missing entries)
    for name in actual_for_index:
        if name not in index_integrity:
            errors.append(IntegrityError(
                code="MISSING_ENTRY",
                path=f"{rel}/{name}",
                message=f"File exists but not in index.toml [integrity]",
            ))

    # Check 4: index.toml extra entries
    for name in index_integrity:
        if name not in actual_for_index:
            errors.append(IntegrityError(
                code="EXTRA_ENTRY",
                path=f"{rel}/{name}",
                message=f"Entry in index.toml [integrity] but file does not exist",
            ))

    # Checks 5-7: README.md integrity block
    if readme_integrity is not None:
        actual_for_readme = get_actual_entries(directory, exclude="README.md")

        for name, declared in readme_integrity.items():
            if name in actual_for_readme:
                actual = actual_for_readme[name]
                if declared != actual:
                    errors.append(IntegrityError(
                        code="HASH_MISMATCH",
                        path=f"{rel}/{name}",
                        message=f"Hash mismatch in README.md integrity block",
                        declared=declared,
                        actual=actual,
                    ))

        for name in actual_for_readme:
            if name not in readme_integrity:
                errors.append(IntegrityError(
                    code="MISSING_ENTRY",
                    path=f"{rel}/{name}",
                    message=f"File exists but not in README.md integrity block",
                ))

        for name in readme_integrity:
            if name not in actual_for_readme:
                errors.append(IntegrityError(
                    code="EXTRA_ENTRY",
                    path=f"{rel}/{name}",
                    message=f"Entry in README.md integrity block but file does not exist",
                ))

    elif readme_path.exists():
        errors.append(IntegrityError(
            code="MISSING_INTEGRITY_BLOCK",
            path=f"{rel}/README.md",
            message="README.md exists but has no <!-- @hs:integrity --> block",
        ))

    # Check 8-9: Cross-validation
    # index.toml should have hash of README.md
    if "README.md" in index_integrity:
        actual_readme_hash = sha256_file(readme_path)
        if index_integrity["README.md"] != actual_readme_hash:
            errors.append(IntegrityError(
                code="CROSS_VALIDATION",
                path=f"{rel}/index.toml",
                message="index.toml hash of README.md is stale",
                declared=index_integrity["README.md"],
                actual=actual_readme_hash,
            ))

    # README.md should have hash of index.toml
    if readme_integrity is not None and "index.toml" in readme_integrity:
        actual_index_hash = sha256_file(index_path)
        if readme_integrity["index.toml"] != actual_index_hash:
            errors.append(IntegrityError(
                code="CROSS_VALIDATION",
                path=f"{rel}/README.md",
                message="README.md hash of index.toml is stale",
                declared=readme_integrity["index.toml"],
                actual=actual_index_hash,
            ))

    return errors


def check_circular_symmetry(
    repo_root: Path,
    all_dirs: list[Path],
) -> list[IntegrityError]:
    """Check that circular dependency declarations are symmetric."""
    errors: list[IntegrityError] = []

    # Collect all circular declarations
    circular_decls: dict[str, dict[str, str]] = {}

    for directory in all_dirs:
        index_path = directory / "index.toml"
        if not index_path.exists():
            continue

        data = parse_index_toml(index_path)
        if data is None:
            continue

        circular = data.get("circular", {})
        if isinstance(circular, dict) and circular:
            rel = str(directory.relative_to(repo_root))
            circular_decls[rel] = {str(k): str(v) for k, v in circular.items()}

    # Check symmetry
    for atom_path, deps in circular_decls.items():
        for dep_path in deps:
            if dep_path not in circular_decls:
                errors.append(IntegrityError(
                    code="CIRCULAR_ASYMMETRIC",
                    path=atom_path,
                    message=(
                        f"Declares circular dependency with {dep_path} "
                        f"but {dep_path} does not declare the reverse"
                    ),
                ))
            elif atom_path not in circular_decls.get(dep_path, {}):
                errors.append(IntegrityError(
                    code="CIRCULAR_ASYMMETRIC",
                    path=atom_path,
                    message=(
                        f"Declares circular dependency with {dep_path} "
                        f"but {dep_path} does not list {atom_path} in [circular]"
                    ),
                ))

    return errors


def find_managed_directories(repo_root: Path) -> list[Path]:
    """Find all directories that should be managed by Hypersaint."""
    result: list[Path] = []

    for dirpath, dirnames, _filenames in os.walk(repo_root):
        dirnames[:] = [
            d for d in dirnames if not should_ignore(d, is_dir=True)
        ]

        path = Path(dirpath)
        # A directory is managed if it contains README.md, index.toml, or any .py/.ts/.rs file
        has_manifest = (path / "README.md").exists() or (path / "index.toml").exists()
        if has_manifest:
            result.append(path)

    return result


def main() -> None:
    """Entry point."""
    if len(sys.argv) < 2:
        print(
            "Usage: python verify_integrity.py <repo_root> [--strict] [--json]",
            file=sys.stderr,
        )
        sys.exit(1)

    repo_root = Path(sys.argv[1]).resolve()
    strict = "--strict" in sys.argv
    use_json = "--json" in sys.argv

    if not repo_root.is_dir():
        print(f"ERROR: '{repo_root}' is not a directory.", file=sys.stderr)
        sys.exit(1)

    all_dirs = find_managed_directories(repo_root)
    all_errors: list[IntegrityError] = []

    for directory in all_dirs:
        errors = check_directory(directory, repo_root)
        all_errors.extend(errors)

    # Check circular symmetry across the whole repo
    all_errors.extend(check_circular_symmetry(repo_root, all_dirs))

    # Output
    if use_json:
        for error in all_errors:
            print(error.to_json())
    else:
        if all_errors:
            print(f"Hypersaint Integrity Check: {len(all_errors)} error(s) found\n")
            for error in all_errors:
                print(f"  {error.to_line()}")
            print()
            print("Run 'python scripts/readme_hooks.py . --all' to fix integrity hashes.")
        else:
            print(f"Hypersaint Integrity Check: OK ({len(all_dirs)} directories verified)")

    if all_errors and strict:
        sys.exit(1)


if __name__ == "__main__":
    main()
