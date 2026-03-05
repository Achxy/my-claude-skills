---
name: workflow-orchestrator
description: Orchestrates the full development workflow by synchronizing commit-policy, issue-policy, pr-policy, and gh-projects skills. Use for any end-to-end development task — planning features, implementing work, creating issues, committing, opening PRs, or managing project boards. Activates when multiple workflow stages are involved or when coordinating planning with execution.
---

# Workflow Orchestrator

This skill coordinates four complementary skills into a unified development workflow:

| Skill | Responsibility |
|-------|---------------|
| **issue-policy** | Work decomposition, issue hierarchy, acceptance criteria |
| **gh-projects** | Project boards, fields, labels, milestones, tracking |
| **commit-policy** | Commit message formatting, atomic commits |
| **pr-policy** | PR creation, review, merge strategy, branch management |

## Workflow Phases

Every development task flows through these phases. Apply the relevant skill(s) at each stage.

### Phase 1: Planning (issue-policy + gh-projects)

**Trigger:** User describes a feature, bug, or task.

1. **Assess scope** — Determine if work needs an issue (see issue-policy mandatory criteria)
2. **Create parent issue** if work is non-trivial:
   - Title: `Component: Imperative action description`
   - Body: Problem statement, acceptance criteria, technical scope
3. **Decompose** into child issues if complex:
   - Each child: single concern, one PR, title prefixed `[#parent-id]`
   - Add Mermaid diagram to parent
4. **Set up project tracking:**
   - Add issues to project board (`gh project item-add`)
   - Apply labels: type (`feature`, `bug`) + priority (`P0`-`P3`)
   - Assign milestone
   - Set custom field values (Status, Priority, Story Points)
5. **Create branches:**
   - Parent: `feature/<parent-number>-<description>`
   - Children: `feature/<parent-number>/<child-number>-<description>`

### Phase 2: Implementation (commit-policy)

**Trigger:** Writing or modifying code.

1. **Work on one child issue at a time** on its feature branch
2. **Make atomic commits** following commit-policy:
   - Issue-tracked: `gh-<issue>: <imperative summary>`
   - Untracked: `<type>(<scope>): <imperative summary>`
3. **Organize commits logically:**
   - Infrastructure/setup first
   - Core implementation
   - Tests
   - Documentation
4. **Use fixup workflow** for incremental fixes during development:
   ```bash
   git commit --fixup=<target-hash>
   ```

### Phase 3: PR Creation (pr-policy + gh-projects)

**Trigger:** Implementation complete, ready for review.

1. **Clean commit history:**
   ```bash
   git rebase -i --autosquash origin/main
   ```
2. **Self-review checklist** (pr-policy)
3. **Create PR:**
   - Title: `[#issue] Component: Imperative description`
   - Body: Changes, issue reference (`Closes #N`), testing, checklist
   - Size: Aim for < 200 lines changed
4. **Update project board:**
   - Move item status to "In Review"
   - Ensure labels reflect current state

### Phase 4: Review & Merge (pr-policy + commit-policy)

**Trigger:** PR review cycle.

1. **Address feedback:**
   - Small changes: `git commit --fixup=<hash>`
   - Substantial: new commit with proper message
2. **Before merge:** Squash all fixups: `git rebase -i --autosquash origin/main`
3. **Merge strategy selection:**
   - Default: **Squash and merge** (one commit per PR in main)
   - Rebase merge: Only if commit history is intentionally structured
   - **Never** merge commits
4. **Post-merge cleanup:**
   - Delete feature branch
   - Update project board: move to "Done"
   - Close child issue (auto-closes via `Closes #N`)
   - Check if parent issue can close (all children done)

### Phase 5: Tracking & Maintenance (gh-projects)

**Ongoing:** Keep project state accurate.

1. **Update milestone progress** — check open/closed issue counts
2. **Archive completed items** on project board
3. **Review blocked items** — update labels, reassign
4. **Close milestones** when all issues resolved

## Decision Matrix

Use this to determine which skills apply to a given task:

| Task | Skills Involved |
|------|----------------|
| "Plan a new feature" | issue-policy → gh-projects |
| "Implement this function" | commit-policy |
| "Open a PR for this work" | pr-policy → gh-projects |
| "Fix this bug" | issue-policy → commit-policy → pr-policy |
| "Set up project tracking" | gh-projects |
| "Review this PR" | pr-policy |
| "Create a release" | gh-projects (milestones) → pr-policy |
| "Decompose this epic" | issue-policy → gh-projects |
| "Clean up commit history" | commit-policy → pr-policy |
| "Full feature lifecycle" | ALL (in order: plan → implement → PR → merge → track) |

