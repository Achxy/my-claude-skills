---
name: issue-policy
description: Enforces GitHub issue creation, hierarchy, and decomposition standards. Use when creating issues, planning features, decomposing work, or structuring parent-child issue relationships. Activates on issue creation, project planning, or work breakdown tasks.
---

# GitHub Issue Policy

## Core Principle

**Decompose work into atomic, trackable units. Every non-trivial change requires an issue.**

## Assignment Rules

- ALWAYS assign the user themselves (`--assignee "@me"`) unless user explicitly opted out
- For child issues, inherit the parent's assignee unless specified otherwise
- Never leave issues unassigned

## When Issues Are Mandatory

| Requires Issue | Optional |
|---------------|----------|
| New features | Typo corrections |
| Bug fixes needing investigation | Formatting-only changes |
| Architectural changes | Routine dependency bumps |
| Multi-file refactoring | Comment additions |
| Substantial documentation | |
| Performance optimization | |
| Security patches | |

## Issue Title Format

```
[#Parent-ID] Component: Imperative action description
```

**Examples:**
- `[#1] Project: Initialize uv with discord.py dependencies`
- `[#1] Bot: Implement core client with intents configuration`
- `Commands: Add slash command registration system` (no parent)

For child issues, ALWAYS prefix with `[#parent-id]`.

## Issue Body Structure

Every issue body MUST contain these sections in order:

### 1. Problem Statement
Explain WHAT needs to be done and WHY. Provide context for the change.

### 2. Acceptance Criteria
Define exact closure conditions. Use checkboxes:
```markdown
- [ ] Criterion one
- [ ] Criterion two
- [ ] All tests pass
```

### 3. Technical Scope
List specific files, modules, or systems affected:
```markdown
**Files:** `src/auth/`, `tests/test_auth.py`
**Dependencies:** `pyjwt>=2.0`
```

### 4. Sub-Issue Visualization (Parent Issues Only)
After a `---` separator, include a Mermaid diagram:
```markdown
---

## Sub-Issues

` ` `mermaid
graph TD
    A[#1 Parent Feature] --> B[#2 Child One]
    A --> C[#3 Child Two]
    A --> D[#4 Child Three]
` ` `
```

## Hierarchy Rules

### Parent Issues
- Represent high-level features or epics
- Remain OPEN until ALL child issues close
- MUST include Mermaid diagram when children exist
- Track overall progress via child completion

### Child Issues
- Address a SINGLE concern
- Implementable in ONE pull request
- Reference parent with `[#parent-id]` in title
- Each maps to exactly one PR

### Depth Limit
Maximum 2 levels: Parent → Child. If deeper decomposition needed, create a new parent.

## Issue Relationships (Sub-Issues & Dependencies)

Use GitHub's native relationship features to formally link issues. This replaces informal "see #N" references.

### Sub-Issues (Parent-Child Hierarchy)

After creating parent and child issues, link them as sub-issues via the GraphQL API:

```bash
# Get issue node IDs
PARENT_ID=$(gh issue view <parent-number> --json id -q '.id')
CHILD_ID=$(gh issue view <child-number> --json id -q '.id')

# Add child as sub-issue of parent
gh api graphql -f query='
  mutation {
    addSubIssue(input: {
      issueId: "'$PARENT_ID'"
      subIssueId: "'$CHILD_ID'"
    }) {
      issue { id }
      subIssue { id }
    }
  }'
```

**Rules:**
- ALWAYS link child issues as sub-issues after creation — do not rely on title prefixes alone
- Sub-issues appear in the parent's sidebar and project boards automatically
- Parent progress tracks sub-issue completion natively

### Removing Sub-Issues

```bash
gh api graphql -f query='
  mutation {
    removeSubIssue(input: {
      issueId: "'$PARENT_ID'"
      subIssueId: "'$CHILD_ID'"
    }) {
      issue { id }
      subIssue { id }
    }
  }'
```

### Dependencies (Blocked By / Blocking)

Use dependency relationships when issues have execution-order constraints:

- **Blocked by**: This issue cannot proceed until another completes
- **Blocking**: This issue prevents another from starting

Dependencies are managed via the GitHub UI (Relationships sidebar) or the MCP server's `sub_issue_write` tool. Apply when:
- A child issue requires another child's output (e.g., DB migration before API layer)
- External dependencies block progress

**Rules:**
- Mark dependencies explicitly; do not assume order from issue numbers
- Blocked issues should carry the `blocked` label
- When a blocking issue closes, review and unblock dependents

## Mermaid Diagram Standards

```mermaid
graph TD
    A[#1 Initial Bot Implementation] --> B[#2 Project Setup]
    A --> C[#3 Core Bot Client]
    A --> D[#4 Command System]
    A --> E[#5 Logging Setup]
```

**Rules:**
- Use `graph TD` (top-down) format
- Node pattern: `NodeID[#issue-number Title]`
- Keep descriptions under 40 characters
- Arrows flow parent → child only

## Branch Naming Convention

| Type | Pattern |
|------|---------|
| Parent feature | `feature/parent-number-description` |
| Child feature | `feature/parent-number/child-number-description` |
| Standalone bugfix | `bugfix/issue-number-description` |
| Hotfix | `hotfix/description` |

**Examples:**
- `feature/1-initial-bot-implementation`
- `feature/1/2-project-setup`
- `feature/1/3-core-bot-client`
- `bugfix/56-null-pointer-handler`

## Issue Lifecycle

```
Creation → Decomposition → Implementation → Integration → Closure
```

1. **Creation**: Write issue with full body template
2. **Decomposition**: Break into child issues if complex
3. **Implementation**: Each child → one branch → one PR
4. **Integration**: Child PRs merge, parent tracks progress
5. **Closure**: Parent closes when all children complete

## Commit Reference Format

Commits referencing issues use: `gh-<issue-number>: description`

## Labels Strategy

Apply labels consistently:
- **Type**: `feature`, `bug`, `enhancement`, `documentation`
- **Priority**: `P0-critical`, `P1-high`, `P2-medium`, `P3-low`
- **Status**: `needs-triage`, `in-progress`, `blocked`
- **Scope**: Component-specific labels matching project modules

## Issue Creation Command

Always include assignment, labels, and milestone:

```bash
gh issue create \
  --title "[#parent] Component: Action description" \
  --body "..." \
  --label "feature" \
  --milestone "vX.Y" \
  --assignee "@me"
```

After creating child issues, ALWAYS link them as sub-issues of the parent (see "Issue Relationships" above).

## Enforcement

- PR templates MUST require issue references
- CI checks validate parent issues contain diagrams when children exist
- CI checks verify child issues reference parents in titles
- Parent issues cannot close while children remain open
- All child issues MUST be linked as sub-issues via the API
