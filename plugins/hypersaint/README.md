# hypersaint

An LLM-native repository architecture framework. Every decision optimizes for an agent that reads only what it needs, when it needs it, and never the whole codebase at once.

## Two Pillars

**Hyperstrictness** — Every configurable dial turned to maximum correctness. Ten dimensions of strictness applied to every decision surface: structural, behavioral, data lifecycle, temporal, communication, error domain, resource, observability, operational, and security. The wrong thing is not discouraged — it is structurally inexpressible.

**Hypermodularity** — Aggressively decomposed directory structure with progressive disclosure at every level. Every directory is a self-describing atom with machine-readable manifests (`index.toml`), progressive disclosure documentation (`README.md`), cross-validated integrity hashes, and soft reference links. An agent navigates root → target by reading one manifest at each level.

## Who It's For

Codebases primarily or fully created and maintained by LLM agents. Hypersaint trades developer experience for maximum correctness — tedium has zero cost when the maintainer doesn't get bored.

## What You Get

- A complete architecture and ruleset (philosophy, modularity, strictness dimensions)
- Progressive disclosure README format with MCP server specification
- Machine-readable `index.toml` manifests with integrity hashes and soft references
- CI integrity verification pipeline (GitHub Actions template + verification script)
- Scripts for manifest generation and maintenance

## Requirements

- Python 3.10+ (scripts use only stdlib)

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
