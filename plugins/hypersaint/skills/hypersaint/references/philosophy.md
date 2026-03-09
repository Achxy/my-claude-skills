# Hypersaint Philosophy

## Table of Contents

1. [The Foundational Axiom](#the-foundational-axiom)
2. [The Strictness Axiom](#the-strictness-axiom)
3. [Tool Selection Doctrine](#tool-selection-doctrine)
4. [Code-Level Strictness](#code-level-strictness)
5. [Dependency Philosophy](#dependency-philosophy)
6. [Security Posture](#security-posture)
7. [Infrastructure as Code](#infrastructure-as-code)
8. [The Feedback Loop](#the-feedback-loop)
9. [What Hypersaint Is Not](#what-hypersaint-is-not)

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

### Context Acquisition

When the agent encounters a library, API, or system it doesn't fully understand, it must seek authoritative context via MCP servers, documentation fetch, or reference files before writing code. The agent does not guess. It does not rely on training data that may be stale. It acquires ground-truth context at the moment of need and acts on verified information. This is the enforcement-over-convention principle applied to the agent's own cognition.

---

## The Strictness Axiom

Strictness is not a property of code. It is the system's relationship to ambiguity. Every decision surface in the system — architectural, behavioral, temporal, communicational, observational, operational, security — is governed by explicit, formal constraints that make incorrect states structurally inexpressible. The wrong thing is not discouraged. The wrong thing is not caught by a test. The wrong thing *cannot be expressed* in the first place. Where this ideal is unreachable, the system falls back through a hierarchy: compile-time enforcement, then static analysis, then runtime assertion, then validated convention with automated auditing — in that order, never skipping a level that is achievable.

The following dimensions describe strictness as axes that the agent must apply to whatever system it is building. They are not code-specific — they apply to architecture, infrastructure, process, communication, and everything else.

### Dimension 1: Structural Strictness

The system's architecture enforces separation of concerns at the boundary level, not the convention level. Components cannot reach into each other's internals — not because a style guide says so, but because the architecture makes it structurally impossible.

This means: dependency inversion enforced by the module system, not by developer discipline. Separation of reads and writes into structurally distinct paths where warranted. Domain core isolated from infrastructure at the compile-time level. If a component should not depend on another, the build system or module structure makes the import fail, not a linter warning.

The agent should evaluate every architectural decision against: "Can a future agent violate this boundary by accident?" If yes, the boundary is not strict enough.

### Dimension 2: Behavioral Strictness

Every stateful component has an explicit, finite state machine. States are enumerated. Transitions are enumerated. Invalid transitions are inexpressible in the type system or state definition. The system cannot enter an undefined state because undefined states do not exist in the model.

No undefined behavior, no implementation-defined behavior, no reliance on implicit execution order. Every operation has a defined outcome for every possible input. Every branch is handled. Every match/switch is exhaustive. Every state machine has an explicit error state and explicit transitions into it.

The agent should be able to look at any stateful component and enumerate every possible state and every possible transition without reading the implementation — because the state machine is declared, not emergent.

### Dimension 3: Data Lifecycle Strictness

Data has an explicit lifecycle: it enters through a validated boundary, flows through typed transformations, and exits through a defined output channel. At no point in this lifecycle is data in an ambiguous state — it is either unvalidated (and typed as such), validated (and typed as such, distinctly from unvalidated), or transformed (and typed as the result type).

No global mutable state. No ambient data. No "just grab it from the context." Every piece of data a function uses arrives through its parameters or through explicitly declared, injected dependencies. Side channels do not exist.

Immutability is the default expression of this: a value that has been validated and transformed should not be mutatable, because mutation would potentially invalidate the guarantees that the validation established. Mutable state exists only at explicitly designated mutation points (database writes, cache updates, state machine transitions) and nowhere else.

### Dimension 4: Temporal Strictness

Every operation that can block has an explicit timeout. Every chain of operations has a deadline that propagates through the call chain. No unbounded waits. No "eventually consistent" without explicit convergence bounds and monitoring for convergence failure.

Retry policies are explicit, bounded, and use backoff. No infinite retry loops. No "retry until it works." Every retry policy has a circuit breaker. Every circuit breaker has an explicit half-open strategy.

Ordering constraints are explicit. If operation A must happen before operation B, this is enforced by the type system or the control flow — not by documentation saying "make sure to call A before B." If causal ordering matters, it is encoded in the data flow (A's output is B's input), not in a comment.

### Dimension 5: Communication Strictness

Between components within the system: schema-validated, versioned contracts. No implicit protocol assumptions. No "just send a dict/object and the other side knows what to do." Every message has a schema. Every schema has a version. Breaking changes to schemas are structurally impossible through additive-only evolution or explicit versioned endpoints.

Between the system and external services: the same. Every external API call goes through a typed client with a schema. No raw HTTP calls with string URLs and untyped response parsing. Idempotency keys on every mutating external call. Exactly-once semantics where needed, at-least-once with deduplication elsewhere.

### Dimension 6: Error Domain Completeness

Every possible failure mode is enumerated in the type system. Not "this function can throw" but "these are the exact failure types, each distinct, each carrying the context needed for the caller to make a decision." No catch-all error handlers. No swallowed errors. No error that disappears into a log without the calling code making an explicit decision about it.

The error path is as well-designed as the success path. Error types carry enough context to be actionable. Error propagation is explicit (Result types, typed exceptions, discriminated unions). The agent reading a function's signature knows every way it can fail without reading the implementation.

### Dimension 7: Resource Strictness

Every acquired resource has a defined, deterministic release path. Connections, file handles, locks, memory allocations, temporary files — every acquisition is paired with a release, and the pairing is enforced by the language construct (RAII, context managers, try-with-resources, defer) rather than by developer memory.

Resource limits are explicit and enforced. Maximum connections, maximum memory, maximum open file descriptors, maximum queue depth. Every limit has a defined behavior when reached (reject, backpressure, circuit-break) rather than undefined degradation.

### Dimension 8: Observability Strictness

The system is fully debuggable from its telemetry alone, without reproducing the issue. Every state transition emits a structured, typed event. Every error is recorded with full causal context. Every external interaction is traced with correlation IDs that span the full request lifecycle.

This is not "add logging." This is: the observability layer is a formal model of the system's behavior, and the model is complete. If something happened, it is observable. If it is not observable, the system treats it as if it didn't happen.

Audit trails are append-only and cannot be tampered with by the service that produces them. Security events (authentication, authorization, access to sensitive data) are always logged, always structured, and always shipped to a separate collection system.

### Dimension 9: Operational Strictness

Builds are reproducible: the same input always produces the same output. Builds are hermetic: no network access during build, no reliance on external state. Artifacts are signed. Deployments are verified against expected state, not just "pushed and hoped."

No manual deployment. No hotfix that bypasses the verification pipeline. No "just SSH in and restart it." Every operational action is either automated (IaC, CI/CD) or explicitly forbidden. The system's operational posture is as strict as its code posture.

Infrastructure is immutable where possible: servers are rebuilt, not patched. Containers are replaced, not updated in place. Configuration changes are deployments, not runtime mutations.

### Dimension 10: Security Strictness

Default-deny at every layer. Network perimeter, process permissions, file access, API authorization — everything starts closed and is opened only with explicit justification. Defense in depth: no single security control is the only thing preventing a class of attack.

Credentials are never in plaintext, never in default paths, never in home directories. Dedicated credential storage with access auditing. Rotation automated. Leak detection in CI. Transport encrypted everywhere including internal service-to-service. Certificate pinning where feasible.

The agent never implements security primitives. It wraps proven, audited libraries so tightly that the unsafe usage path does not exist in the API.

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

**Every data structure declares its shape exhaustively at definition time.** No attribute, field, or member may exist at runtime that is not declared in the structure's definition. Dynamic attribute creation, monkey-patching, and implicit field inheritance are prohibited. The structure's definition is the single source of truth for what it contains.

*Examples: Python `__slots__`, TypeScript explicit interfaces with no index signatures, Rust structs with explicit field declarations, Go structs with explicitly typed fields.*

### Namespace Hygiene

**The public surface of every module is an explicit, conscious declaration — not an emergent property of what happens to be defined.** Nothing leaks into a namespace by accident. Every symbol that is accessible from outside the module is intentionally exported. Wildcard imports from consuming code are acceptable only when the exporting module explicitly constrains what the wildcard exposes.

*Examples: Python `__all__` on every module and package, TypeScript explicit named exports with no default exports, Rust `pub(crate)` over `pub` with explicit `pub use` re-exports, Go capitalized identifiers as the sole export mechanism.*

### Exhaustive Static Typing

**The strictest mode the type checker supports is always enabled.** Every function has full parameter and return type annotations. Escape hatches from the type system (untyped casts, type suppression comments, top types used as concrete types) are prohibited except at boundaries with untyped external code — and at those boundaries, the untyped value is immediately narrowed through a typed wrapper. Every type suppression is tracked as technical debt and annotated with a specific error code and justification.

*Examples: Python Pyright strict mode with no bare `Any`, TypeScript `strict: true` plus `noUncheckedIndexedAccess` and `exactOptionalPropertyTypes`, Rust `#![deny(clippy::all, clippy::pedantic)]`, Go `go vet` plus `staticcheck` with all analyzers enabled.*

### Runtime Validation at Trust Boundaries

**Static types are a compile-time promise. Runtime validation is the proof.** Data crossing a trust boundary — user input, API responses, file reads, environment variables, database results, deserialized payloads — is validated at the boundary with a schema that produces a distinctly typed "validated" value. The system distinguishes validated from unvalidated data at the type level. Parse, don't validate: the validation step returns a typed result, not a boolean.

*Examples: Python Pydantic models and `SecretStr`, TypeScript Zod schemas with `z.parse()`, Rust `serde` with `#[serde(deny_unknown_fields)]` and newtype wrappers, Go struct validation tags with explicit error returns.*

### Error Handling

**Every function's failure modes are explicit in its signature or contract.** Prefer error-as-value patterns over thrown/raised exceptions where the language supports it. When exceptions are idiomatic, catch the narrowest type and document every raisable exception. No catch-all handlers. No swallowed errors. Every error carries enough context for the caller to make a decision. The error path receives the same design rigor as the success path.

*Examples: Rust `Result<T, E>` with `thiserror`, TypeScript discriminated union result types, Python narrowly-typed `except` clauses with documented `Raises:` sections, Go multi-return `(value, error)` with explicit error checks.*

### Documentation as Contract

**Every public symbol has a doc comment that constitutes a binding contract.** The documentation declares what the unit does, what it accepts, what it returns, what it raises or returns as errors, and what invariants it maintains — without requiring the reader to examine the implementation. This is not optional and it is not decoration. The doc comment is the specification that enables any agent to use the symbol correctly on first encounter.

*Examples: Python Google-style docstrings with `Args:`, `Returns:`, `Raises:` sections, TypeScript TSDoc with `@param`, `@returns`, `@throws` tags, Rust `///` doc comments with compilable examples, Go package-level and function-level comments per `godoc` convention.*

### Testing

**Tests are mandatory, layered, and co-located with the code they test.** Every public function has at least one unit test verifying its contract (inputs to outputs, not implementation details). Every function with a meaningful invariant has a property-based test that expresses the invariant — unit tests are specific instances of it. Preconditions are asserted at function entry. Postconditions are asserted before return. These assertions are executable specifications, not defensive programming.

*Examples: Python `pytest` with Hypothesis for property tests, TypeScript Vitest with fast-check, Rust built-in `#[test]` with proptest, Go table-driven tests with `testing/quick`.*

### Formatting

**Formatting is never manual and never debatable.** A single formatter is configured once in the project's configuration file and run automatically. No overrides. No per-file exceptions. The tool decides; the agent runs it.

*Examples: Python Ruff format, TypeScript/JavaScript Biome format, Rust `rustfmt`, Go `gofmt`.*

---

## Dependency Philosophy

### Use Dependencies Aggressively — But Only Proven Ones

A "proven" dependency satisfies ALL of:
- **High adoption:** Significant community usage, download counts, production deployment.
- **Active maintenance:** Recent commits, responsive to issues, regular releases.
- **Trusted provenance:** Backed by a known organization or a well-known maintainer with a track record.
- **Type-safe:** Ships with type definitions or type annotations native to the language's type system. An untyped dependency cannot satisfy Hypersaint's static typing requirements.

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
- Sensitive values use dedicated opaque types that prevent accidental logging or serialization.
- If a user can XSS themselves through your interface, that is a failure — regardless of how
  unlikely or trivial the vector is.

*Examples: Python `SecretStr`/`SecretBytes`, Rust `secrecy::Secret<T>`, TypeScript branded types wrapping sensitive strings.*

### Trust Boundaries Are Explicit

Every point where data enters the system from an external source is marked as a trust boundary.
Data at trust boundaries is:
1. Validated against a schema.
2. Sanitized for the context it will be used in (HTML escaping, SQL parameterization, etc.).
3. Typed as "validated" after passing through the boundary — so consuming code can distinguish
   validated from unvalidated data at the type level.

*Examples: Python Pydantic, TypeScript Zod, Rust `serde` with `deny_unknown_fields`, Go struct validation.*

---

## Infrastructure as Code — Full Extent

Nothing is manual. Nothing lives in a dashboard. Nothing depends on "just SSH in and..." or "click
this button in the console." The entire system — from the developer's local shell to production
deployment — is described in versioned, reviewable, reproducible files.

### Development Environment

Declarative environment definitions pin the complete development shell. Every tool, every
dependency, every version is pinned and reproducible. A new contributor (human or LLM) runs one
command and gets the exact environment. No "install these six things and hope the versions align."

*Examples: Nix flakes with `flake.nix` + `flake.lock` + `.envrc` for direnv integration, devcontainers with `devcontainer.json`, Hermit for hermetic per-project tooling.*

### Infrastructure

Declarative infrastructure-as-code tooling. Cloud resources are code. DNS is code. Secrets
management is code (sealed/encrypted, never plaintext in the repo). If it exists in production,
it exists as a versioned file in the repository.

*Examples: Terraform, Pulumi, AWS CDK, Crossplane.*

### CI/CD

Pipelines are code in the repository. The full strictness suite runs on every change:
1. Formatting check
2. Linting
3. Static type checking
4. Unit tests
5. Property-based tests
6. Security scanning (dependency audit, SAST)
7. Integrity verification (Hypersaint hash checks — see CI Integrity reference)

The LLM's feedback loop depends on this: it makes a change, pushes, and gets machine-readable
pass/fail output it can self-correct from. Every failure message must be specific and actionable.

### Configuration

**Application config is typed and validated at startup, not read from loose environment variables with string fallbacks.** Missing or malformed config crashes at startup with a clear error identifying the specific field and expected type. Never silently fall back to a default for a required value. Environment-specific overrides (dev, staging, prod) are structured files validated against the same schema.

*Examples: Python Pydantic `BaseSettings`, TypeScript Zod schema parsing `process.env`, Rust typed config struct via `serde`, Go `envconfig` with struct tags.*

### Containerization

- Multi-stage builds. Build stage installs dependencies and compiles. Final stage copies only
  artifacts.
- Minimal final images. Distroless or scratch where possible. Alpine only if distroless
  is genuinely impractical.
- No shell in production images unless explicitly required and justified.
- Health checks defined in the Dockerfile or compose file, not assumed.
- Non-root user by default.

---

## The Feedback Loop

All of the above converges on one operational principle: **the LLM self-corrects from
machine-readable toolchain output.**

Every change the agent makes passes through the full strictness suite. If it fails, the error
messages are specific, actionable, and parseable. The agent loops — fix, re-run, fix, re-run —
until the suite passes. Overkill is not in the vocabulary. The cost of running the suite ten
times is zero. The cost of shipping a defect is nonzero.

This is why tool selection matters so much. Fast tools give the agent tight feedback loops. Slow
legacy tools make the loop expensive. Speed is not a developer-experience luxury — it is an
agent-efficiency requirement.

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

**It is not about developer experience.** Verbose? Good. Ceremonial? Good. Requires exhaustive
shape declarations on every data structure, explicit export lists on every module, docstrings on
every function, property tests for every invariant? Good. The maintainer doesn't get bored or
frustrated.

**It is not about shipping fast.** It is about shipping *correctly*. The first version may take
longer. Every version after that is faster because the codebase is so well-constrained that changes
are safe and isolated.

**It is not language-specific.** The examples reference specific languages because concreteness aids
understanding. The philosophy applies to any language. The agent's job is to find the
Hypersaint-aligned tools and patterns for whatever environment it encounters.

**It is not a framework.** Hypersaint is an architecture and a ruleset. It does not impose a
directory naming scheme beyond the structural rules (README.md, index.toml). It does not require
a specific web framework, database, or deployment target. It constrains *how* code is organized
and maintained, not *what* the code does.
