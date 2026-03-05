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

PR titles use the same format as commit messages — the issue reference prefix followed by an imperative description:

```
gh-<issue>: <imperative description>
```

**Examples:**
- ``gh-6: initialize `uv` with `discord.py` dependencies``
- ``gh-8: implement command registration system``
- ``gh-15: add OAuth2 token refresh logic``

Use inline codeblocks (backtick wrapping) for filenames, flags, tool/package names, and directory paths in titles. See commit-policy for the full codeblock usage guide.

**Hotfix format (no issue):**
```
hotfix: critical issue description
```

## PR Creation Command

When creating a PR, apply all metadata in one command. **Always use `--body-file`** to pass the PR body — never inline markdown in `--body "..."` because backticks, code blocks, and special characters get mangled by shell interpretation.

```bash
# Write body to temp file (markdown is preserved exactly)
cat > /tmp/pr-body.md <<'EOF'
## Changes
Brief technical summary.

Closes #issue-number

## Testing
- [ ] Tests pass

## Checklist
- [ ] Self-reviewed diff
EOF

gh pr create \
  --title "gh-<issue>: <imperative description>" \
  --body-file /tmp/pr-body.md \
  --label "existing-label" \
  --project "Project Name" \
  --milestone "vX.Y" \
  --reviewer "@me" \
  --assignee "@me"

rm /tmp/pr-body.md
```

**Why `--body-file`?** The `--body` flag passes through shell expansion, which corrupts backticks (`` ` ``), code fences (` ``` `), and `$` in markdown. Writing to a file first with a single-quoted heredoc (`<<'EOF'`) preserves content exactly.

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

**The `Closes #N` line goes directly in the Changes section** — not in a separate heading. This creates the Development sidebar link automatically when the PR targets the default branch, giving a clean linked-issue appearance rather than a verbose "Issue Reference" section.

## PR Project Tracking

PRs are project artifacts just like issues. They should be tracked on the project board with full metadata.

### Adding PR to Project

After creating a PR, add it to the project board and set fields:

```bash
# Add PR to project
PR_URL=$(gh pr view <number> --json url -q .url)
ITEM_ID=$(gh project item-add <project-number> --owner "@me" --url "$PR_URL" --format json --jq '.id')

# Set status to "In Review"
gh project item-edit --id "$ITEM_ID" --field-id "$STATUS_FIELD_ID" --project-id "$PROJECT_ID" \
  --single-select-option-id "$IN_REVIEW_OPTION_ID"
```

### PR Metadata Checklist

Every PR must have:
- **Project**: Added to the active project board
- **Milestone**: Same milestone as its linked issue
- **Labels**: Matching issue labels
- **Development link**: Issue linked in the Development sidebar (see below)
- **Assignee**: The user (`--assignee "@me"`)
- **Reviewer**: The user or designated reviewer

### Development Sidebar Linking

The Development sidebar shows linked issues with a status icon — this is the proper way to associate PRs with issues (not a body section).

**When PR targets the default branch (main):**
Include `Closes #N` in the PR body (inside the Changes section). GitHub automatically creates the Development sidebar link and will auto-close the issue on merge.

**When PR targets a non-default branch (child → parent):**
Closing keywords are **ignored** by GitHub when the PR doesn't target the default branch — no link is created and merging has no effect on issues. Instead, reference the issue with `Part of #N` or `For #N` in the body (no closing keyword). The Development sidebar link must be created manually via the GitHub UI, or accepted as absent for intermediate PRs.

**Supported closing keywords:** `close`, `closes`, `closed`, `fix`, `fixes`, `fixed`, `resolve`, `resolves`, `resolved` (case-insensitive, optional colon).

## Checkbox Management

**Check boxes as work completes.** After each task in a checklist is done, update the issue or PR body to replace `- [ ]` with `- [x]`. This applies to both PR checklists and issue acceptance criteria.

### How to tick checkboxes

Fetch the current body, apply sed replacements, write to a temp file, and update via `--body-file`:

```bash
# Tick a checkbox on a PR
gh pr view <number> --json body -q .body \
  | sed 's/- \[ \] Unit tests added/- [x] Unit tests added/' \
  > /tmp/updated-body.md
gh pr edit <number> --body-file /tmp/updated-body.md

# Tick a checkbox on an issue
gh issue view <number> --json body -q .body \
  | sed 's/- \[ \] Criterion one/- [x] Criterion one/' \
  > /tmp/updated-body.md
gh issue edit <number> --body-file /tmp/updated-body.md
```

**For multiple checkboxes**, chain the sed replacements:

```bash
gh pr view <number> --json body -q .body \
  | sed 's/- \[ \] Unit tests added/- [x] Unit tests added/' \
  | sed 's/- \[ \] Self-reviewed diff/- [x] Self-reviewed diff/' \
  > /tmp/updated-body.md
gh pr edit <number> --body-file /tmp/updated-body.md
```

**Rules:**
- Check a box ONLY when its condition is verifiably met
- Tick issue acceptance criteria as each criterion is satisfied during implementation
- Tick PR checklist items as each condition is confirmed before/after merge
- If a checkbox CANNOT be satisfied (e.g., no tests applicable), note why in Reviewer Notes and either remove the checkbox or leave it unchecked with an inline explanation
- Never leave stale unchecked boxes on a merged PR or closed issue without explanation

## Merge Strategies

### Default: Rebase and Merge

**Always prefer rebase merge** to maintain a clean linear history where every commit on main is meaningful and passes tests independently.

Use for:
- PRs with clean, atomic commit history (the standard case)
- Each commit represents a distinct logical step
- Commit messages follow the format guide
- No broken intermediary commits

**Requirements:**
- Each commit passes tests independently
- Commit messages follow format guide
- No "fix typo" or "address review" commits (use fixup workflow)
- Linear history without merge commits
- **Before merging:** amend all commit messages to include `(#pr)` suffix (e.g., `gh-11: add OAuth2 config (#20)`). This is mandatory — every commit on main must reference the PR it came from.

```bash
# Amend commits to add (#pr), then force push
git rebase -i HEAD~N  # reword each commit to append "(#<pr-number>)"
git push --force-with-lease

gh pr merge <number> --rebase --delete-branch
```

### When: Squash and Merge

Use **only** when the branch has broken intermediary commits that cannot be cleaned up:
- Multiple WIP commits that weren't rebased before review
- History littered with "fix typo", "oops", "address review" commits
- External contributor PRs where you can't rewrite history
- Commits that don't individually pass tests

**Squash commit message format:**
```
gh-<issue>: <imperative description> (#pr)

- Key change 1
- Key change 2
- Key change 3

Co-authored-by: Reviewer Name <email>
```

```bash
gh pr merge <number> --squash --delete-branch
```

**Rule of thumb:** If you followed the fixup workflow during development and rebased before marking ready, you should never need squash. Squash is a fallback for messy history, not the default.

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
5. Rebase merge to `main` (squash only if intermediaries are broken)
6. Delete branch

### Hierarchical Branches

For parent issue #1 with children #2, #3:
```
main
├── feature/1-parent-issue
    ├── feature/1/2-child-issue-one
    └── feature/1/3-child-issue-two
```

**Rule:** When child issues exist, ALWAYS create corresponding sub-branches. Every child issue gets its own `feature/parent/child-description` branch. Sub-branches mirror sub-issues — if you decomposed the issue, decompose the branch.

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
Revert "gh-23: add OAuth2 support"

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
