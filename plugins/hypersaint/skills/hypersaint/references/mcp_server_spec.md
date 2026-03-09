# Hypersaint MCP Server Specification

## For: A Coding Agent Building This Server

This document specifies the Hypersaint Navigation MCP Server. You (the coding agent) will
implement this as a Python MCP server using FastMCP. This document tells you what to build,
how it should behave, and what the intended usage patterns are. It does NOT contain implementation
code — that is your job.

---

## Table of Contents

1. [Purpose and Role](#purpose-and-role)
2. [Architecture Overview](#architecture-overview)
3. [The Progressive Disclosure README Parser](#the-progressive-disclosure-readme-parser)
4. [The index.toml Parser](#the-indextoml-parser)
5. [Tool Definitions](#tool-definitions)
6. [Recursive Navigation](#recursive-navigation)
7. [Integrity Verification](#integrity-verification)
8. [Error Handling](#error-handling)
9. [Performance Requirements](#performance-requirements)
10. [Configuration](#configuration)
11. [Testing Requirements](#testing-requirements)
12. [Deployment](#deployment)

---

## Purpose and Role

The Hypersaint MCP server is the **primary navigation tool** for LLM agents working in a
Hypersaint repository. Its job is to replace `ls`, `find`, `cat`, `grep`, and ad-hoc bash
exploration with a structured, token-efficient interface that serves exactly the right level of
detail at each step.

Without this server, the agent would:
- Run `ls -R` and load the entire directory tree (massive token waste).
- `cat README.md` and load the entire progressive disclosure document (defeats the purpose).
- `grep -r` across the repo to find relevant code (slow, noisy, context-flooding).

With this server, the agent:
- Calls `navigate("/")` and gets the top-level structure with one-line descriptions.
- Calls `readme("/src/features/auth/login")` and gets ONLY the brief.
- Calls `readme("/src/features/auth/login", section="gotchas")` and gets ONLY the gotchas.
- Calls `readme("/src/features/auth/login", faq="3")` and gets ONLY that answer.
- Calls `tree("/src/features")` and gets a recursive map with descriptions at every level.

The token savings are orders of magnitude. More importantly, the agent receives *curated,
high-relevance* information instead of raw filesystem dumps.

---

## Architecture Overview

The server is a single Python process that:

1. **On startup:** Receives the repository root path as configuration.
2. **On each request:** Reads the relevant files from disk (index.toml, README.md) and returns
   parsed, filtered results.
3. **Caches parsed index.toml and README.md structures** in memory (invalidated on file mtime
   change).

There is NO database. No external dependencies beyond the MCP SDK and TOML/markdown parsing.
The source of truth is always the filesystem.

### Technology Stack

- **Language:** Python 3.11+
- **MCP Framework:** FastMCP (Python MCP SDK)
- **TOML parsing:** `tomllib` (stdlib in 3.11+)
- **README parsing:** Custom parser for `<!-- @hs:... -->` markers (see below)
- **Hashing:** `hashlib` (stdlib)
- **Transport:** stdio (for local use) and streamable HTTP (for remote)

---

## The Progressive Disclosure README Parser

This is the core component. It parses Hypersaint README.md files into a structured tree that
can be queried at any granularity.

### Input

A README.md file containing `<!-- @hs:... -->` markers as defined in the README Format Spec.

### Parsing Rules

1. **Identify all markers.** Scan for `<!-- @hs:DIRECTIVE` and `<!-- @/hs:DIRECTIVE -->` pairs.
   Build a tree from the nesting structure.

2. **Extract brief.** Content between `<!-- @hs:brief -->` and `<!-- @/hs:brief -->`.

3. **Extract sections.** Content between `<!-- @hs:section id="ID" title="TITLE" -->` and
   `<!-- @/hs:section -->`. Each section has an `id` and `title`.

4. **Extract items within sections.** Content between `<!-- @hs:item id="ID" title="TITLE" -->`
   and `<!-- @/hs:item -->`. Items are children of their containing section.

5. **Extract FAQ entries.** Content between `<!-- @hs:faq id="ID" question="QUESTION" -->` and
   `<!-- @/hs:faq -->`. FAQs are a special type of item within their containing section.

6. **Extract integrity block.** Content between `<!-- @hs:integrity -->` and
   `<!-- @/hs:integrity -->`. Parse the markdown table into a dictionary of filename → hash.

### Output Data Structure

The parser produces a tree:

```
ReadmeDocument:
  brief: str                          # Raw markdown content of brief section
  sections: dict[str, Section]        # id → Section
  integrity: dict[str, str]           # filename → sha256 hash

Section:
  id: str
  title: str
  content: str                        # Raw markdown content (excluding nested items)
  items: dict[str, Item]              # id → Item
  faqs: dict[str, FAQ]                # id → FAQ (only in sections containing FAQs)

Item:
  id: str
  title: str
  content: str                        # Raw markdown content

FAQ:
  id: str
  question: str
  answer: str                         # Raw markdown content
```

### Edge Cases

- **No markers at all:** Treat the entire file content as the brief. Return empty sections.
- **Malformed markers:** Missing closing tag → error. The server should report which marker is
  unclosed and at what line number.
- **Nested items:** Items can theoretically contain sub-items. The parser should handle arbitrary
  nesting depth by recursing on the same pattern.
- **Content outside markers:** Any content not inside any marker is ignored by the parser (it
  renders on GitHub but is not served by the MCP server). This allows decorative markdown that
  only humans see.

---

## The index.toml Parser

Simpler than the README parser. Uses `tomllib` to parse TOML and validates against the
Hypersaint schema.

### Output Data Structure

```
IndexManifest:
  description: str | None             # Optional description
  exports: list[str]                  # Symbol names
  dependencies: dict[str, list[str]]  # import_path → [symbols]
  circular: dict[str, str]            # import_path → justification
  references: dict[str, list[Reference]]  # local_file → [Reference]
  integrity: dict[str, str]           # filename → sha256 hash
  children: dict[str, str]            # dirname → description

Reference:
  path: str                               # Repo-relative path to referenced file
  rel: str                                # Relationship type
```

### Validation

On parse, validate:
- All required tables exist (`[exports]`, `[dependencies]`, `[integrity]`).
- No unknown tables.
- All values are the expected types.
- If `[circular]` exists, values are non-empty strings (justifications).
- If `[children]` exists, every listed directory actually exists on disk.
- If `[references]` exists, every `path` must point to an existing file. Every `rel` must be from the known relationship types.

Return validation errors as structured data, not exceptions.

---

## Tool Definitions

The MCP server exposes the following tools. Each tool definition includes its name, description,
parameters, and exact behavior.

### `navigate`

**Purpose:** Get the structure of a directory — what's in it, what each child does, and the
atom's export/dependency information.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `path` | string | Yes | Path relative to repo root. Use `/` for root. |

**Behavior:**
1. Read `index.toml` at the given path.
2. Read the `brief` section from `README.md` at the given path.
3. Return a structured response containing:
   - The brief text
   - The exports list
   - The dependencies dict
   - The children dict (if non-leaf)
   - The description (if present in index.toml)
   - Whether circular dependencies exist (boolean flag — details loaded separately)
   - Soft references summary (count and relationship types, if any exist)

**Response format:**
Return as structured text. Example:

```
# /src/features/auth

Handles all authentication and authorization flows.

## Exports
(none — this is a grouping directory)

## Dependencies
(none)

## Children
- login: User authentication via password and OAuth2
- logout: Session termination and token revocation
- session: Session creation, validation, and lifecycle
- password_reset: Password reset flow via email token

## Circular Dependencies
None declared.

## Soft References
- docs/api_reference.html documents src/features/auth/login/login.py
- config/auth_limits.toml configures src/features/auth/login/login.py
```

### `readme`

**Purpose:** Read progressive disclosure sections from a README.md.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `path` | string | Yes | Path relative to repo root |
| `level` | string | No | One of: `brief` (default), `full`. Controls how much is returned. |
| `section` | string | No | Section ID to load (e.g., `architecture`, `gotchas`, `contracts`) |
| `item` | string | No | Item ID to load (e.g., `contracts.login_handler`, `examples.oauth_login`) |
| `faq` | string | No | FAQ ID to load (e.g., `1`, `2`, `3`). Returns the answer. |

**Parameter precedence:** `faq` > `item` > `section` > `level`. If `faq` is provided, return
only that FAQ answer. If `item` is provided, return only that item. And so on.

**Special behavior for FAQ sections:**
When `section="faq"` is requested (without a specific `faq` ID), return ONLY the question list,
not the answers:

```
## FAQ

1. Why does login() return a Result type instead of raising exceptions?
2. Why is there a 100ms sleep after failed login?
3. Why was a type: ignore set at line 47 in login.py?
```

The agent then requests a specific answer: `readme(path, faq="2")`.

**When `level="brief"` (default):**
Return only the brief section.

**When `level="full"`:**
Return the entire README content (all sections, all items, all FAQ answers). This is rare and
should only be used when the agent needs to rewrite or comprehensively review the README.

### `tree`

**Purpose:** Get a recursive directory tree with descriptions at every level. This is the
"zoomed out" view for understanding overall repo structure.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `path` | string | Yes | Path relative to repo root |
| `depth` | integer | No | Maximum recursion depth. Default: 3. Use -1 for unlimited. |
| `descriptions` | boolean | No | Include one-line descriptions from index.toml children tables. Default: true. |

**Behavior:**
1. Starting at the given path, recursively list child directories up to `depth` levels.
2. For each directory, read its `index.toml` to get the `[children]` descriptions.
3. If `descriptions` is true, include the one-line description next to each directory name.
4. Format as an indented tree.

**Response format:**

```
src/
  features/ — Domain feature modules
    auth/ — Authentication and authorization
      login/ — User authentication via password and OAuth2
      logout/ — Session termination and token revocation
      session/ — Session creation, validation, and lifecycle
    billing/ — Payment processing and invoicing
      invoice/ — Invoice generation and management
      payment/ — Payment gateway integration
    format/ — Shared formatting utilities
      date_format/ — Date/time formatting and parsing
      currency_format/ — Currency display formatting
  infra/ — Infrastructure layer
    database/ — Database connection and query utilities
    cache/ — Caching layer (Redis wrapper)
  core/ — Repository-wide shared utilities
    types/ — Common type definitions
    errors/ — Error hierarchy and error handling
    validation/ — Input validation utilities
```

### `deps`

**Purpose:** Analyze dependency relationships for an atom or subtree.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `path` | string | Yes | Path relative to repo root |
| `direction` | string | No | `outgoing` (what this atom depends on), `incoming` (what depends on this atom), or `both`. Default: `both`. |
| `recursive` | boolean | No | If true, follow dependency chains transitively. Default: false. |
| `include_references` | boolean | No | Include soft reference relationships alongside import dependencies. Default: true. |

**Behavior:**
1. Read the target atom's `index.toml` for outgoing dependencies.
2. For incoming dependencies: scan all `index.toml` files in the repo to find atoms that list
   the target as a dependency. (This is cached — the server builds a reverse dependency index
   on first call and invalidates on file changes.)
3. If `recursive`, follow the chain: for outgoing, get deps of deps. For incoming, get dependents
   of dependents. Mark cycle points.

**Response format:**

```
# Dependencies for /src/features/auth/login

## Outgoing (what login depends on)
- src.features.auth.session → [create_session, SessionToken]
- src.core.validation.email_format → [validate_email]
- src.infra.database.connection → [DatabaseConnection]

## Incoming (what depends on login)
- src.features.auth.password_reset → [LoginError]
- src.features.notifications.auth_events → [LoginEvent]

## Circular Dependencies
- src.features.auth.session ↔ src.features.auth.login
  Reason: Session imports LoginError for error propagation.

## Soft References
- config/auth_limits.toml configures login.py
- docs/api_reference.html documents login.py
- login.py is documented-by docs/api_reference.html
```

### `integrity`

**Purpose:** Verify integrity hashes for a directory or the entire repo.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `path` | string | Yes | Path relative to repo root. Use `/` for full repo. |
| `fix` | boolean | No | If true, update hashes in-place instead of just reporting mismatches. Default: false. |

**Behavior:**
1. Walk the directory tree starting at `path`.
2. For each directory with `index.toml` and `README.md`:
   - Recompute all file hashes.
   - Compare against declared hashes in both `index.toml` and `README.md`.
   - Report mismatches.
3. If `fix=true`: rewrite `index.toml` and `README.md` integrity blocks with correct hashes.
   Also update parent directory hashes that reference the changed files.

**Response format (check mode):**

```
# Integrity Check: /src/features/auth

✓ /src/features/auth/login — All hashes match
✗ /src/features/auth/session — 2 errors:
  HASH_MISMATCH: session.py declared=abc123... actual=def456...
  CROSS_VALIDATION: index.toml hash of README.md is stale
✓ /src/features/auth/logout — All hashes match

Summary: 1 of 3 atoms have integrity errors.
```

**Response format (fix mode):**

```
# Integrity Fix: /src/features/auth

Fixed /src/features/auth/session/index.toml — updated 1 hash
Fixed /src/features/auth/session/README.md — updated 1 hash
Fixed /src/features/auth/index.toml — updated 1 child hash (session changed)
Fixed /src/features/auth/README.md — updated 1 child hash (session changed)

Summary: 4 files updated. Run integrity check to verify.
```

### `search`

**Purpose:** Search across all manifests (index.toml and README briefs) for atoms matching a
query. This is the agent's alternative to `grep -r` — it searches structured metadata instead
of raw code.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `query` | string | Yes | Search terms |
| `scope` | string | No | `exports` (search symbol names), `briefs` (search README briefs), `descriptions` (search index.toml descriptions and children descriptions), or `all`. Default: `all`. |

**Behavior:**
1. Load all index.toml and README briefs in the repo (cached).
2. Search for the query string (case-insensitive substring match) across the selected scope.
3. Return matching atoms with their path, matched field, and a snippet of the match context.

**Response format:**

```
# Search results for "email"

1. /src/core/validation/email_format
   Match in: exports → ["validate_email", "EmailAddress"]
   Brief: Validates and normalizes email addresses. Wraps the `email-validator` library.

2. /src/features/auth/login
   Match in: brief → "Email input validation"
   Brief: Handles user authentication via username/password and OAuth2 flows.

3. /src/features/format/email_format
   Match in: children description → "Email address display formatting"
   Brief: (load with readme for details)

3 results found.
```

---

## Recursive Navigation

Several tools support recursive operation. The recursion model:

### Tree Recursion (for `tree`)
- Start at the given path.
- Read `index.toml` `[children]` table.
- For each child, recurse (up to `depth` limit).
- Output is a formatted tree string.

### Dependency Recursion (for `deps`)
- Start at the given path's `index.toml`.
- For each dependency, load that atom's `index.toml` and follow its dependencies.
- Maintain a "visited" set to detect cycles. When a cycle is detected, mark it and stop recursing
  that branch.
- Output is a formatted dependency graph.

### Integrity Recursion (for `integrity`)
- Walk all directories from the given path downward.
- At each directory, verify hashes.
- Propagation: if a child directory's `index.toml` changes (because hashes were fixed), the
  parent's hash of that child is now stale → fix the parent too → propagate upward.

---

## Error Handling

Every tool returns structured errors. Never raise unhandled exceptions to the MCP client.

### Error Response Format

When a tool encounters an error, return it as structured text in the tool response:

```
ERROR: DIRECTORY_NOT_FOUND
Path: /src/features/auth/nonexistent
Message: The directory does not exist. Available children at /src/features/auth:
  - login
  - logout
  - session
  - password_reset
```

### Error Types

| Error | When | Recovery Hint |
|-------|------|---------------|
| `DIRECTORY_NOT_FOUND` | Path doesn't exist | List available children at parent |
| `MISSING_MANIFEST` | Directory exists but lacks index.toml or README.md | Suggest running index_toml_generator.py and creating README.md |
| `MALFORMED_MANIFEST` | TOML parse error or schema violation | Show the specific parse error with line number |
| `MALFORMED_README` | Unclosed or invalid `@hs:` markers | Show the specific marker error with line number |
| `SECTION_NOT_FOUND` | Requested section/item/faq ID doesn't exist | List available section IDs |
| `HASH_MISMATCH` | Integrity check found mismatches | Show declared vs actual hash |

### Actionable Hints

Every error must include enough information for the agent to self-correct. If a section isn't
found, list the sections that DO exist. If a directory isn't found, list the directories that DO
exist at the parent level. The agent should never receive an error and have to guess what to do
next.

---

## Performance Requirements

### Caching

The server MUST cache:
- Parsed `index.toml` structures (invalidated when file mtime changes).
- Parsed `README.md` structures (invalidated when file mtime changes).
- The reverse dependency index (invalidated when any `index.toml` changes).

Cache invalidation is based on file mtime checks. On each request, check whether the relevant
files have changed since last parse. If so, re-parse. If not, serve from cache.

### Response Time

- `navigate`: < 50ms for a single directory.
- `readme`: < 50ms for a single section.
- `tree`: < 200ms for depth=3 in a repo with 1000 directories.
- `deps`: < 200ms for non-recursive, < 2s for recursive in a large repo.
- `integrity`: Proportional to repo size. < 5s for full repo check on 1000 files.
- `search`: < 500ms for full-repo search across all scopes.

### Memory

The full cache for a 1000-directory repo should fit in < 100MB. If the repo is larger, consider
LRU eviction for README parses (they are the largest cached objects).

---

## Configuration

The server accepts configuration via environment variables or a config file.

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `HYPERSAINT_REPO_ROOT` | Yes | - | Absolute path to the repository root |
| `HYPERSAINT_CACHE_SIZE` | No | `1000` | Maximum number of cached README/index parses |
| `HYPERSAINT_IGNORE_PATTERNS` | No | `.git,__pycache__,node_modules,.mypy_cache,.ruff_cache,.pytest_cache,dist,build` | Comma-separated directory names to ignore during tree/integrity walks |
| `HYPERSAINT_TRANSPORT` | No | `stdio` | Transport mode: `stdio` or `http` |
| `HYPERSAINT_HTTP_PORT` | No | `8765` | Port for HTTP transport |

### Config File

Alternatively, place a `.hypersaint.toml` at the repo root:

```toml
[server]
cache_size = 1000
transport = "stdio"
http_port = 8765
ignore_patterns = [".git", "__pycache__", "node_modules", ".mypy_cache", ".ruff_cache", ".pytest_cache", "dist", "build"]
```

Environment variables override config file values.

---

## Testing Requirements

The MCP server itself must follow Hypersaint principles. That means:

### Unit Tests

- Parser tests: Verify correct parsing of README markers for every section type, including
  edge cases (empty sections, deeply nested items, malformed markers).
- index.toml parser tests: Verify correct parsing for all table types, including optional tables.
- Hash computation tests: Verify correct SHA-256 for known files.
- Tool response format tests: Verify each tool returns correctly formatted responses.

### Property-Based Tests

- For the README parser: generate random valid README structures and verify round-trip (parse →
  serialize → parse produces identical structure).
- For integrity checking: generate random directory trees, compute hashes, mutate one file,
  verify the checker detects exactly the mutated file.

### Integration Tests

- Create a temporary Hypersaint-compliant directory structure.
- Start the MCP server pointing at it.
- Call each tool and verify responses match expectations.
- Modify a file, verify integrity tool detects the change.
- Run fix mode, verify the change is corrected.

### Test Fixtures

Include a `test_fixtures/` directory containing:
- A minimal valid Hypersaint repository structure (3-4 atoms, 2 levels deep).
- A deliberately broken structure (missing manifests, stale hashes, asymmetric circular deps)
  for testing error detection.

---

## Deployment

### Local (stdio)

For use with Claude Code, Cursor, or any MCP client that supports stdio transport:

```json
{
  "mcpServers": {
    "hypersaint": {
      "command": "python",
      "args": ["-m", "hypersaint_mcp"],
      "env": {
        "HYPERSAINT_REPO_ROOT": "/path/to/repo"
      }
    }
  }
}
```

### Remote (HTTP)

For use with remote MCP clients:

```bash
HYPERSAINT_REPO_ROOT=/path/to/repo HYPERSAINT_TRANSPORT=http python -m hypersaint_mcp
```

The server listens on the configured port and serves MCP over streamable HTTP.

### As a Dev Dependency

The server should be installable as a Python package:

```bash
pip install hypersaint-mcp
```

Or included in the project's Nix flake as a dev tool, consistent with Hypersaint's IaC principles.
