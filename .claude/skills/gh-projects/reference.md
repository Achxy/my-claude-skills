# gh project CLI — Complete Command Reference

## Command Overview

| Command | Description |
|---------|-------------|
| `gh project create` | Create a project |
| `gh project list` / `ls` | List projects |
| `gh project view` | View project details |
| `gh project edit` | Edit project settings |
| `gh project close` | Close (or reopen with `--undo`) a project |
| `gh project copy` | Copy a project |
| `gh project delete` | Delete a project |
| `gh project link` | Link a repository to a project |
| `gh project unlink` | Unlink a repository from a project |
| `gh project mark-template` | Mark/unmark project as template |
| `gh project field-create` | Create a custom field |
| `gh project field-list` | List project fields |
| `gh project field-delete` | Delete a field |
| `gh project item-add` | Add existing issue/PR to project |
| `gh project item-create` | Create a draft item |
| `gh project item-list` | List project items |
| `gh project item-edit` | Edit item field values |
| `gh project item-archive` | Archive/unarchive an item |
| `gh project item-delete` | Delete an item |

## Common Flags (Available on Most Commands)

| Flag | Description |
|------|-------------|
| `--owner <string>` | Login of the owner. Use `@me` for current user. |
| `--format <string>` | Output format: `json` |
| `-q, --jq <expression>` | Filter JSON output using jq |
| `-t, --template <string>` | Format JSON output using Go template |

## gh project create

```
gh project create [flags]
```

| Flag | Description |
|------|-------------|
| `--title <string>` | Title for the project |
| `--owner <string>` | Owner login |

## gh project edit

```
gh project edit [<number>] [flags]
```

| Flag | Description |
|------|-------------|
| `--title <string>` | New title |
| `-d, --description <string>` | New description |
| `--readme <string>` | New readme |
| `--visibility <string>` | `PUBLIC` or `PRIVATE` |

## gh project close

```
gh project close [<number>] [flags]
```

| Flag | Description |
|------|-------------|
| `--undo` | Reopen a closed project |

## gh project copy

```
gh project copy [<number>] [flags]
```

| Flag | Description |
|------|-------------|
| `--source-owner <string>` | Source owner login |
| `--target-owner <string>` | Target owner login |
| `--title <string>` | Title for the copy |
| `--drafts` | Include draft issues |

## gh project field-create

```
gh project field-create [<number>] [flags]
```

| Flag | Description |
|------|-------------|
| `--name <string>` | Field name |
| `--data-type <string>` | `TEXT`, `SINGLE_SELECT`, `DATE`, `NUMBER` |
| `--single-select-options <strings>` | Comma-separated options for SINGLE_SELECT |

## gh project field-delete

```
gh project field-delete [flags]
```

| Flag | Description |
|------|-------------|
| `--id <string>` | ID of the field to delete |

## gh project item-add

```
gh project item-add [<number>] [flags]
```

| Flag | Description |
|------|-------------|
| `--url <string>` | URL of the issue or PR to add |

## gh project item-create

```
gh project item-create [<number>] [flags]
```

| Flag | Description |
|------|-------------|
| `--title <string>` | Title for the draft item |
| `--body <string>` | Body for the draft item |

## gh project item-edit

```
gh project item-edit [flags]
```

| Flag | Description |
|------|-------------|
| `--id <string>` | ID of the item to edit |
| `--field-id <string>` | ID of the field to update |
| `--text <string>` | Text value |
| `--number <float>` | Number value |
| `--date <string>` | Date value (YYYY-MM-DD) |
| `--single-select-option-id <string>` | Option ID for single select |
| `--iteration-id <string>` | Iteration ID |
| `--clear` | Clear the field value |

## gh project item-archive

```
gh project item-archive [<number>] [flags]
```

| Flag | Description |
|------|-------------|
| `--id <string>` | ID of the item |
| `--undo` | Unarchive the item |

## gh project item-delete

```
gh project item-delete [<number>] [flags]
```

| Flag | Description |
|------|-------------|
| `--id <string>` | ID of the item to delete |

## gh project link / unlink

```
gh project link [<number>] [flags]
gh project unlink [<number>] [flags]
```

| Flag | Description |
|------|-------------|
| `--repo <string>` | Repository in `owner/repo` format |

## gh label Commands

| Command | Description |
|---------|-------------|
| `gh label create <name>` | Create a label |
| `gh label list` | List labels |
| `gh label edit <name>` | Edit a label |
| `gh label delete <name>` | Delete a label |
| `gh label clone <source-repo>` | Clone labels from another repo |

### gh label create flags

| Flag | Description |
|------|-------------|
| `-c, --color <string>` | Color hex code (without `#`) |
| `-d, --description <string>` | Label description |
| `-f, --force` | Update if label exists |

## Milestone REST API Reference

Milestones are managed via `gh api`:

| Operation | Command |
|-----------|---------|
| Create | `gh api repos/{owner}/{repo}/milestones -f title="..." -f due_on="..." -f state="open"` |
| List | `gh api repos/{owner}/{repo}/milestones` |
| Get | `gh api repos/{owner}/{repo}/milestones/{number}` |
| Update | `gh api -X PATCH repos/{owner}/{repo}/milestones/{number} -f title="..."` |
| Delete | `gh api -X DELETE repos/{owner}/{repo}/milestones/{number}` |

### Milestone Fields

| Field | Type | Description |
|-------|------|-------------|
| `title` | string | Milestone title (required) |
| `description` | string | Description |
| `due_on` | string | ISO 8601 date (`2024-06-01T00:00:00Z`) |
| `state` | string | `open` or `closed` |

## GitHub MCP Server Toolsets

When using `github-mcp-server`, these toolsets provide project-related capabilities:

| Toolset | Tools | Description |
|---------|-------|-------------|
| `projects` | `projects_get`, `projects_list`, `projects_write` | Project CRUD |
| `issues` | `issue_read`, `issue_write`, `list_issues`, `search_issues`, `add_issue_comment`, `sub_issue_write`, `list_issue_types` | Issue operations |
| `labels` | `get_label`, `label_write`, `list_label` | Label management |
| `pull_requests` | `create_pull_request`, `list_pull_requests`, `merge_pull_request`, `pull_request_read`, `update_pull_request`, etc. | PR operations |

Configure via: `GITHUB_TOOLSETS=projects,issues,labels,pull_requests`
