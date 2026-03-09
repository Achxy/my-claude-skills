# Hypersaint Philosophy

## Table of Contents

1. [The Foundational Axiom](#the-foundational-axiom)
2. [Tool Selection Doctrine](#tool-selection-doctrine)
3. [Code-Level Strictness](#code-level-strictness)
4. [Dependency Philosophy](#dependency-philosophy)
5. [Security Posture](#security-posture)
6. [Infrastructure as Code](#infrastructure-as-code)
7. [The Feedback Loop](#the-feedback-loop)
8. [What Hypersaint Is Not](#what-hypersaint-is-not)

---

## The Foundational Axiom

An LLM's time is free. Tedium has zero cost. Therefore, every trade-off that humans historically
resolved in favor of "good enough" or "pragmatic" gets resolved instead in favor of maximum
correctness, maximum explicitness, and maximum strictness. Developer experience is not a concern.
Shipping speed is not a concern. The only concern is that the codebase is so rigorously correct,
so self-describing, and so tightly constrained that failure becomes structurally difficult rather
than behaviorally avoided.

A new LLM agent — dropped in cold, with no conversation history, reading a single file — should be
able to understand that file completely, modify it correctly, and have the toolchain catch any
mistake before it propagates.

The codebase is the specification. The specification is the codebase. There is no gap between
intent and implementation because every intent is encoded as a type, a contract, a test, a
validation, or an assertion. Ambiguity is a defect.

---

## Tool Selection Doctrine

When multiple tools exist for a job, Hypersaint selects by the following hierarchy. These criteria
are ordered by priority — a tool that satisfies criterion 1 beats one that satisfies only 2-4.

### 1. Strictness by Default

The tool that ships with the harshest defaults wins. A tool you have to configure *down* from
strictness is preferred over one you configure *up* toward it. If two tools are equal in strictness,
the one with fewer configuration options wins — fewer knobs means fewer opportunities for the agent
to weaken the contract.

### 2. Unification

One tool that replaces three is preferred. Fewer moving parts, fewer config files, fewer sources of
truth, fewer things to version and keep in sync. A single tool that lints, formats, and sorts imports
is superior to three tools that do those things separately — even if each individual tool is slightly
better at its narrow job.

### 3. Modernity

The tool built with knowledge of its predecessors' mistakes, written in a fast compiled language,
designed for today's workflows. Rust-based tooling over legacy Python-based tooling. This is not
novelty bias — it is a recognition that newer tools encode lessons from the failures of older ones.

### 4. Enforcement over Convention

A tool that makes the wrong thing a hard error is preferred over one that makes the wrong thing a
warning. A tool that makes the wrong thing a warning is preferred over one that relies on
documentation. If it can be a type error, it must not be a runtime error. If it can be a lint error,
it must not be a code review comment.

### Concrete Examples

These examples illustrate the pattern. The agent must extrapolate to any domain — the specific
tools change over time; the selection principle does not.

| Domain | Hypersaint Choice | Over | Why |
|--------|------------------|------|-----|
| Python linting + formatting | Ruff | flake8+isort+black | Unified, fast, strict defaults |
| Python type checking | Pyright (strict mode) | mypy, pyflakes | Stricter, faster, better inference |
| JS/TS linting + formatting | Biome | ESLint+Prettier | Unified, fast, strict defaults |
| JS/TS runtime | Bun | Node+npm | Unified (runtime+pm+bundler), faster |
| Static typing | TypeScript | JavaScript | Enforcement over convention |
| Systems language | Rust | C++ | Memory safety by default, stricter compiler |
| Desktop apps | Tauri | Electron | Smaller, more secure, Rust core |
| Mail server | Stalwart | Dovecot+Postfix | Unified, modern, Rust |
| Dev environment | Nix flakes | Manual install / Homebrew | Reproducible, declarative, versioned |
| IaC | Terraform/Pulumi | Manual cloud console | Versioned, reviewable, reproducible |
| Container base | Distroless/scratch | Ubuntu/Alpine | Minimal attack surface |

When encountering a domain not listed here, apply the four criteria in order. If uncertain between
two tools that seem equivalent, **ask the user** — Hypersaint is opinionated, but the user's
context (existing team familiarity, deployment constraints) can override tool selection when there
is genuine parity.

---

## Code-Level Strictness

Every configurable dial in the language and its toolchain gets turned to its strictest defensible
setting. What follows are principles with examples — not an exhaustive list. The agent must
extrapolate the underlying principle to any language.

### Explicit Shape Declaration

Every class, struct, or data type declares its own shape explicitly in the file where it is defined.

- **Python:** Every class defines `__slots__`. This forces explicit attribute declaration, prevents
  typo-based silent attribute creation, reduces memory usage, and critically — tells any agent
  reading the file exactly what attributes exist without chasing inheritance.
- **TypeScript:** Every interface is explicit. No `any`, no implicit index signatures, no `Record`
  where a proper interface belongs.
- **Rust:** Structs derive only what they need. No blanket `#[derive(Clone, Debug, Default)]` unless
  every trait is actually used.

### Namespace Hygiene

Nothing leaks into a namespace by accident. The public surface of every module is a conscious,
documented decision.

- **Python:** Every module declares `__all__`. Every package's `__init__.py` declares `__all__`.
  Every re-export is intentional. `from module import *` in consuming code is acceptable *only*
  because `__all__` guarantees it imports exactly what was intended.
- **TypeScript:** Explicit `export` on every public symbol. No default exports (they create naming
  ambiguity). Barrel files (`index.ts`) declare explicit re-exports.
- **Rust:** `pub(crate)` over `pub` where full public visibility isn't needed. Explicit `pub use`
  re-exports in `mod.rs` / `lib.rs`.

### Exhaustive Static Typing

The strictest mode the type checker supports is always enabled.

- **Python:** Pyright in strict mode (`"typeCheckingMode": "strict"`). Every function has full
  parameter and return type annotations. No `Any` unless interfacing with an untyped external
  library — and then, the `Any` is immediately narrowed at the boundary via a typed wrapper.
  No `# type: ignore` without a specific error code and a comment explaining why. Every
  `# type: ignore[specific-code]` is tracked as technical debt.
- **TypeScript:** `strict: true` plus: `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`,
  `noPropertyAccessFromIndexSignature`, `noFallthroughCasesInSwitch`, `forceConsistentCasingInFileNames`.
  No `as any`. No `@ts-ignore` — use `@ts-expect-error` with explanation if absolutely necessary.
- **Rust:** `#![deny(clippy::all, clippy::pedantic)]`. Address or explicitly allow every warning
  with justification.

### Runtime Validation at Trust Boundaries

Static types are a compile-time promise. Runtime validation is the proof. Data crossing a trust
boundary — user input, API responses, file reads, environment variables, database results,
deserialized payloads — is validated at the boundary with a schema.

- **Python:** Pydantic models for structured data. beartype decorators for function signatures
  where Pydantic is too heavy. `pydantic.SecretStr` for sensitive values.
- **TypeScript:** Zod schemas at every trust boundary. Parse, don't validate — `z.parse()` returns
  typed data, not a boolean.
- **Rust:** `serde` with `#[serde(deny_unknown_fields)]`. Newtype wrappers for validated primitives
  (e.g., `EmailAddress(String)` that validates on construction).

### Error Handling

Prefer explicit error-as-value patterns over thrown exceptions where the language supports it.

- **Rust:** `Result<T, E>` everywhere. `?` operator for propagation. Custom error types via
  `thiserror`. Never `unwrap()` in library code — only in tests or with a comment explaining why
  the panic is logically impossible.
- **TypeScript:** Discriminated union result types or a `Result<T, E>` library. `try/catch` only
  at the outermost boundary (HTTP handler, CLI entry point). Inner code returns errors as values.
- **Python:** Exceptions are idiomatic, so: never bare `except`. Always catch the narrowest
  exception type. Document every exception a function can raise in its docstring. Consider
  `returns` library for Result-type patterns in critical paths.

### Documentation as Contract

Every public symbol has a docstring or doc comment. This is not optional and it is not decoration.
The docstring is the contract that tells the next agent what this unit does, what it accepts, what
it returns, what it raises, and what invariants it maintains — without reading the implementation.

Format:
- **Python:** Google-style docstrings. `Args:`, `Returns:`, `Raises:` sections mandatory for any
  function with parameters. One-line summary mandatory for everything.
- **TypeScript:** TSDoc (`/** */`). `@param`, `@returns`, `@throws` tags mandatory.
- **Rust:** `///` doc comments. Examples in doc comments that compile and run via `cargo test`.

### Testing

Tests are mandatory, layered, and co-located with the code they test.

- **Unit tests:** Every public function has at least one. Test the contract (inputs → outputs),
  not the implementation.
- **Property-based tests:** Every public function with a meaningful invariant has a property test.
  Hypothesis (Python), fast-check (TypeScript), proptest (Rust). The property test expresses the
  invariant; unit tests are specific instances of it.
- **Contracts and invariants:** Assert preconditions at function entry. Assert postconditions before
  return. These are not "defensive programming" — they are executable specifications that catch
  violations at the earliest possible moment.

### Formatting

Formatting is never manual and never debatable. The tool decides. The agent runs the formatter.

- **Python:** Ruff format. Line length configured once in `pyproject.toml`. Never overridden.
- **TypeScript:** Biome format. Configured once in `biome.json`.
- **Rust:** `rustfmt` with `edition = 2021`. No overrides.

---

## Dependency Philosophy

### Use Dependencies Aggressively — But Only Proven Ones

A "proven" dependency satisfies ALL of:
- **High adoption:** Significant GitHub stars, download counts, production usage.
- **Active maintenance:** Recent commits, responsive to issues, regular releases.
- **Trusted provenance:** Backed by a known organization (Microsoft, Google, Mozilla, etc.) or a
  well-known maintainer with a track record.
- **Type-safe:** Ships with types (TypeScript declarations, py.typed marker, etc.). An untyped
  dependency cannot satisfy Hypersaint's static typing requirements.

If a battle-tested library exists, use it. Do not rewrite what the ecosystem has already solved
and hardened through years of production use and security audits.

### Author the Least Code Possible

The safest code is code you didn't write. Prefer a thin, strictly typed wrapper around a proven
library over a bespoke implementation. The wrapper's job is:

1. Constrain the library's API surface to only the correct usage patterns for your domain.
2. Add type narrowing so that misuse is caught at the type level.
3. Add runtime validation at the boundary between your code and the library.
4. Provide a stable internal API so the library can be swapped without touching consumers.

### Minimal but Not Ascetic

This is not a "zero dependency" philosophy. It is a "zero unjustified dependency" philosophy. Every
dependency earns its place by being better, more tested, and more maintained than what you would
write. When a dependency doesn't exist or isn't trustworthy for a task, then and only then do you
author it — to the same standard as everything else in the codebase.

When authoring is necessary, prefer writing the smallest possible utility and placing it at a
semantically named shared path (see Modularity) where other atoms can import it.

---

## Security Posture

Security in Hypersaint is not a feature — it is a structural property. The codebase is designed
so that insecure code is *inexpressible*, not merely discouraged.

### Never Author Security-Sensitive Code

Authentication, cryptography, session management, token handling, CSRF protection, input
sanitization, password hashing, key derivation — these are always delegated to established
libraries. The agent NEVER writes custom implementations of any security-critical algorithm.

### Wrappers Must Make Misuse Impossible

The wrapper around a security library must constrain the API so that:
- The insecure configuration is a type error, not a runtime option.
- Default parameters are the secure choice. There is no "easy insecure mode."
- Sensitive values use dedicated types (`SecretStr`, `SecretBytes`) that prevent accidental
  logging or serialization.
- If a user can XSS themselves through your interface, that is a failure — regardless of how
  unlikely or trivial the vector is.

### Trust Boundaries Are Explicit

Every point where data enters the system from an external source is marked as a trust boundary.
Data at trust boundaries is:
1. Validated against a schema (Pydantic, Zod, serde).
2. Sanitized for the context it will be used in (HTML escaping, SQL parameterization, etc.).
3. Typed as "validated" after passing through the boundary — so consuming code can distinguish
   validated from unvalidated data at the type level.

---

## Infrastructure as Code — Full Extent

Nothing is manual. Nothing lives in a dashboard. Nothing depends on "just SSH in and..." or "click
this button in the console." The entire system — from the developer's local shell to production
deployment — is described in versioned, reviewable, reproducible files.

### Development Environment

Nix flakes define the complete development shell. Every tool, every dependency, every version is
pinned and reproducible. A new contributor (human or LLM) runs one command and gets the exact
environment. No "install these six things and hope the versions align."

```
flake.nix           # Pin all dev tools and system dependencies
flake.lock          # Locked dependency graph
.envrc              # direnv integration for automatic shell activation
```

### Infrastructure

Terraform, Pulumi, or equivalent. Cloud resources are code. DNS is code. Secrets management is
code (sealed/encrypted, never plaintext in the repo). If it exists in production, it exists as a
versioned file in the repository.

### CI/CD

Pipelines are code in the repository. The full strictness suite runs on every change:
1. Formatting check (Ruff format / Biome format)
2. Linting (Ruff / Biome lint)
3. Static type checking (Pyright / tsc)
4. Unit tests
5. Property-based tests
6. Security scanning (dependency audit, SAST)
7. Integrity verification (Hypersaint hash checks — see CI Integrity reference)

The LLM's feedback loop depends on this: it makes a change, pushes, and gets machine-readable
pass/fail output it can self-correct from. Every failure message must be specific and actionable.

### Configuration

Application config is typed and validated at startup, not read from loose env vars with string
fallbacks.

- **Python:** Pydantic `BaseSettings` with validators. Missing or malformed config → crash at
  startup with a clear error. Never silently fall back to a default for a required value.
- **TypeScript:** Zod schema parsing `process.env` at startup. Invalid config → thrown error
  with the specific field and expected type.
- **Rust:** Typed config struct deserialized at startup via `serde`. Missing fields → panic with
  field name and expected type.

Environment-specific overrides (dev, staging, prod) are structured files (TOML, JSON), not ad-hoc
env vars. Each override file is validated against the same schema.

### Containerization

- Multi-stage builds. Build stage installs dependencies and compiles. Final stage copies only
  artifacts.
- Minimal final images. Distroless (Google) or scratch where possible. Alpine only if distroless
  is genuinely impractical.
- No shell in production images unless explicitly required and justified.
- Health checks defined in the Dockerfile or compose file, not assumed.
- Non-root user by default. `USER nobody` or equivalent.

---

## The Feedback Loop

All of the above converges on one operational principle: **the LLM self-corrects from
machine-readable toolchain output.**

Every change the agent makes passes through the full strictness suite. If it fails, the error
messages are specific, actionable, and parseable. The agent loops — fix, re-run, fix, re-run —
until the suite passes. Overkill is not in the vocabulary. The cost of running the suite ten
times is zero. The cost of shipping a defect is nonzero.

This is why tool selection matters so much. Fast tools (Ruff: milliseconds, Biome: milliseconds,
Pyright: seconds) give the agent tight feedback loops. Slow legacy tools (pylint: many seconds,
ESLint: seconds per file) make the loop expensive. Speed is not a developer-experience luxury —
it is an agent-efficiency requirement.

The ideal loop:
1. Agent modifies an atom (one or a few files in one directory).
2. Agent runs the strictness suite on that atom (< 5 seconds).
3. On failure: agent reads the error, modifies, re-runs. Repeat until pass.
4. Agent updates README.md and index.toml for the containing directory.
5. Agent runs integrity check (hash verification).
6. On pass: change is complete. Commit.

---

## What Hypersaint Is Not

**It is not about functional programming purity.** Side effects are fine. Mutation is fine. IO is
fine. What matters is that side effects are explicit, typed, contained, and tested — not that they
don't exist.

**It is not about developer experience.** Verbose? Good. Ceremonial? Good. Requires writing
`__slots__` on every class, `__all__` on every module, docstrings on every function, property tests
for every invariant? Good. The maintainer doesn't get bored or frustrated.

**It is not about shipping fast.** It is about shipping *correctly*. The first version may take
longer. Every version after that is faster because the codebase is so well-constrained that changes
are safe and isolated.

**It is not language-specific.** The examples skew toward Python, TypeScript, and Rust because those
are common LLM-maintained stacks. The philosophy applies to any language. The agent's job is to find
the Hypersaint-aligned tools and patterns for whatever environment it encounters.

**It is not a framework.** Hypersaint is an architecture and a ruleset. It does not impose a
directory naming scheme beyond the structural rules (README.md, index.toml). It does not require
a specific web framework, database, or deployment target. It constrains *how* code is organized
and maintained, not *what* the code does.