## Integrated Example: Full Feature Lifecycle

Given: "Add user authentication"

**Step 1 — Plan (issue-policy + gh-projects):**
```bash
# Create parent issue
gh issue create --title "Auth: Implement user authentication system" \
  --body "## Problem Statement
Application needs user authentication.

## Acceptance Criteria
- [ ] Login/logout endpoints
- [ ] JWT token handling
- [ ] Session management
- [ ] Tests pass

## Technical Scope
**Files:** \`src/auth/\`, \`tests/test_auth.py\`
---
## Sub-Issues
\`\`\`mermaid
graph TD
    A[#10 User Authentication] --> B[#11 OAuth2 Client]
    A --> C[#12 Token Refresh]
    A --> D[#13 Session Management]
\`\`\`" \
  --label "feature,P1-high" --milestone "v1.0"

# Create child issues
gh issue create --title "[#10] Auth: Set up OAuth2 client" --label "feature" --milestone "v1.0"
gh issue create --title "[#10] Auth: Implement token refresh" --label "feature" --milestone "v1.0"
gh issue create --title "[#10] Auth: Add session management" --label "feature" --milestone "v1.0"

# Add to project
gh project item-add 1 --owner "@me" --url "$(gh issue view 10 --json url -q .url)"
gh project item-add 1 --owner "@me" --url "$(gh issue view 11 --json url -q .url)"
# ... for each issue

# Set priority fields on project items
# (use gh project item-edit with field IDs)
```

**Step 2 — Implement (commit-policy):**
```bash
git checkout -b feature/10/11-oauth2-client

# Atomic commits
git commit -m "gh-11: add OAuth2 client configuration"
git commit -m "gh-11: implement authorization code flow"
git commit -m "gh-11: add OAuth2 client tests"
```

**Step 3 — PR (pr-policy):**
```bash
# Clean history
git rebase -i --autosquash origin/main
git push --force-with-lease

# Create PR
gh pr create --title "[#11] Auth: Set up OAuth2 client" \
  --body "## Changes
- OAuth2 client with PKCE support
- Configuration via environment variables

## Issue Reference
Closes #11

## Testing
- [ ] Unit tests added
- [ ] Integration test passes"
```

**Step 4 — Merge (pr-policy + gh-projects):**
```bash
# After approval, squash merge
# Update project: item → "Done"
# Delete branch
git branch -d feature/10/11-oauth2-client
```

**Step 5 — Track (gh-projects):**
```bash
# Check parent progress
gh issue view 10
# When all children (#11, #12, #13) closed → close parent
gh issue close 10
# Update milestone
gh api repos/{owner}/{repo}/milestones/1 --jq '{open_issues, closed_issues}'
```

## Conflict Resolution Between Skills

When skills have overlapping guidance:

1. **commit-policy** governs commit message format — always
2. **pr-policy** governs PR title/description format — always
3. **issue-policy** governs issue structure — always
4. **gh-projects** governs project board state — always
5. For branch naming: issue-policy and pr-policy agree — follow the `feature/parent/child` convention
6. For merge strategy: pr-policy decides (default squash)

## Automation Patterns

### Script: Full Issue-to-Project Pipeline
```bash
# Create issue, add to project, set fields — all in one flow
ISSUE_URL=$(gh issue create --title "$TITLE" --label "$LABELS" --milestone "$MILESTONE" --json url -q .url)
ITEM_ID=$(gh project item-add $PROJECT_NUM --owner "@me" --url "$ISSUE_URL" --format json --jq '.id')
gh project item-edit --id "$ITEM_ID" --field-id "$PRIORITY_FIELD_ID" --single-select-option-id "$P1_OPTION_ID"
gh project item-edit --id "$ITEM_ID" --field-id "$STATUS_FIELD_ID" --single-select-option-id "$TODO_OPTION_ID"
```

### When to Use Agent Teams

For large-scale work (epics with 5+ children), consider using agent teams:
- **Lead**: Coordinates overall planning and tracks progress
- **Planner teammate**: Creates issues, sets up project board (issue-policy + gh-projects)
- **Implementer teammates**: Each works on a child issue in its own worktree (commit-policy)
- **Reviewer teammate**: Reviews PRs as they come in (pr-policy)

This parallelizes the workflow while maintaining policy compliance across all phases.
