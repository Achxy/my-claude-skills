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
- `gh-23: add database migration for user roles (#30)`
- `gh-142579: avoid divmod crash on malformed _pylong.int (#435)`
- `gh-18421: reject invalid UTF-8 in marshal string loader (#19012)`

**Rules:**
- Issue identifier comes FIRST
- PR number `(#pr)` MUST be appended to all commits that land on main — this is the final commit message after merge, not optional
- During development on a feature branch, commits may omit `(#pr)` since the PR does not exist yet. The PR number is added at merge time (squash merge auto-appends it; for rebase merge, amend the commit message before merging)
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
| Inline codeblocks | Use backtick-wrapped codeblocks for filenames, flags, identifiers, and tool names in commit messages. See below. |

## Inline Codeblock Usage

**Aggressively use inline codeblocks** (backtick wrapping) in commit messages, issue titles, PR titles, and any public-facing text for:

| What to wrap | Example |
|-------------|---------|
| Filenames and extensions | `` `README.md` ``, `` `.gitignore` ``, `` `pyproject.toml` `` |
| CLI flags and options | `` `--body-file` ``, `` `--force-with-lease` ``, `` `--assignee` `` |
| Directory paths | `` `plugins/` ``, `` `src/auth/` ``, `` `.claude/` `` |
| Function/class/variable names | `` `export_session()` ``, `` `ConfigSnapshot` `` |
| Plugin/tool/package names | `` `ccgraft` ``, `` `gh-sdlc` ``, `` `watchdog` `` |
| Config keys and values | `` `SINGLE_SELECT` ``, `` `settings.json` `` |

**Do NOT wrap:**
- Generic English words that happen to also be technical terms (e.g., "session", "project", "branch" when used in plain prose)
- Issue/PR numbers (`#42`, not `` `#42` ``)

**Examples:**
- `gh-37: use `--body-file` for all issue and PR body content (#38)` — flag wrapped
- `gh-42: add `README.md` for `gh-sdlc` plugin (#44)` — filename and plugin name wrapped
- `docs: add MIT license and `.gitignore` (#5)` — filename wrapped
- `gh-23: migrate `gh-sdlc` skills to `plugins/` directory (#30)` — plugin name and directory wrapped

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
