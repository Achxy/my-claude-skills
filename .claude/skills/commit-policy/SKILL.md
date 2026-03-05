---
name: commit-policy
description: "Commit message formatting standards (part of gh-sdlc). Provides formatting rules for git commits — only applies when commits are actually being created. Does NOT trigger the full SDLC workflow on its own."
---

# Commit Message Policy

## Philosophy

Keep messages simple by default. Add descriptions only when the change's purpose isn't clear from code inspection alone. If work is tracked in an issue, omit the description — the issue provides context.

**Guiding rule:** Use the simplest format that provides necessary context. Allow problem complexity to dictate message structure.

## Format Selection

### Case 1: Issue-Tracked Changes (Preferred)

```
gh-<issue>: <imperative summary> (#pr)
```

**Examples:**
- `gh-18421: reject invalid UTF-8 in marshal string loader`
- `gh-142579: avoid divmod crash on malformed _pylong.int (#435)`
- `gh-23: add database migration for user roles`

**Rules:**
- Issue identifier comes FIRST
- PR number appended in parentheses when applicable
- Description body is RARELY needed — the issue tracker holds the context

### Case 2: Direct Commits (No Issue)

```
<type>(<scope>): <imperative summary>
```

**Examples:**
- `refactor(parser): eliminate redundant token buffering`
- `fix(auth): handle expired session tokens gracefully`
- `feat(api): add rate limiting middleware`

**Scope** references modules/subsystems (e.g., `parser`, `gc`, `stdlib/asyncio`, `auth`). Omit scope when changes span multiple systems.

## Subject Line Standards

| Rule | Detail |
|------|--------|
| Mood | Imperative ("add", "fix", "remove" — NOT "added", "fixes") |
| Target length | 50 characters |
| Hard limit | 72 characters (optimized for `git log --oneline`) |
| Capitalization | Lowercase after type/scope prefix |
| Punctuation | No trailing period |

## Type Taxonomy

| Type | Purpose |
|------|---------|
| `feat` | New feature |
| `fix` | Bug fix |
| `perf` | Performance improvement |
| `refactor` | Code restructuring (no behavior change) |
| `test` | Test modifications |
| `build` | Build system changes |
| `ci` | CI/CD configuration |
| `docs` | Documentation |
| `chore` | Maintenance/tooling |
| `revert` | Revert previous commit |

## When to Add a Description Body

Include body text ONLY for:
- Non-obvious behavior changes
- Subtle performance characteristics
- Security implications
- Complex bug trigger conditions
- Implementation justification requiring explanation

**Omit descriptions when:**
- Changes are self-explanatory from the diff
- Fully documented in issue tracker
- Adequately explained through code comments

## Body Format (When Required)

```
gh-<issue>: <imperative summary> (#pr)

- Bullet point explaining the "why"
- Another point if needed
- Keep lines under 72 characters
```

Use imperative language in bullets. Focus on WHY, not WHAT (the diff shows what).

## Multi-Commit PR Organization

Order commits logically within a PR:
1. Infrastructure/setup commits
2. Core implementation commits
3. Test commits
4. Documentation commits

**Example PR sequence:**
```
gh-23: add database migration for user roles
gh-23: implement role-based permission system
gh-23: add permission check tests
gh-23: document permission API in README
```

## Fixup Workflow

During development, mark commits for auto-squashing:
```bash
git commit --fixup=<target-hash>
git rebase -i --autosquash origin/main
```

## Enforcement Checklist

Before finalizing any commit:
- [ ] Imperative mood in subject
- [ ] Under 72 characters
- [ ] Issue reference present (if tracked)
- [ ] Correct type prefix (if untracked)
- [ ] Body only if non-obvious
- [ ] No debugging artifacts in message
