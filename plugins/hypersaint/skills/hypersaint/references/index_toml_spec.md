# Hypersaint index.toml Specification

## Table of Contents

1. [Overview](#overview)
2. [Full Schema](#full-schema)
3. [Field Definitions](#field-definitions)
4. [Hash Computation](#hash-computation)
5. [Dependency Declarations](#dependency-declarations)
6. [Circular Dependencies](#circular-dependencies)
7. [Soft References](#soft-references)
8. [Description Field](#description-field)
9. [Examples](#examples)
10. [Validation Rules](#validation-rules)

---

## Overview

`index.toml` is the machine-readable manifest present in every directory of a Hypersaint
repository. It serves three purposes:

1. **Integrity verification.** SHA-256 hashes of every sibling file (including README.md, excluding
   itself) enable CI to detect when code changes without manifest updates.
2. **Dependency declaration.** Explicit listing of what this atom imports and exports, enabling
   dependency graph analysis without parsing code.
3. **Navigation support.** The MCP server reads index.toml to provide structured directory
   information to the agent.

---

## Full Schema

```toml
# Optional: 1-2 sentence description. RARE. See Description Field section.
# description = "..."

[exports]
# Public symbols this atom exposes
symbols = ["LoginHandler", "LoginConfig", "LoginError"]

[dependencies]
# Atoms this one imports from. Keys are import paths, values are lists of imported symbols.
"src.features.auth.session" = ["create_session", "SessionToken"]
"src.core.validation.email_format" = ["validate_email"]
"src.infra.database.connection" = ["DatabaseConnection"]

[circular]
# Only present if circular dependencies exist. See Circular Dependencies section.
# "src.features.auth.session" = "Session needs LoginError type for error propagation"

[references]
# Only present if soft references exist. See Soft References section.
# [[references."local_file"]]
# path = "repo/relative/path"
# rel = "relationship_type"

[integrity]
# SHA-256 hashes of every sibling file/directory, excluding index.toml itself.
# README.md IS included here (cross-validation).
# Subdirectories are hashed as the SHA-256 of their index.toml content.
# Entries are sorted alphabetically.
"README.md" = "a1b2c3d4e5f6..."
"login.py" = "f6e5d4c3b2a1..."
"test_login.py" = "1a2b3c4d5e6f..."
"fixtures" = "6f5e4d3c2b1a..."

[children]
# Only present in non-leaf directories. Lists immediate child directories.
# Keys are directory names, values are one-line descriptions.
login = "User authentication via password and OAuth2"
logout = "Session termination and token revocation"
session = "Session creation, validation, and lifecycle management"
```

---

## Field Definitions

### `description` (Optional, Top-Level)

A 1-2 sentence description of what this directory contains. This field is **rare and discouraged
in most cases** — the README.md brief section is the primary description mechanism.

Use `description` ONLY when something is non-obvious at the architectural level — for example:
- Multiple sources of truth exist and the manifest needs to clarify which is canonical.
- The directory's purpose is not inferable from its name and position in the tree.
- A significant architectural decision affects how this directory should be interpreted.

If the directory name, its position in the hierarchy, and its README brief adequately describe
its purpose, omit this field.

### `[exports]`

The public API surface of this atom.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `symbols` | Array of strings | Yes | Every public symbol this atom exports. In Python, this mirrors `__all__`. In TypeScript, this mirrors the named exports. |

### `[dependencies]`

What this atom imports from other atoms.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Keys | String (import path) | - | The full import path to the dependency atom |
| Values | Array of strings | - | The specific symbols imported from that atom |

If the atom has no external dependencies, this table is present but empty: `[dependencies]`.

### `[circular]`

Present ONLY if circular dependencies exist. See Circular Dependencies section below.

### `[references]`

Present ONLY if semantic cross-references exist between files in this atom and files elsewhere
in the repository.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Keys | String (local filename) | - | Relative path to the local file being cross-referenced |
| `path` | String | Yes | Path to the referenced file, relative to repo root |
| `rel` | String | Yes | Relationship type from the known set |

### `[integrity]`

SHA-256 hashes for integrity verification.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Keys | String (filename or dirname) | - | Relative path to the sibling file or directory |
| Values | String (hex SHA-256) | - | Lowercase hex-encoded SHA-256 hash |

Rules:
- `index.toml` itself is EXCLUDED (cannot hash itself).
- `README.md` IS included (cross-validation).
- All other files are included.
- Subdirectories are represented by the SHA-256 hash of their `index.toml` file content.
- Entries are sorted alphabetically by key.

### `[children]`

Present ONLY in non-leaf directories (directories that contain subdirectories).

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Keys | String (directory name) | - | Name of the child directory |
| Values | String | - | One-line description (< 80 chars) |

---

## Hash Computation

All hashes are SHA-256, hex-encoded, lowercase, full 64-character digest.

### File Hashing

```python
import hashlib

def hash_file(path: str) -> str:
    """Compute SHA-256 of a file's raw bytes."""
    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()
```

### Directory Hashing

A directory's hash is the SHA-256 of its `index.toml` file content. This creates a Merkle-like
chain: if any file inside a subdirectory changes → its `index.toml` hashes change → the parent's
integrity hash for that subdirectory changes → the parent's `README.md` integrity block changes →
the grandparent's integrity hash for the parent changes → and so on up to root.

```python
def hash_directory(path: str) -> str:
    """Compute hash of a directory by hashing its index.toml."""
    index_path = os.path.join(path, "index.toml")
    return hash_file(index_path)
```

### Cross-Validation

The cross-validation guarantee:

1. `README.md` integrity block contains the hash of `index.toml`.
2. `index.toml` `[integrity]` table contains the hash of `README.md`.
3. If either file is modified, the other's hash reference becomes stale.
4. CI recomputes all hashes and compares against both files.
5. Any mismatch → hard failure. No merge.

This means modifying ANY file in a directory requires updating BOTH `README.md` and `index.toml`.
There is no shortcut.

---

## Dependency Declarations

Dependencies are declared with full import paths and specific symbols.

```toml
[dependencies]
"src.features.auth.session" = ["create_session", "SessionToken"]
"src.core.types.result" = ["Result", "Ok", "Err"]
```

### Rules

1. **Every import must be declared.** If the code in this atom imports from another atom, the
   dependency must appear here. Import linting tooling (import-linter, eslint-plugin-import)
   enforces this.
2. **Symbols must be specific.** No wildcard imports. `["*"]` is never valid. List every symbol.
3. **Transitive dependencies are not declared.** If A depends on B and B depends on C, A's
   index.toml only lists B. Transitive deps are resolved by the MCP server's recursive navigation.
4. **Standard library and third-party imports are not declared.** Only dependencies on other atoms
   within the same repository are listed.

---

## Circular Dependencies

Circular dependencies are not banned but must be declared, justified, and ideally contained.

```toml
[circular]
"src.features.auth.session" = "Session creates LoginEvent which references LoginError type. Restructuring would require a shared error types atom that adds indirection without benefit since these two atoms are always modified together."
```

### Rules

1. **Both sides must declare.** If A ↔ B is circular, both A's and B's index.toml must have a
   `[circular]` entry naming the other.
2. **Justification is mandatory.** The value is a string explaining WHY the cycle exists and WHY
   restructuring is worse than the cycle.
3. **Same-parent preferred (soft rule).** Circular dependencies between siblings (atoms under the
   same parent directory) are tolerable. Cross-branch cycles are a strong signal of misplaced
   responsibility and should be restructured unless the justification is compelling.
4. **CI can enforce.** The integrity CI can optionally fail on undeclared circular dependencies
   detected by import analysis.

---

## Soft References

The `[references]` table declares semantic relationships between files that are not import
dependencies. These are many-to-many cross-links: a documentation file documents an implementation
file, a generated artifact derives from a source template, a config file governs a service file.

### Schema

```toml
[references]
# Keys are local files (relative to this directory).
# Values are arrays of tables with `path` (relative to repo root) and `rel` (relationship type).

[[references."docs/api_reference.html"]]
path = "src/features/download/downloader.py"
rel = "documents"

[[references."docs/api_reference.html"]]
path = "src/features/upload/uploader.py"
rel = "documents"

[[references."config/download_limits.toml"]]
path = "src/features/download/downloader.py"
rel = "configures"
```

### Relationship Types

| Type | Meaning | Inverse |
|------|---------|---------|
| `documents` | This file documents the target | `documented-by` |
| `documented-by` | This file is documented by the target | `documents` |
| `generates` | This file is the source that generates the target | `generated-from` |
| `generated-from` | This file was generated from the target | `generates` |
| `configures` | This file configures the behavior of the target | `configured-by` |
| `configured-by` | This file's behavior is configured by the target | `configures` |
| `tests` | This file tests the target (beyond co-located test files) | `tested-by` |
| `tested-by` | This file is tested by the target | `tests` |
| `related` | General semantic relationship (use sparingly; prefer specific types) | `related` |

### Rules

1. **Paths in `path` must point to existing files.** Non-existent reference targets are hard
   failures in CI.
2. **Relationship types must be from the known set.** Unknown relationship types are errors.
3. **Many-to-many is expected.** A single file can reference multiple targets, and a single
   target can be referenced by multiple files across different atoms.
4. **Inverse declarations are encouraged but not required.** If atom A says file X `documents`
   file Y, atom B (containing Y) may optionally declare Y as `documented-by` X. The MCP server
   can infer inverse relationships from one-sided declarations.
5. **`related` is the escape hatch.** Use it only when no specific type fits. Overuse of
   `related` signals that a new relationship type should be proposed.

---

## Description Field

The optional top-level `description` field is governed by strict rules to prevent it from becoming
a dumping ground.

### When to Use

- A report directory contains both PNG figures and the HTML/CSS source that generated them, and
  it's unclear which is canonical.
- A directory exists for historical reasons and its name doesn't reflect its current purpose.
- An architectural constraint makes this directory's role non-obvious (e.g., it exists to break
  a dependency cycle, not because it represents a domain concept).

### When NOT to Use

- The directory name clearly describes its purpose (`login/`, `date_format/`, `database/`).
- The README.md brief section adequately explains the directory.
- You're tempted to use it because "it doesn't hurt" — if it's not needed, its presence adds
  noise that the agent must process.

### Format

```toml
description = "Contains both generated PNG figures and the HTML/CSS templates used to create them. The PNGs in output/ are the canonical artifacts; the templates in src/ are the source of truth."
```

Maximum 2 sentences. If you need more, the README.md architecture section is the right place.

---

## Examples

### Leaf Atom (No Children)

```toml
[exports]
symbols = ["LoginHandler", "LoginConfig", "LoginError"]

[dependencies]
"src.features.auth.session" = ["create_session", "SessionToken"]
"src.core.validation.email_format" = ["validate_email"]
"src.infra.database.connection" = ["DatabaseConnection"]

[integrity]
"README.md" = "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2"
"login.py" = "f6e5d4c3b2a1f6e5d4c3b2a1f6e5d4c3b2a1f6e5d4c3b2a1f6e5d4c3b2a1f6e5"
"test_login.py" = "1a2b3c4d5e6f1a2b3c4d5e6f1a2b3c4d5e6f1a2b3c4d5e6f1a2b3c4d5e6f1a2b"
```

### Grouping Directory (Has Children)

```toml
[exports]
symbols = []

[dependencies]

[children]
login = "User authentication via password and OAuth2"
logout = "Session termination and token revocation"
session = "Session creation, validation, and lifecycle"
password_reset = "Password reset flow via email token"

[integrity]
"README.md" = "b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3"
"login" = "c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4"
"logout" = "d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5"
"session" = "e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6"
"password_reset" = "f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1"
```

### Atom with Circular Dependency

```toml
[exports]
symbols = ["LoginHandler", "LoginConfig", "LoginError"]

[dependencies]
"src.features.auth.session" = ["create_session", "SessionToken"]

[circular]
"src.features.auth.session" = "Session imports LoginError for error propagation. Both atoms model the auth flow and are always modified together."

[integrity]
"README.md" = "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2"
"login.py" = "f6e5d4c3b2a1f6e5d4c3b2a1f6e5d4c3b2a1f6e5d4c3b2a1f6e5d4c3b2a1f6e5"
"test_login.py" = "1a2b3c4d5e6f1a2b3c4d5e6f1a2b3c4d5e6f1a2b3c4d5e6f1a2b3c4d5e6f1a2b"
```

### Atom with Description (Rare)

```toml
description = "Contains generated PNG figures and the HTML/CSS source templates. PNGs in output/ are canonical; templates in src/ are source of truth."

[exports]
symbols = ["generate_figure", "FigureConfig"]

[dependencies]
"src.core.types.color" = ["ColorPalette"]

[integrity]
"README.md" = "1122334455667788990011223344556677889900112233445566778899001122"
"figure_gen.py" = "aabbccddeeff00112233445566778899aabbccddeeff00112233445566778899"
"test_figure_gen.py" = "ffeeddccbbaa99887766554433221100ffeeddccbbaa99887766554433221100"
```

---

## Validation Rules

CI and the MCP server validate index.toml against these rules:

1. **Schema compliance.** All tables must be from the known set: `exports`, `dependencies`,
   `circular`, `references`, `integrity`, `children`. Unknown tables are errors.
2. **Hash accuracy.** Every hash in `[integrity]` must match the recomputed hash of the
   corresponding file or directory. Mismatches are hard failures.
3. **Completeness.** Every file and directory sibling to index.toml must have an entry in
   `[integrity]`. Missing entries are hard failures. Extra entries (referencing nonexistent
   files) are also hard failures.
4. **Cross-validation.** The hash of `README.md` in `[integrity]` must match the actual file.
   The hash of `index.toml` in README.md's integrity block must match the actual file.
5. **Circular symmetry.** If atom A declares a circular dependency on atom B, atom B must also
   declare a circular dependency on atom A. Asymmetric declarations are hard failures.
6. **Export accuracy.** If the atom contains Python files, `[exports].symbols` should match the
   union of all `__all__` declarations. (Tooling can enforce this; it is a recommended check,
   not always a hard failure depending on language.)
7. **Description length.** If `description` is present, it must be ≤ 2 sentences. Enforced by
   counting sentence-ending punctuation (`.`, `!`, `?`).
8. **Reference target existence.** Every `path` in `[references]` must point to a file that
   exists in the repository. Non-existent targets are hard failures.
9. **Reference relationship validity.** Every `rel` in `[references]` must be from the known
   set of relationship types. Unknown types are hard failures.
