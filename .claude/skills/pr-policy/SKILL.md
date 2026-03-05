---
name: pr-policy
description: "Pull request standards and merge strategies (part of gh-sdlc). Provides formatting rules for PRs — only applies when PRs are actually being created as part of the /gh-sdlc workflow. Does NOT auto-activate on its own."
---

# Pull Request Policy

## Core Principle

**Pull requests are the unit of code integration. Every PR represents atomic, reviewable work that advances a single issue.**

## Mandatory PR Requirements

- [ ] Reference exactly one repository issue (except emergency hotfixes)
- [ ] Contain atomic, focused changes
- [ ] Pass all CI checks before review request
- [ ] Include tests for behavioral changes
- [ ] Update documentation when interface changes
- [ ] Maintain linear, clean commit history
- [ ] Apply relevant labels (use existing labels; only create new ones when no existing label fits)
- [ ] Add to the active GitHub Project board
- [ ] Set milestone matching the issue's milestone
- [ ] Assign the user as reviewer (unless user explicitly opted out)

## PR Title Format

```
[#issue] Component: Imperative description
```

**Examples:**
- `[#6] Project: Initialize uv with discord.py dependencies`
- `[#8] Commands: Implement command registration system`
- `[#15] Auth: Add OAuth2 token refresh logic`

**Hotfix format (no issue):**
```
hotfix: Critical issue description
```

## PR Creation Command

When creating a PR, apply all metadata in one command:

```bash
gh pr create \
  --title "[#issue] Component: Imperative description" \
  --body "..." \
  --label "existing-label" \
  --project "Project Name" \
  --milestone "vX.Y" \
  --reviewer "@me" \
  --assignee "@me"
```

**Label rules:**
- Use existing repository labels; rely on context to pick the right ones
- Only create a new label when NO existing label is relevant (this should be rare)
- Prefer specific labels over generic ones

**Reviewer/assignee rules:**
- ALWAYS assign the user as assignee (`--assignee "@me"`) unless user explicitly opted out
- Attempt to add user as reviewer (`--reviewer <username>`) — note: `@me` is not supported for `--reviewer`, use the actual username. GitHub may reject self-review requests on some plans; this is acceptable.

## PR Description Template

```markdown
## Changes
Brief technical summary of implementation approach.

## Issue Reference
Closes #issue-number

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests pass
- [ ] Manual testing completed

## Checklist
- [ ] Code follows project style guide
- [ ] Documentation updated
- [ ] No debugging artifacts
- [ ] Commit history is clean
- [ ] Self-reviewed diff

## Reviewer Notes
Context for architectural decisions and tradeoffs.
```

## Checkbox Management

**Check boxes as work completes.** After each task in a checklist is done, update the PR body to mark it `[x]`. Use `gh pr edit` to update:

```bash
# Update PR body with checked boxes
gh pr edit <number> --body "$(updated body with [x] marks)"
```

**Rules:**
- Check a box ONLY when its condition is verifiably met
- If a checkbox CANNOT be satisfied (e.g., no tests applicable), report to the user and document why in Reviewer Notes
- Never leave stale unchecked boxes on a merged PR without explanation

## Merge Strategies

### Default: Squash and Merge

Use for:
- Feature branches with messy history
- Multiple WIP commits during development
- PRs from external contributors
- Single-issue, single-concept PRs

**Squash commit message format:**
```
[#issue] Component: Description (#pr)

- Key change 1
- Key change 2
- Key change 3

Co-authored-by: Reviewer Name <email>
```

### When: Rebase and Merge

Use ONLY when:
- PR has intentionally structured commit history
- Each commit represents a distinct logical step
- Commits are already clean and atomic
- Preserving granular history adds value

**Requirements:**
- Each commit passes tests independently
- Commit messages follow format guide
- No "fix typo" or "address review" commits
- Linear history without merge commits

### Never: Merge Commit

**Prohibited.** Creates non-linear history and pollutes git log.

**Exception:** Merging long-lived release branches back to main.

## Branch Strategy

### Naming Convention

