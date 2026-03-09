---
name: hypersaint
description: >-
  Enforces hypermodular, maximally strict repository architecture for codebases primarily or fully
  created and maintained by LLM agents. Use this skill whenever creating a new project, repository,
  or codebase from scratch, or when restructuring an existing one for LLM maintainability. Also
  trigger when the user mentions "hypersaint", "hypermodular", "hyperstrict", "LLM-native repo",
  "LLM-optimized codebase", "agent-maintained code", or asks for maximum strictness, maximum
  correctness, or aggressive modularity. Use this skill even when the user asks for project setup,
  scaffolding, or boilerplate — if the context suggests the project will be maintained by LLM agents,
  Hypersaint is the correct architecture. This skill governs both the structural organization of code
  (hypermodularity) and the quality/tooling standards (hyperstrictness). Always use this skill in
  conjunction with language-specific best practices — Hypersaint is language-agnostic and the agent
  must extrapolate its principles to whatever stack is in use.
---

# Hypersaint

An architecture and ruleset for repositories that are primarily or fully created and maintained by
LLM agents. Every decision optimizes for an agent that reads only what it needs, when it needs it,
and never the whole codebase at once.

**Two pillars:**
1. **Hyperstrictness** — Every configurable dial turned to maximum correctness. Tooling that
   enforces rather than suggests. Ceremony that eliminates ambiguity.
2. **Hypermodularity** — Aggressively decomposed directory structure with progressive disclosure
   at every level. Self-describing atoms navigable without loading the full repo.

---

## Quick Decision Guide

| Situation | Action |
|-----------|--------|
| Starting a new project | Read [Philosophy](./references/philosophy.md), then [Modularity](./references/modularity.md) |
| Setting up tooling/linting | Read [Philosophy → Tool Selection Doctrine](./references/philosophy.md) |
| Creating directory structure | Read [Modularity](./references/modularity.md) |
| Writing a README.md | Read [README Format Spec](./references/readme_format.md) |
| Creating/updating index.toml | Read [index.toml Spec](./references/index_toml_spec.md), use `scripts/index_toml_generator.py` |
| Adding CI pipeline | Use `assets/ci.yml` as template, read [CI Integrity](./references/ci_integrity.md) |
| Updating READMEs after changes | Use `scripts/readme_hooks.py` |
| Building the MCP navigation server | Read [MCP Server Spec](./references/mcp_server_spec.md) |

---

## Core Rules (Always in Context)

These rules are non-negotiable. Every Hypersaint repository must satisfy all of them.

### Strictness Rules

0. **Every strictness dimension applies.** The dimensions described in the Philosophy reference
   (structural, behavioral, data lifecycle, temporal, communication, error domain, resource,
   observability, operational, security) govern every decision. The rules below are common
   instances of those dimensions, not the exhaustive list. The agent must identify and apply
   the relevant strictness dimensions for every decision it makes.
1. **Every configurable strictness dial is at maximum.** The language's type checker, linter, and
   formatter must all run at their strictest settings. No exceptions without explicit, commented
   justification citing the specific error code. (E.g., Pyright strict mode, TypeScript `strict: true`
   plus all pedantic flags, Clippy with all lints in Rust.)
2. **Prefer tools that unify and enforce.** When multiple tools cover overlapping concerns, choose the
   single tool that consolidates them and makes the wrong thing a hard error. Fewer tools with broader
   scope beat many tools with narrow scope. (E.g., Ruff over flake8+isort+black, Biome over
   ESLint+Prettier.)
3. **Static typing is exhaustive.** Every function has full parameter and return annotations. No escape
   hatches from the type system. No untyped public API surface. Runtime validation at every trust
   boundary using the language's canonical schema validation library.
4. **Every data structure declares its shape explicitly.** No attribute, field, or member may exist at
   runtime that is not declared in the structure's definition. Dynamic attribute creation and implicit
   field inheritance are prohibited.
5. **Every module declares its public surface.** Every file and package must explicitly enumerate what
   it exports. No namespace pollution — consumers see only what the author intended. (E.g., `__all__`
   in Python, explicit `export` in TypeScript, `pub` visibility in Rust.)
