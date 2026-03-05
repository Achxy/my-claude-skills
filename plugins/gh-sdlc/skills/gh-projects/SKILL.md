---
name: gh-projects
description: "GitHub Projects management reference (part of gh-sdlc). Provides commands for project boards, fields, items, labels, milestones — only applies when project management is needed as part of the /gh-sdlc workflow. Does NOT auto-activate on its own."
allowed-tools: Bash(gh *), Bash(git *)
---

# GitHub Projects Management

Comprehensive project management using `gh` CLI and GitHub MCP Server. Use `gh` CLI as the primary tool; fall back to `gh api` for operations not covered by first-class commands (milestones, advanced queries).

For additional reference, see [reference.md](reference.md) for the complete gh CLI command reference.

## Prerequisites

Ensure project scope is available:
```bash
gh auth refresh -s project
gh auth status
```

## Project Lifecycle

### Create a Project
```bash
gh project create --owner "@me" --title "Project Title"
gh project create --owner <org> --title "Sprint 1"
```

### List Projects
```bash
gh project list --owner "@me" --limit 50
gh project list --owner <org> --closed  # include closed
gh project ls  # alias
```

### View Project Details
```bash
gh project view <number> --owner "@me"
gh project view <number> --owner "@me" --format json
gh project view <number> --owner <org> --web  # open in browser
```

### Edit Project
```bash
gh project edit <number> --owner "@me" --title "New Title"
gh project edit <number> --owner "@me" --description "Updated description"
gh project edit <number> --owner "@me" --visibility PUBLIC|PRIVATE
gh project edit <number> --owner "@me" --readme "Project readme content"
```

### Close / Reopen Project
```bash
gh project close <number> --owner "@me"
gh project close <number> --owner "@me" --undo  # reopen
```

### Copy Project
```bash
gh project copy <number> --source-owner <source> --target-owner <target> --title "Copy"
gh project copy <number> --source-owner <source> --target-owner <target> --drafts  # include drafts
```

### Delete Project
```bash
gh project delete <number> --owner "@me"
```

### Link/Unlink Repository
```bash
gh project link <number> --owner "@me" --repo <owner/repo>
gh project unlink <number> --owner "@me" --repo <owner/repo>
```

### Mark as Template
```bash
gh project mark-template <number> --owner <org>
gh project mark-template <number> --owner <org> --undo
```

## Custom Fields

### Create Fields
```bash
# Text field
gh project field-create <number> --owner "@me" --name "Priority" --data-type TEXT

# Number field
gh project field-create <number> --owner "@me" --name "Story Points" --data-type NUMBER

# Date field
gh project field-create <number> --owner "@me" --name "Due Date" --data-type DATE

# Single select with options
gh project field-create <number> --owner "@me" --name "Status" --data-type SINGLE_SELECT --single-select-options "Todo,In Progress,Done,Blocked"

# Priority field
gh project field-create <number> --owner "@me" --name "Priority" --data-type SINGLE_SELECT --single-select-options "P0-critical,P1-high,P2-medium,P3-low"
```

### List Fields
```bash
gh project field-list <number> --owner "@me"
gh project field-list <number> --owner "@me" --format json
```

### Delete Field
```bash
gh project field-delete --id <field-id>
```

## Project Items

### Add Existing Issue/PR to Project
```bash
gh project item-add <number> --owner "@me" --url <issue-or-pr-url>
```

### Create Draft Item
```bash
gh project item-create <number> --owner "@me" --title "Draft item" --body "Description"
```

### List Items
```bash
gh project item-list <number> --owner "@me"
gh project item-list <number> --owner "@me" --limit 100 --format json
gh project item-list <number> --owner "@me" --query "assignee:username"  # filter syntax
```