| Type | Pattern | Example |
|------|---------|---------|
| Feature | `feature/issue-number-description` | `feature/23-role-permissions` |
| Child feature | `feature/parent/child-description` | `feature/1/6-uv-setup` |
| Bugfix | `bugfix/issue-number-description` | `bugfix/56-null-pointer` |
| Hotfix | `hotfix/description` | `hotfix/redis-connection-leak` |

### Branch Lifecycle

1. Create branch from `main`
2. Implement changes
3. Push and open PR
4. Review feedback loop (address and force push cleaned history)
5. Squash merge to `main`
6. Delete branch

### Hierarchical Branches

For parent issue #1 with children #2, #3:
```
main
├── feature/1-parent-issue
    ├── feature/1/2-child-issue-one
    └── feature/1/3-child-issue-two
```

**Merge order:** Children → Parent → Main

## History Rewriting

### Force Push: Encouraged BEFORE Merge

Acceptable scenarios:
- Squashing "fix review comments" commits
- Reordering commits logically
- Splitting large commits into atomic units
- Amending commit messages for clarity
- Rebasing onto updated main

```bash
# Interactive rebase to clean last 5 commits
git rebase -i HEAD~5

# Rebase onto latest main
git fetch origin main
git rebase origin/main

# Force push cleaned history
git push --force-with-lease
```

**After PR approval:** No force pushes. Use additional commits.

### Interactive Rebase Workflow

Standard cleanup before marking PR ready:

| Operation | Usage |
|-----------|-------|
| `pick` | Keep commit as-is |
| `reword` | Change commit message |
| `edit` | Modify commit content |
| `squash` | Combine with previous, keep both messages |
| `fixup` | Combine with previous, discard message |
| `drop` | Remove commit entirely |

### Partial Staging

```bash
git add -p file.py
```

Choose hunks that belong together for focused, atomic commits.

## Size Guidelines

| Lines Changed | Recommendation |
|---------------|---------------|
| < 200 | Ideal |
| 200-500 | Acceptable |
| 500-1000 | Consider splitting |
| > 1000 | Must split |

**Exceptions:** Generated code, mechanical refactors, initial scaffolding, documentation overhauls.

## Review Process

### Self-Review Checklist (Before Requesting Review)

- [ ] Rebased onto latest main
- [ ] All commits follow message format
- [ ] No WIP, fixup, or temporary commits
- [ ] Each commit compiles and passes tests
- [ ] Diff contains only relevant changes
- [ ] No commented-out code or debug statements
- [ ] Documentation updated

### Reviewer Responsibilities

Verify: code correctness, edge case handling, test coverage, performance implications, security considerations, API design coherence, commit message quality.

### Feedback Resolution

**Small changes** (typos, minor logic):
```bash
git commit --fixup=target-commit-hash
```

**Substantial changes** (architectural):
```bash
git commit -m "gh-23: refactor permission cache invalidation"
```

**Before merge**, squash all fixups:
```bash
git rebase -i --autosquash origin/main
git push --force-with-lease
```

## Conflict Resolution

```bash
git fetch origin main
git rebase origin/main
# Resolve conflicts in files
git add resolved-file.py
git rebase --continue
git push --force-with-lease
```

**Never** merge main into feature branch. Always rebase.

## Emergency Procedures

### Hotfix Process
1. Create `hotfix/` branch from main
2. Implement minimal fix
3. Open PR with `hotfix:` prefix
4. Expedited review → squash merge immediately
5. Backport to affected release branches

### Reverting
```bash
git revert <commit-hash>
```

**Revert PR format:**
```
Revert "[#23] Auth: Add OAuth2 support"

This reverts commit a1b2c3d due to [reason].
Root cause under investigation in #45.
```

## Draft PR Workflow

Use draft PRs for:
- Work in progress requiring early feedback
- Demonstrating approach before full implementation
- CI validation before review request

Convert to ready when: all criteria met, CI passes, history cleaned, self-review complete.

## CI/CD Requirements

- Linting passes
- Unit tests (100% of new code covered)
- Integration tests pass
- Security scans clean
- Build verification succeeds
- Documentation builds
