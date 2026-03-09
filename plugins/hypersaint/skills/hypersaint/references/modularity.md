# Hypersaint Modularity

## Table of Contents

1. [The Modularity Axiom](#the-modularity-axiom)
2. [The Atom](#the-atom)
3. [Directory Nesting](#directory-nesting)
4. [Shared Utilities](#shared-utilities)
5. [Dependency Management](#dependency-management)
6. [The Manifest System](#the-manifest-system)
7. [Progressive Disclosure Architecture](#progressive-disclosure-architecture)
8. [Naming Conventions](#naming-conventions)
9. [The Agent Navigation Model](#the-agent-navigation-model)
10. [File Size and Complexity Limits](#file-size-and-complexity-limits)

---

## The Modularity Axiom

Traditional codebases are organized around human ergonomics — files grouped by what makes sense to
scroll through together, modules sized for a developer's mental model of a feature. This breaks
down when the primary maintainer is an LLM that does not scroll, does not have persistent memory,
and operates best when it can load a single small unit, understand it completely, modify it, and
put it back without needing to comprehend the surrounding system.

Hypersaint modularity resolves the tension between **navigability** (the LLM needs to find the
right piece fast) and **isolation** (once it finds the piece, it should need nothing else to work
on it).

The key insight: in a hypermodular repo with full type annotations, docstrings, and `__all__`
declarations, the agent working on module B does not need to read the *implementation* of a
dependency — it reads the type signature and the docstring, which are the contract. DRY therefore
*saves* context window rather than costing it, because a shared utility's contract is loaded once
and is far smaller than duplicated implementations.

---

## The Atom

The atom is the fundamental unit of work in a Hypersaint repository. It is a **directory**
containing tightly related files that together represent one concept.

### What Lives Inside an Atom

```
feature_name/
├── README.md              # Progressive disclosure documentation (required)
├── index.toml             # Machine-readable manifest (required)
├── feature_name.py        # Implementation (one or more files)
├── test_feature_name.py   # Unit + property-based tests (co-located, required)
└── fixtures/              # Test fixtures, if needed (co-located)
    └── sample_input.json
```

Rules for atom contents:

1. **README.md** — Required. Uses Hypersaint progressive disclosure format. Contains integrity
   hashes of every sibling file and directory (including index.toml, excluding itself).
2. **index.toml** — Required. Machine-readable manifest. Contains integrity hashes of every sibling
   file and directory (including README.md, excluding itself).
3. **Implementation files** — The actual code. One concept per atom. If a file grows beyond what
   represents a single cohesive concept, it should be split into a sub-atom (a subdirectory with
   its own README.md and index.toml).
4. **Test files** — Co-located. Always. The agent loading this atom has everything it needs to
   understand and verify the code. Test file names mirror implementation file names with a `test_`
   prefix (Python) or `.test.` infix (TypeScript) or `_test` suffix (Rust/Go).
5. **Test fixtures** — Co-located inside the atom if they are specific to this atom. Shared test
   infrastructure (factories, builders, mock servers) lives at a semantically named shared path
   under the lowest common ancestor.
6. **No configuration files at the atom level.** Tooling configuration (pyproject.toml, biome.json,
   Cargo.toml) lives at the repository root or at the top-level project boundary. Atoms inherit
   configuration. They do not override it.

### What Does NOT Live Inside an Atom

- Global configuration files (these live at root)
- Documentation that spans multiple atoms (this lives at the parent level)
- Build artifacts, cache files, generated code (these are gitignored)

---

## Directory Nesting

Directories nest predictably following conventional domain decomposition, but decomposed to
extremes. There is **no depth limit**. Each level self-describes via its README.md and index.toml.

### Example Structure

```
project_root/
├── README.md
├── index.toml
├── flake.nix
├── pyproject.toml
│
├── src/
│   ├── README.md
│   ├── index.toml
│   │
│   ├── features/
│   │   ├── README.md
│   │   ├── index.toml
│   │   │
│   │   ├── auth/
│   │   │   ├── README.md
│   │   │   ├── index.toml
│   │   │   │
│   │   │   ├── login/
│   │   │   │   ├── README.md
│   │   │   │   ├── index.toml
│   │   │   │   ├── login.py
│   │   │   │   └── test_login.py
│   │   │   │
│   │   │   ├── logout/
│   │   │   │   ├── README.md
│   │   │   │   ├── index.toml
│   │   │   │   ├── logout.py
│   │   │   │   └── test_logout.py
│   │   │   │
│   │   │   └── session/
│   │   │       ├── README.md
│   │   │       ├── index.toml
│   │   │       ├── session.py
│   │   │       └── test_session.py
│   │   │
│   │   ├── billing/
│   │   │   ├── README.md
│   │   │   ├── index.toml
│   │   │   │
│   │   │   ├── invoice/
│   │   │   │   └── ...
│   │   │   └── payment/
│   │   │       └── ...
│   │   │
│   │   └── format/                    # Shared utilities for features
│   │       ├── README.md
│   │       ├── index.toml
│   │       │
│   │       ├── date_format/
│   │       │   ├── README.md
│   │       │   ├── index.toml
│   │       │   ├── date_format.py
│   │       │   └── test_date_format.py
│   │       │
│   │       ├── currency_format/
│   │       │   └── ...
│   │       └── email_format/
│   │           └── ...
│   │
│   ├── infra/
│   │   ├── README.md
│   │   ├── index.toml
│   │   │
│   │   ├── database/
│   │   │   └── ...
│   │   └── cache/
│   │       └── ...
│   │
│   └── core/                          # Repository-wide shared utilities
│       ├── README.md
│       ├── index.toml
│       │
│       ├── types/
│       │   └── ...
│       ├── errors/
│       │   └── ...
│       └── validation/
│           └── ...
│
├── deploy/
│   ├── README.md
│   ├── index.toml
│   ├── terraform/
│   │   └── ...
│   └── docker/
│       └── ...
│
└── ci/
    ├── README.md
    ├── index.toml
    └── workflows/
        └── ...
```

### Nesting Rules

1. **Every directory at every level has README.md and index.toml.** No exceptions. Even if the
   directory contains a single subdirectory, it has its own manifests.
2. **Nesting follows domain decomposition.** `features/auth/login/` is three levels because the
   domain is `features` → `auth` → `login`. Do not flatten this to `features/auth_login/` — depth
   encodes semantic hierarchy that the agent uses for navigation.
3. **Each level's README describes only its immediate contents.** The `features/` README describes
   `auth/`, `billing/`, and `format/`. It does NOT describe `auth/login/` — that is `auth/`'s
   README's job. This prevents redundancy and ensures each level is independently accurate.
4. **No depth limit, but earn each level.** A new directory level is warranted when:
   - The parent directory would otherwise contain more than ~7 atoms (cognitive overload threshold).
   - The items being grouped share a semantic relationship that deserves a name.
   - The grouping enables a shared utility path (see Shared Utilities below).
5. **Leaf atoms should be small.** A leaf atom (one with no subdirectories) should ideally be
   comprehensible by loading just its files — typically 1-3 implementation files, 1-3 test files.
   If a leaf atom grows beyond this, decompose it into sub-atoms.

---

## Shared Utilities

Shared utilities are code used by more than one atom. They follow the DRY principle, which is
supreme in Hypersaint — duplicated code is the most dangerous defect in an LLM-maintained repo.

### Placement Rules

Shared utilities live at **semantically named paths** under the **lowest common ancestor** of
their consumers.

1. **Semantic naming is mandatory.** Never `_shared/`, `_common/`, `utils/`, or `helpers/`. The
   directory name must describe what the utilities *do*. `format/` if they format things.
   `validation/` if they validate things. `transform/` if they transform things. The name is the
   first layer of progressive disclosure — an agent reading the parent directory's manifest
   should understand what this group of utilities is for without loading any of them.

2. **Lowest common ancestor placement.** If `features/auth/` and `features/billing/` both need
   date formatting, the utility lives at `features/format/date_format/`. If `features/auth/` and
   `infra/database/` both need it, it lives at `src/core/format/date_format/` (the root-level
   shared utilities). The utility rises *exactly* to the level where all consumers can import it.

3. **Promotion on second use.** A utility starts life inside the atom that first needs it. When a
   second consumer appears, the utility is extracted to the appropriate shared path. This prevents
   premature abstraction — utilities earn their shared status by being actually shared.

4. **Shared utilities are atoms too.** They have README.md, index.toml, tests. They follow every
   Hypersaint rule. They are not second-class citizens just because they are "utilities."

### Example

Two features need date formatting and currency formatting, but only one needs email formatting:

```
features/
├── format/                        # Shared by multiple features
│   ├── date_format/              # Used by auth + billing
│   └── currency_format/          # Used by billing + reporting
├── auth/
│   ├── email_format/             # Used only by auth (not promoted yet)
│   ├── login/
│   └── session/
└── billing/
    ├── invoice/
    └── payment/
```

If `notifications/` later needs email formatting too:

```
features/
├── format/
│   ├── date_format/
│   ├── currency_format/
│   └── email_format/            # Promoted: now used by auth + notifications
├── auth/
│   ├── login/
│   └── session/
├── billing/
│   └── ...
└── notifications/
    └── ...
```

---

## Dependency Management

### DRY Is Supreme

Duplicated code is the single most dangerous defect in an LLM-maintained repo. The agent fixes a
bug in one copy and doesn't know the other copies exist. Every piece of logic exists exactly once.
Every other module that needs it imports it from that single source.

This is not at odds with atom isolation. In a Hypersaint repo where every public symbol has full
type annotations and a docstring, the agent working on a consumer module reads the utility's
*contract* (type signature + docstring) — not its implementation. The implementation need not be
loaded into context unless the task is to modify the utility itself.

### Dependency Direction

There is no mandatory layered architecture (e.g., "domain never imports infrastructure"). Hypersaint
does not impose a layer cake. However:

1. **Dependency cycles must be declared.** If atom A depends on atom B and atom B depends on atom A,
   both atoms' index.toml files must declare the circular dependency with a `[circular]` table
   that names the other atom and provides a justification.

2. **Cycles are preferred within the same parent.** Two siblings under the same parent directory
   (e.g., `auth/login/` and `auth/session/`) having a circular dependency is tolerable and often
   honest — they model a genuine bidirectional relationship. Cross-branch cycles
   (e.g., `auth/login/` ↔ `billing/payment/`) are a strong signal of a misplaced responsibility
   and should be restructured. This is a **soft rule** — if restructuring would create worse
   problems (duplication, artificial indirection), the cycle can remain with justification.

3. **Import linting is mandatory.** Use tooling to enforce dependency rules:
   - Python: `import-linter` or `ruff` import rules
   - TypeScript: `eslint-plugin-import` or Biome import rules
   - Rust: `cargo-deny` for crate-level, module visibility for internal

---

## The Manifest System

Every directory has two manifests that cross-validate each other.

### README.md

Human-and-agent-readable. Progressive disclosure format (see README Format Spec reference).
Contains:
- Brief description (always visible via MCP)
- Architecture details (loaded on request)
- Gotchas/traps (loaded on request)
- Invariants/contracts (loaded on request, per-component)
- Related atoms (loaded on request)
- Usage examples (loaded on request, per-API)
- Changelog / decision log (loaded on request)
- FAQ with individually loadable answers (loaded on request, per-question)
- Integrity hash block

### index.toml

Machine-readable. Contains:
- File integrity hashes (including README.md hash)
- Exports declaration
- Dependency declarations
- Circular dependency declarations (if any, with justification)
- Optional 1-2 sentence description (rare, reserved for non-obvious cases)

See the index.toml Spec reference for the full schema.

### Cross-Validation

README.md contains the hash of index.toml. index.toml contains the hash of README.md. They
validate each other. If either is modified without updating the other, CI fails. This mechanical
check makes manifest staleness impossible to miss.

---

## Progressive Disclosure Architecture

README.md files use a marker-based progressive disclosure system that renders as valid GitHub
markdown but is parsed by the Hypersaint MCP server into individually loadable sections.

The full format specification is in the README Format Spec reference. The key architectural
principles:

1. **Brief is always returned.** Any query about a directory returns the brief section. This is
   the agent's table of contents — enough to decide whether to load deeper.
2. **Sections are loaded individually.** The agent requests "architecture" or "gotchas" or
   "examples" by name. Only that section is returned.
3. **FAQ questions are listed without answers.** The agent sees the questions, identifies which
   is relevant to its task, and requests only that answer by ID.
4. **Sub-sections within sections are independently loadable.** Contracts can be loaded per-component.
   Examples can be loaded per-API. The granularity matches the agent's likely task scope.
5. **Integrity is loadable but not auto-included.** Hash verification is a separate concern from
   content navigation. The agent or CI requests the integrity block explicitly.

---

## Naming Conventions

### Directories

- **Lowercase with underscores.** `date_format/`, not `DateFormat/` or `date-format/`.
- **Singular nouns for atoms.** `login/`, not `logins/`. The directory is the concept, not a
  collection.
- **Plural nouns for grouping directories.** `features/`, `types/`, `errors/`. The directory
  contains multiple atoms.
- **Semantically descriptive.** The name should tell the agent what is inside without opening
  anything. `format/` over `utils/`. `validation/` over `helpers/`. `transform/` over `common/`.

### Files

- **Implementation files match the atom name.** `login/login.py`, `session/session.ts`.
- **Test files mirror implementation files.** `login/test_login.py`, `session/session.test.ts`.
- **One public concept per file.** A file may contain private helpers for the public concept, but
  it exports exactly one primary thing (a class, a function group, a schema).

### Imports

- **Absolute imports from the project root.** `from src.features.auth.login.login import LoginHandler`.
  Never relative imports that navigate upward (`from ...format import ...`). Absolute imports are
  greppable and unambiguous.
- **Import the symbol, not the module** (where language conventions permit). `from module import Class`
  over `import module` in Python. Named imports in TypeScript/JavaScript.

---

## The Agent Navigation Model

An agent working on a Hypersaint repository follows this pattern:

1. **Start at root.** Read root index.toml (via MCP: `navigate("/")`). Get top-level structure.
2. **Navigate to area of interest.** Based on the task, identify which top-level directory to
   enter. Read its brief (via MCP: `readme("/src/features", level="brief")`).
3. **Drill down.** Repeat: read the next level's brief, identify the target atom.
4. **Load the atom.** Read the target atom's brief. If needed, request architecture, contracts,
   examples, or FAQ answers for specific questions relevant to the task.
5. **Work.** Load the implementation and test files. Make changes.
6. **Update manifests.** Update the atom's README.md (hashes, and any content changes if the
   atom's public API changed) and index.toml. Propagate hash updates to parent directories
   (the parent's README and index.toml hash their children, which now changed).
7. **Verify.** Run integrity check. Run strictness suite on the atom. Loop until pass.
8. **Commit.** The change is complete.

The MCP server is the primary navigation tool. The agent should not use `find`, `ls -R`, or `grep`
to navigate the structure — it uses the MCP server, which returns exactly the right level of detail
at each step and prevents accidental context overload.

---

## File Size and Complexity Limits

These are guidelines, not hard limits. The principle is: if an agent would need to scroll, the file
is too long.

- **Implementation files:** Aim for < 200 lines. If a file exceeds this, consider whether it
  represents more than one concept and should be decomposed into sub-atoms.
- **Test files:** May be longer than implementation files (test code is often more verbose). Aim
  for < 400 lines. If longer, split by test category (unit vs property vs integration).
- **README.md:** No limit — the progressive disclosure system means the agent never loads the
  whole thing at once. Write as comprehensively as needed.
- **index.toml:** Typically < 50 lines. If longer, the directory has too many direct children
  and should be further decomposed.
