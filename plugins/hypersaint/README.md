# hypersaint

A Claude Code plugin that enforces hypermodular, maximally strict repository architecture for codebases primarily or fully created and maintained by LLM agents.

## Overview

Hypersaint is a language-agnostic architecture framework built on two pillars:

1. **Hyperstrictness** — Every configurable dial turned to maximum correctness. Tooling that enforces rather than suggests. Ceremony that eliminates ambiguity.
2. **Hypermodularity** — Aggressively decomposed directory structure with progressive disclosure at every level. Self-describing atoms navigable without loading the full repo.

Every decision optimizes for an agent that reads only what it needs, when it needs it, and never the whole codebase at once.

## Skills

| Skill | Purpose |
|-------|---------|
| **hypersaint** | Architecture orchestrator. Guides project setup, directory structure, manifest creation, CI integrity, and MCP server implementation following the Hypersaint framework. |

## The Atom

The atomic unit of work is a **directory** containing tightly related files for one concept:

```
any-directory/
├── README.md          # Progressive disclosure docs (integrity hashes of siblings)
├── index.toml         # Machine-readable manifest (exports, deps, integrity hashes)
├── implementation     # Source files (< 200 lines each)
└── tests/             # Unit + property-based tests (< 400 lines each)
```

- `README.md` hashes `index.toml`. `index.toml` hashes `README.md`. CI verifies both.
- An agent navigates root → target by reading one manifest at each level.
- No level requires loading its children to understand itself.

## Reference Documents

Loaded on-demand by the skill — never all at once.

| Document | When to Load |
|----------|-------------|
| `philosophy.md` | Project setup, tool selection, dependency decisions |
| `modularity.md` | Creating directory structure, organizing code |
| `readme_format.md` | Writing or updating any `README.md` |
| `index_toml_spec.md` | Creating or updating any `index.toml` |
| `ci_integrity.md` | Setting up or modifying CI pipeline |
| `mcp_server_spec.md` | Building the Hypersaint navigation MCP server |

## Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| `index_toml_generator.py` | Generate/update `index.toml` for a directory | `python scripts/index_toml_generator.py <target_dir>` |
| `readme_hooks.py` | Top-down `README.md` update after changes | `python scripts/readme_hooks.py <root_dir> --changed <file1> <file2>` |
| `verify_integrity.py` | CI integrity verification | `python scripts/verify_integrity.py . --strict` |

## Assets

| Asset | Purpose |
|-------|---------|
| `ci.yml` | GitHub Actions workflow template for integrity verification |

## Key Conventions

### Strictness
- Maximum strictness on all linters and type checkers — no exceptions without commented justification
- Exhaustive static typing — no `Any`, no untyped public API surface
- Runtime validation (Pydantic, Zod, beartype) at every trust boundary
- `__slots__` in Python, explicit interfaces in TypeScript
- `__all__` in every Python file, explicit exports in TypeScript
- Docstrings on every public symbol
- Unit tests + property-based tests for every public function

### Modularity
- Directories are atoms — one concept per directory
- Every directory has `README.md` + `index.toml` with cross-validated integrity hashes
- DRY is supreme — shared utilities at the lowest common ancestor
- Circular dependencies must be declared in both atoms with justification
- Updating manifests is part of every change — CI enforces this

## Requirements

- Python 3.10+ (scripts use only stdlib)
- A project where LLM agents are the primary maintainers

## Installation

Via the dotclaude marketplace:

```
/plugin marketplace add Achxy/dotclaude
/plugin install hypersaint@dotclaude
```

Or load directly for development:

```bash
claude --plugin-dir ./plugins/hypersaint
```