6. **Every public symbol has a docstring.** Functions, classes, methods, modules. The docstring is the
   contract the next agent reads instead of the implementation.
7. **Tests are mandatory and layered.** Unit tests for known cases. Property-based tests for invariants.
   Both required for every public function. Use the language's canonical property-based testing library.
   (E.g., Hypothesis for Python, fast-check for TypeScript, proptest for Rust.)
8. **Dependencies must be proven.** High adoption, active maintenance, trusted maintainers. Never
   author security-sensitive code — wrap proven libraries so tightly that misuse is a type error.
9. **Infrastructure is code.** Dev environment, cloud resources, CI/CD, configuration, and containers
   are all declared in version-controlled, reproducible configuration files. Configuration must be
   typed and validated at startup. (E.g., Nix flakes, Terraform/Pulumi, multi-stage distroless
   container builds.)
10. **The feedback loop is sacred.** Every change runs the full strictness suite. The agent loops
    until it passes. Fast tooling is mandatory — speed enables tight loops.

### Modularity Rules

The modularity rules below are the structural strictness dimension applied to code organization. The
reason every directory has manifests, the reason boundaries are enforced by the integrity system, the
reason DRY is supreme — is because these rules make incorrect organizational states structurally
inexpressible.

1. **Directories are atoms.** The atomic unit of work is a directory containing tightly related files
   for one concept. The agent loads one atom, understands it fully, modifies it, and puts it back.
2. **Every directory has a README.md.** Uses Hypersaint progressive disclosure format. Contains
   integrity hashes of all sibling files (including index.toml, excluding itself).
3. **Every directory has an index.toml.** Machine-readable manifest declaring exports, dependencies,
   and integrity hashes of all sibling files (including README.md, excluding itself).
4. **README and index.toml cross-validate.** README hashes index.toml. index.toml hashes README.md.
   CI verifies both on every change. Mismatch is a hard failure.
5. **Nesting has no depth limit but every level self-describes.** An agent navigates root → target
   by reading one manifest at each level. No level requires loading its children to understand itself.
6. **DRY is supreme.** Duplicated code is the most dangerous defect in an LLM-maintained repo. Shared
   utilities live at semantically named paths under the lowest common ancestor of their consumers.
7. **Circular dependencies must be declared.** In the index.toml of both involved atoms. Preferred
   within the same parent directory. Always with justification.
8. **Updating manifests is part of every change.** Modifying a file without updating the containing
   directory's README.md and index.toml is an incomplete change. CI enforces this.

---

## Reference Documents

Load these as needed — do not read all of them upfront.

| Document | When to Load | Content |
|----------|-------------|---------|
| [Philosophy](./references/philosophy.md) | Project setup, tool selection, dependency decisions | Full Hypersaint philosophy: axioms, tool doctrine, code strictness, security, IaC, feedback loops |
| [Modularity](./references/modularity.md) | Creating directory structure, organizing code | Atom structure, nesting rules, shared utilities, naming, progressive disclosure architecture |
| [README Format](./references/readme_format.md) | Writing or updating any README.md | Progressive disclosure marker syntax, section types, FAQ format, integrity blocks |
| [index.toml Spec](./references/index_toml_spec.md) | Creating or updating any index.toml | Full TOML schema, field definitions, hash format, dependency declarations |
| [CI Integrity](./references/ci_integrity.md) | Setting up or modifying CI pipeline | Hash verification workflow, failure modes, integration with GitHub Actions |
| [MCP Server Spec](./references/mcp_server_spec.md) | Building the Hypersaint navigation MCP server | Complete specification for the progressive disclosure MCP server |

---

## Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| `scripts/index_toml_generator.py` | Generate/update index.toml for a directory | `python scripts/index_toml_generator.py <target_dir>` |
| `scripts/readme_hooks.py` | Top-down README update after changes | `python scripts/readme_hooks.py <root_dir> --changed <file1> <file2> ...` |

---

## Assets

| Asset | Purpose |
|-------|---------|
| `assets/ci.yml` | GitHub Actions workflow template for integrity verification |