### Edit Item Fields
```bash
# NOTE: --project-id is the GraphQL node ID (from `gh project view --format json --jq '.id'`)
# --field-id and --id are also GraphQL IDs (from field-list/item-list --format json)

# Edit text field
gh project item-edit --id <item-id> --field-id <field-id> --project-id <project-id> --text "value"

# Edit number field
gh project item-edit --id <item-id> --field-id <field-id> --project-id <project-id> --number 5

# Edit date field
gh project item-edit --id <item-id> --field-id <field-id> --project-id <project-id> --date "2024-03-15"

# Edit single select
gh project item-edit --id <item-id> --field-id <field-id> --project-id <project-id> --single-select-option-id <option-id>

# Edit iteration
gh project item-edit --id <item-id> --field-id <field-id> --project-id <project-id> --iteration-id <iteration-id>

# Clear field value
gh project item-edit --id <item-id> --field-id <field-id> --project-id <project-id> --clear
```

### Archive / Unarchive Item
```bash
gh project item-archive <number> --owner "@me" --id <item-id>
gh project item-archive <number> --owner "@me" --id <item-id> --undo
```

### Delete Item
```bash
gh project item-delete <number> --owner "@me" --id <item-id>
```

## Labels Management

### Create Labels
```bash
gh label create "P0-critical" --description "Critical priority" --color "B60205"
gh label create "P1-high" --description "High priority" --color "D93F0B"
gh label create "P2-medium" --description "Medium priority" --color "FBCA04"
gh label create "P3-low" --description "Low priority" --color "0E8A16"
gh label create "feature" --description "New feature" --color "1D76DB"
gh label create "bug" --description "Bug fix" --color "B60205"
gh label create "enhancement" --description "Enhancement" --color "A2EEEF"
gh label create "documentation" --description "Documentation" --color "0075CA"
gh label create "blocked" --description "Blocked by dependency" --color "D93F0B"
gh label create "needs-triage" --description "Needs triage" --color "E4E669"
```

### List Labels
```bash
gh label list
gh label list --json name,description,color
```

### Edit Label
```bash
gh label edit "old-name" --name "new-name" --description "Updated" --color "FF0000"
```

### Delete Label
```bash
gh label delete "label-name" --yes
```

### Apply Labels to Issues
```bash
gh issue edit <number> --add-label "P1-high,feature"
gh issue edit <number> --remove-label "needs-triage"
```

## Milestones (via gh api)

### Create Milestone
```bash
gh api repos/{owner}/{repo}/milestones -f title="v1.0" -f description="First release" -f due_on="2024-06-01T00:00:00Z" -f state="open"
```

### List Milestones
```bash
gh api repos/{owner}/{repo}/milestones --jq '.[].title'
gh api repos/{owner}/{repo}/milestones --jq '.[] | {number, title, state, due_on, open_issues, closed_issues}'
```

### Update Milestone
```bash
gh api -X PATCH repos/{owner}/{repo}/milestones/<number> -f title="v1.0 - Updated" -f state="closed"
```

### Delete Milestone
```bash
gh api -X DELETE repos/{owner}/{repo}/milestones/<number>
```

### Assign Milestone to Issue
```bash
gh issue edit <issue-number> --milestone "v1.0"
```

## Sub-Issues and Dependencies (via GraphQL API)

### Link Child as Sub-Issue
```bash
PARENT_ID=$(gh issue view <parent> --json id -q '.id')
CHILD_ID=$(gh issue view <child> --json id -q '.id')

gh api graphql -f query='
  mutation { addSubIssue(input: { issueId: "'$PARENT_ID'", subIssueId: "'$CHILD_ID'" }) {
    issue { id } subIssue { id }
  }}'
```

### Remove Sub-Issue
```bash
gh api graphql -f query='
  mutation { removeSubIssue(input: { issueId: "'$PARENT_ID'", subIssueId: "'$CHILD_ID'" }) {
    issue { id } subIssue { id }
  }}'
```

### Reorder Sub-Issue
```bash
# Place CHILD after AFTER_CHILD in the sub-issue list
gh api graphql -f query='
  mutation { reprioritizeSubIssue(input: {
    issueId: "'$PARENT_ID'", subIssueId: "'$CHILD_ID'", afterId: "'$AFTER_CHILD_ID'"
  }) { issue { id } }}'
```

## PR Management with Project Context

PRs are first-class project items just like issues. They should be added to the project board, assigned fields, and tracked through their lifecycle.

### Add PR to Project

