# Hypersaint README Format Specification

## Table of Contents

1. [Overview](#overview)
2. [Marker Syntax](#marker-syntax)
3. [Section Types](#section-types)
4. [Disclosure Levels](#disclosure-levels)
5. [FAQ Format](#faq-format)
6. [Sub-Sections](#sub-sections)
7. [Integrity Block](#integrity-block)
8. [Full Example](#full-example)
9. [Rendering Behavior](#rendering-behavior)
10. [Authoring Rules](#authoring-rules)

---

## Overview

Every README.md in a Hypersaint repository is simultaneously:

1. **Valid GitHub-flavored markdown** — renders correctly on GitHub, GitLab, etc.
2. **A progressive disclosure document** — parsed by the Hypersaint MCP server into individually
   loadable sections.

The progressive disclosure is implemented via HTML comment markers that are invisible in rendered
markdown but structurally meaningful to the MCP server.

The fundamental principle: an agent should NEVER load the entire README. It loads the brief, decides
what else it needs, and loads only those sections. The README can be arbitrarily comprehensive
because the cost of comprehensiveness is zero when disclosure is progressive.

---

## Marker Syntax

All markers are HTML comments with the `@hs:` prefix:

```
<!-- @hs:DIRECTIVE [arguments] -->
content
<!-- @/hs:DIRECTIVE -->
```

Markers are always paired (opening + closing) except for self-closing markers:

```
<!-- @hs:DIRECTIVE [arguments] /-->
```

### Escaping

Content within markers is standard markdown. No special escaping is needed. The MCP server extracts
raw content between markers and returns it as-is.

### Nesting

Markers can be nested. A section can contain sub-sections. A FAQ section contains question markers,
each containing an answer marker. The nesting is parsed into a tree by the MCP server.

---

## Section Types

### Brief

The brief is the outermost mandatory section. It is always returned by the MCP server when a
directory is queried without specifying a section. It is the "table of contents" for the atom.

```markdown
<!-- @hs:brief -->
# Login Handler

Handles user authentication via username/password and OAuth2 flows.

**Exports:** `LoginHandler`, `LoginConfig`, `LoginError`

**Files:**
- `login.py` — Core login logic and session creation
- `test_login.py` — Unit and property-based tests
- `fixtures/` — Test credentials and mock OAuth responses

**Dependencies:**
- `src.features.auth.session` — Session creation after successful login
- `src.core.validation.email_format` — Email input validation
- `src.infra.database.connection` — User credential lookup
<!-- @/hs:brief -->
```

The brief MUST include:
- A one-line description of what this atom is
- Exports (public symbols)
- File listing with one-line descriptions
- Dependencies (what this atom imports from)

The brief SHOULD be < 30 lines. It is loaded on every navigation step, so brevity matters.

### Architecture

Deeper structural detail about how the atom works internally.

```markdown
<!-- @hs:section id="architecture" title="Architecture" -->
## Architecture

The login handler implements a two-phase authentication flow:

1. **Credential validation phase:** Validates input format (email via `email_format`, password
   strength via internal `_validate_password_strength`), then checks credentials against the
   database via the `connection` dependency.

2. **Session creation phase:** On successful credential validation, delegates to `session.create()`
   which returns a `SessionToken`. The handler never creates sessions directly — this separation
   ensures session policy changes don't require login code changes.

The OAuth2 flow follows the same two-phase pattern but replaces credential validation with token
exchange via the OAuth provider.

**Data flow:**
```
UserInput → validate_input() → check_credentials() → session.create() → SessionToken
UserInput → validate_input() → exchange_oauth_token() → session.create() → SessionToken
```
<!-- @/hs:section -->
```

### Gotchas / Traps

Things that look wrong but are intentional, or things that look like they should work but don't.
**This is the highest-value section for LLM maintainers** because LLMs pattern-match aggressively
and will "fix" intentional deviations unless warned.

```markdown
<!-- @hs:section id="gotchas" title="Gotchas" -->
## Gotchas

<!-- @hs:item id="gotchas.timing" title="Constant-time comparison is intentional" -->
The password comparison in `_check_password()` uses `hmac.compare_digest()` instead of `==`.
This looks unnecessarily complex but prevents timing attacks. Do NOT simplify this to a direct
string comparison.
<!-- @/hs:item -->

<!-- @hs:item id="gotchas.sleep" title="Sleep after failed login is intentional" -->
The 100ms sleep after a failed login attempt in `_handle_failed_attempt()` is a rate-limiting
measure, not dead code. Do not remove it.
<!-- @/hs:item -->

<!-- @hs:item id="gotchas.no_cache" title="Login responses must never be cached" -->
The `Cache-Control: no-store` header on login responses is set explicitly even though the
framework default already prevents caching. This is defense-in-depth — do not rely on framework
defaults for security-sensitive responses.
<!-- @/hs:item -->

<!-- @/hs:section -->
```

### Contracts / Invariants

What must always be true about this module. Loaded per-component so the agent only sees the
contracts relevant to what it is modifying.

```markdown
<!-- @hs:section id="contracts" title="Contracts" -->
## Contracts

<!-- @hs:item id="contracts.login_handler" title="LoginHandler contracts" -->
**Preconditions:**
- `email` parameter must be a valid email string (enforced by Pydantic at the boundary)
- `password` parameter must be non-empty (enforced by Pydantic at the boundary)

**Postconditions:**
- On success: returns a `SessionToken` with `expires_at` > `now()`
- On failure: returns a `LoginError` with a specific error code. NEVER returns a raw exception.

**Invariants:**
- `LoginHandler` never stores passwords in memory beyond the scope of a single `login()` call.
- `LoginHandler` never logs the password value, even at DEBUG level.
- Failed login attempts always take the same wall-clock time as successful ones (± 10ms) to
  prevent timing attacks.
<!-- @/hs:item -->

<!-- @hs:item id="contracts.login_config" title="LoginConfig contracts" -->
**Invariants:**
- `max_attempts` is always > 0 and <= 100.
- `lockout_duration_seconds` is always > 0.
- These constraints are enforced by Pydantic validators at config load time.
<!-- @/hs:item -->

<!-- @/hs:section -->
```

### Related Atoms

Which other modules interact with this one and how — not just dependency declarations (those are
in index.toml) but the semantic relationship.

```markdown
<!-- @hs:section id="related" title="Related Atoms" -->
## Related Atoms

<!-- @hs:item id="related.session" title="Session relationship" -->
**`src.features.auth.session`** — This atom creates sessions after successful login. The
relationship is strictly one-directional: login calls `session.create()`, session never calls
back into login. If session creation semantics change, the login handler may need to update
its error handling for new session creation failure modes.
<!-- @/hs:item -->

<!-- @hs:item id="related.notifications" title="Notifications relationship" -->
**`src.features.notifications.dispatch`** — Login emits a `LoginEvent` that the notification
dispatcher consumes asynchronously. Login does not depend on notifications — it fires the event
and forgets. If the event schema changes, both atoms must be updated.
<!-- @/hs:item -->

<!-- @/hs:section -->
```

### Examples / Usage

Canonical usage snippets showing how the public API is meant to be called. Loadable per-API so
the agent only sees examples for what it is working with.

```markdown
<!-- @hs:section id="examples" title="Examples" -->
## Examples

<!-- @hs:item id="examples.login_handler" title="LoginHandler usage" -->
```python
from src.features.auth.login.login import LoginHandler, LoginConfig

config = LoginConfig(
    max_attempts=5,
    lockout_duration_seconds=300,
)
handler = LoginHandler(config=config, db=db_connection, session_factory=session_factory)

result = handler.login(email="user@example.com", password="correct-password")
match result:
    case SessionToken() as token:
        print(f"Login successful, expires at {token.expires_at}")
    case LoginError() as error:
        print(f"Login failed: {error.code}")
```
<!-- @/hs:item -->

<!-- @hs:item id="examples.oauth_login" title="OAuth2 login usage" -->
```python
result = handler.login_oauth(
    provider="google",
    authorization_code="abc123",
    redirect_uri="https://app.example.com/callback",
)
```
<!-- @/hs:item -->

<!-- @/hs:section -->
```

### Changelog / Decision Log

Curated record of why things changed. Not git history — semantic decisions.

```markdown
<!-- @hs:section id="changelog" title="Changelog" -->
## Changelog

<!-- @hs:item id="changelog.v3_sync" title="v3: Switched from async to sync" -->
**v3 (2025-11-15):** Switched `login()` from async to sync. Reason: the downstream session
store (Redis) was replaced with an in-process SQLite store, eliminating the need for async IO.
The async version introduced unnecessary complexity (cancellation handling, timeout management)
for what is now a synchronous operation. Do not re-introduce async without a genuine async
dependency.
<!-- @/hs:item -->

<!-- @hs:item id="changelog.v2_timing" title="v2: Added constant-time comparison" -->
**v2 (2025-09-01):** Added constant-time password comparison and fixed-duration login attempts.
Reason: security audit identified timing side-channel. See gotchas section for details on why
this must not be simplified.
<!-- @/hs:item -->

<!-- @/hs:section -->
```

### FAQ

Questions with individually loadable answers. The MCP server returns questions as a numbered
list. The agent identifies which question is relevant and requests only that answer.

```markdown
<!-- @hs:section id="faq" title="FAQ" -->
## FAQ

<!-- @hs:faq id="1" question="Why does login() return a Result type instead of raising exceptions?" -->
Python idiom favors exceptions, but this module is on a critical security path. A Result type
makes error handling explicit at every call site — the caller cannot accidentally ignore a login
failure by forgetting a try/except. The `LoginError` type carries structured error codes that
enable programmatic handling (e.g., `ACCOUNT_LOCKED` triggers a different UI flow than
`INVALID_CREDENTIALS`). Switching to exceptions would require auditing every call site to ensure
proper handling.
<!-- @/hs:faq -->

<!-- @hs:faq id="2" question="Why is there a 100ms sleep after failed login?" -->
Rate-limiting against brute force attacks. The sleep ensures that an attacker cannot determine
whether a failure was due to an invalid email (user doesn't exist) vs. invalid password (user
exists but password is wrong) by measuring response time. Combined with the constant-time
comparison (see gotchas), this makes all failed logins indistinguishable from the attacker's
perspective.
<!-- @/hs:faq -->

<!-- @hs:faq id="3" question="Why was a type: ignore set at line 47 in login.py?" -->
Line 47 calls `session.create()` which returns `SessionToken | None`. Pyright strict mode flags
the `None` case as unhandled. However, `session.create()` only returns `None` when the session
store is in read-only mode, which is checked and prevented by an assertion at handler
initialization (see contracts). The type: ignore is justified because the `None` path is
structurally unreachable after initialization. Removing the ignore would require either an
unnecessary runtime check or a protocol change in the session module.
<!-- @/hs:faq -->

<!-- @/hs:section -->
```

---

## Disclosure Levels

The MCP server processes requests at these disclosure levels:

| Level | What Is Returned | When to Use |
|-------|-----------------|-------------|
| `brief` | Brief section only | Navigation, discovery, understanding what an atom is |
| `section` | A specific named section | The agent needs architecture, gotchas, contracts, etc. |
| `item` | A specific item within a section | The agent needs one contract, one example, one changelog entry |
| `faq_list` | All FAQ questions (no answers) | The agent needs to find which FAQ is relevant |
| `faq` | A specific FAQ answer by ID | The agent found the relevant question |
| `integrity` | The integrity hash block | CI verification, or agent verifying after modification |
| `full` | The entire README | Rare — only when the agent needs everything (e.g., rewriting the README) |

---

## Sub-Sections

Sections contain items. Items are the finest granularity of disclosure. The `id` attribute
provides a stable reference path:

```
readme("/src/features/auth/login", section="contracts")           → all contracts
readme("/src/features/auth/login", item="contracts.login_handler") → one contract
readme("/src/features/auth/login", section="examples")             → all examples
readme("/src/features/auth/login", item="examples.oauth_login")    → one example
readme("/src/features/auth/login", section="faq")                  → question list only
readme("/src/features/auth/login", faq="2")                        → answer to question 2
```

Items can be further nested if needed (e.g., a contract item containing sub-items for
preconditions, postconditions, invariants). The MCP server handles arbitrary nesting depth.

---

## Integrity Block

The integrity block is a special section that contains SHA-256 hashes of every file in the
directory (excluding README.md itself).

```markdown
<!-- @hs:integrity -->
## Integrity

| File | SHA-256 |
|------|---------|
| index.toml | a1b2c3d4e5f6... |
| login.py | f6e5d4c3b2a1... |
| test_login.py | 1a2b3c4d5e6f... |
| fixtures/sample_input.json | 6f5e4d3c2b1a... |
<!-- @/hs:integrity -->
```

Rules:
- Hashes cover every file and directory in the same directory as the README.md.
- `README.md` itself is excluded (it cannot hash itself).
- `index.toml` IS included (cross-validation: README hashes index.toml, index.toml hashes README).
- Subdirectories are hashed as the SHA-256 of their own `index.toml` content. This creates a
  Merkle-like chain — if any file in a subdirectory changes, the subdirectory's index.toml hash
  changes, which changes the parent's integrity block.
- The hash is of the file's raw bytes, hex-encoded, lowercase.
- Entries are sorted alphabetically by file path for deterministic output.

---

## Full Example

A complete README.md for a login handler atom:

```markdown
<!-- @hs:brief -->
# Login Handler

Handles user authentication via username/password and OAuth2 flows.

**Exports:** `LoginHandler`, `LoginConfig`, `LoginError`

**Files:**
- `login.py` — Core login logic and session creation
- `test_login.py` — Unit and property-based tests
- `fixtures/` — Test credentials and mock OAuth responses

**Dependencies:**
- `src.features.auth.session` — Session creation after successful login
- `src.core.validation.email_format` — Email input validation
- `src.infra.database.connection` — User credential lookup
<!-- @/hs:brief -->

<!-- @hs:section id="architecture" title="Architecture" -->
## Architecture

[Architecture content here]
<!-- @/hs:section -->

<!-- @hs:section id="gotchas" title="Gotchas" -->
## Gotchas

<!-- @hs:item id="gotchas.timing" title="Constant-time comparison is intentional" -->
[Gotcha content here]
<!-- @/hs:item -->

<!-- @/hs:section -->

<!-- @hs:section id="contracts" title="Contracts" -->
## Contracts

<!-- @hs:item id="contracts.login_handler" title="LoginHandler contracts" -->
[Contract content here]
<!-- @/hs:item -->

<!-- @/hs:section -->

<!-- @hs:section id="related" title="Related Atoms" -->
## Related Atoms

<!-- @hs:item id="related.session" title="Session relationship" -->
[Related content here]
<!-- @/hs:item -->

<!-- @/hs:section -->

<!-- @hs:section id="examples" title="Examples" -->
## Examples

<!-- @hs:item id="examples.login_handler" title="LoginHandler usage" -->
[Example content here]
<!-- @/hs:item -->

<!-- @/hs:section -->

<!-- @hs:section id="changelog" title="Changelog" -->
## Changelog

<!-- @hs:item id="changelog.v3_sync" title="v3: Switched from async to sync" -->
[Changelog content here]
<!-- @/hs:item -->

<!-- @/hs:section -->

<!-- @hs:section id="faq" title="FAQ" -->
## FAQ

<!-- @hs:faq id="1" question="Why does login() return a Result type instead of raising exceptions?" -->
[Answer content here]
<!-- @/hs:faq -->

<!-- @/hs:section -->

<!-- @hs:integrity -->
## Integrity

| File | SHA-256 |
|------|---------|
| index.toml | a1b2c3d4e5f6... |
| login.py | f6e5d4c3b2a1... |
| test_login.py | 1a2b3c4d5e6f... |
| fixtures/sample_input.json | 6f5e4d3c2b1a... |
<!-- @/hs:integrity -->
```

---

## Rendering Behavior

### On GitHub / GitLab

HTML comments are invisible. The README renders as a normal markdown document with all sections
visible. This is by design — when browsing on GitHub, you see everything. Progressive disclosure
is an agent optimization, not a human optimization.

### Via MCP Server

The MCP server parses the markers and serves sections individually. The agent never receives the
full document unless it explicitly requests `level="full"`.

### In Plain Editors

The markers are visible as HTML comments. They are designed to be human-readable even in raw
form — a developer editing the README can see the structure.

---

## Authoring Rules

1. **Brief is mandatory.** Every README.md must have a `<!-- @hs:brief -->` section.
2. **Integrity is mandatory.** Every README.md must have a `<!-- @hs:integrity -->` section.
3. **All other sections are optional** but strongly encouraged. At minimum, atoms with non-trivial
   logic should have: architecture, contracts, and examples.
4. **IDs are stable.** Once an item has an ID, that ID does not change (even if the content changes).
   Other atoms may reference items by ID in their own documentation. Changing an ID is a breaking
   change to the documentation API.
5. **IDs use dot-separated paths.** `contracts.login_handler`, `examples.oauth_login`,
   `gotchas.timing`. The prefix matches the section ID.
6. **FAQ question text should be self-contained.** An agent reading just the question (without the
   answer) should understand what the question is asking and be able to decide if it is relevant
   to the current task.
7. **Updating a file requires updating integrity hashes.** This is enforced by CI. The agent
   must recompute hashes after any file modification. Use `scripts/readme_hooks.py` to automate.
8. **README updates are part of the change.** If you modify a file in an atom, updating the
   README's integrity hashes (and any content sections affected by the change) is part of the
   same operation. An incomplete change is one that modifies code but not manifests.