```bash
PR_URL=$(gh pr view <number> --json url -q .url)
ITEM_ID=$(gh project item-add <project-number> --owner "@me" --url "$PR_URL" --format json --jq '.id')

# Set status, priority, and other fields
gh project item-edit --id "$ITEM_ID" --field-id "$STATUS_FIELD_ID" --project-id "$PROJECT_ID" \
  --single-select-option-id "$IN_REVIEW_OPTION_ID"
gh project item-edit --id "$ITEM_ID" --field-id "$PRIORITY_FIELD_ID" --project-id "$PROJECT_ID" \
  --single-select-option-id "$PRIORITY_OPTION_ID"
```

### PR Lifecycle on Project Board

| PR State | Project Status |
|----------|---------------|
| Open (draft or ready) | In Progress |
| Merged | Done |
| Closed without merge | Remove or archive |

### PR Metadata

When creating PRs, attach project metadata directly:

```bash
gh pr create \
  --title "gh-<issue>: <imperative description>" \
  --body-file /tmp/pr-body.md \
  --project "Project Name" \
  --milestone "v1.0" \
  --label "feature" \
  --reviewer <username> \
  --assignee "@me"
```

## Issue Management with Project Context

### Create Issue with Full Metadata

Always use `--body-file` for issue bodies to avoid shell corruption of markdown:

```bash
cat > /tmp/issue-body.md <<'EOF'
## Problem Statement
OAuth2 needed for third-party auth.

## Acceptance Criteria
- [ ] OAuth2 client configured
- [ ] Token refresh implemented
- [ ] Tests pass

## Technical Scope
**Files:** `src/auth/`, `tests/test_auth.py`
EOF

gh issue create --title "Auth: Implement OAuth2 flow" \
  --body-file /tmp/issue-body.md \
  --label "feature,P1-high" \
  --milestone "v1.0" \
  --assignee "@me"

rm /tmp/issue-body.md
```

### Add Issue to Project
```bash
# Get issue URL, then add to project
gh project item-add <project-number> --owner "@me" --url "$(gh issue view <issue-number> --json url --jq '.url')"
```

### Bulk Operations
```bash
# Add all open issues to a project
gh issue list --state open --json url --jq '.[].url' | while read url; do
  gh project item-add <project-number> --owner "@me" --url "$url"
done

# Label all issues in a milestone
gh issue list --milestone "v1.0" --json number --jq '.[].number' | while read num; do
  gh issue edit "$num" --add-label "sprint-1"
done
```

## GitHub MCP Server Integration

When the GitHub MCP Server is configured, these tools are available:

| MCP Tool | Operation |
|----------|-----------|
| `projects_get` | View project details |
| `projects_list` | List projects for owner |
| `projects_write` | Create/edit/manage projects |
| `issue_read` | Read issue details |
| `issue_write` | Create/edit issues |
| `label_write` | Create/manage labels |
| `list_label` | List available labels |
| `get_label` | Get label details |
| `sub_issue_write` | Manage sub-issues |

### MCP Setup for Claude Code
```bash
# Quick setup via gh mcp
gh mcp

# Or configure with specific toolsets
GITHUB_TOOLSETS=projects,issues,labels,pull_requests
```

## Standard Project Setup Workflow

When starting a new project, execute this setup sequence:

1. **Create project**: `gh project create --owner "@me" --title "Project Name"`
2. **Create standard labels**: Priority labels (P0-P3), type labels (feature, bug, etc.)
3. **Create milestones**: Version-based milestones with due dates
4. **Create custom fields**: Status, Priority, Story Points, Due Date
5. **Link repository**: `gh project link <number> --owner "@me" --repo <repo>`
6. **Create parent issues**: High-level feature issues with Mermaid diagrams
7. **Decompose into children**: Atomic child issues linked via sub-issue API
8. **Add all issues to project**: Bulk add with field assignments
9. **Set field values**: Priority, status, iteration for each item

## JSON Output for Scripting

All `gh project` commands support `--format json` and `--jq` for machine-readable output:

```bash
# Get project ID
gh project view <number> --owner "@me" --format json --jq '.id'

# Get all item IDs
gh project item-list <number> --owner "@me" --format json --jq '.[].id'

# Get field IDs
gh project field-list <number> --owner "@me" --format json --jq '.[] | {name, id}'
```
