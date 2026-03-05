# gh-sdlc

A Claude Code plugin that orchestrates the full GitHub Software Development Lifecycle — from issue creation through project tracking, branching, atomic commits, pull requests, merging, and board maintenance.

## Overview

gh-sdlc codifies an opinionated SDLC workflow into five coordinated policy skills and an autonomous shipping agent. When invoked, it decomposes work into trackable GitHub issues, organizes them on project boards, creates hierarchical branches, enforces commit message standards, opens well-structured PRs, and merges with a clean linear history.

The plugin is **opt-in only** — it never auto-activates. You trigger it explicitly with `/gh-sdlc` or by saying "commit", "ship it", "open a PR", etc.

## Skills

| Skill | Purpose |
|-------|---------|
| **gh-sdlc** | Top-level orchestrator. Parses arguments, selects execution mode, and coordinates the other four skills through a 5-phase pipeline. |
| **issue-policy** | Work decomposition, issue hierarchy (parent/child via sub-issue API), acceptance criteria, Mermaid diagrams, branch naming conventions. |
| **commit-policy** | Commit message formatting (`gh-<issue>: <summary>` for tracked work, `type(scope): summary` for untracked), atomic commit organization, fixup workflow. |
| **pr-policy** | PR creation with full metadata, `Closes #N` linking, merge strategy selection (rebase default, squash fallback), self-review checklist, checkbox management. |
| **gh-projects** | Project board management — fields, items, labels, milestones, sub-issues, bulk operations. Includes a complete `gh` CLI command reference. |

## Agent

**sdlc-shipper** — An autonomous subagent (runs on Sonnet) spawned for retroactive shipping (Use Case B). When you've already written the code and just want to formalize it, the shipper analyzes your diff, plans the decomposition, creates issues, commits atomically, opens PRs, merges, and updates the project board — all without asking questions.

## Usage

### Slash command

```
/gh-sdlc                              # Ship completed work (yolo mode, delegates to shipper)
/gh-sdlc add OAuth2 support            # Plan + implement + ship (yolo mode)
/gh-sdlc interactive add OAuth2        # Same, but confirm each decision
```

### Use Cases

| Scenario | What happens |
|----------|-------------|
| **A) Upfront** — `/gh-sdlc <objective>` before work starts | Full pipeline: plan → implement → PR → merge → track. Runs in the current model. |
| **B) Retroactive** — `/gh-sdlc` after work is done | Delegates to the `sdlc-shipper` agent, which formalizes existing changes through the full pipeline. |

### Interaction Modes

| Mode | Behavior |
|------|----------|
| **yolo** (default) | All decisions made autonomously. No questions asked. |
| **interactive** | Confirms each decision point (decomposition, commit grouping, PR metadata, merge strategy) via `AskUserQuestion`. Always runs in the current model. |

## Workflow Phases

```
Phase 1: Planning         — Assess scope, create issues, decompose, set up project tracking, create branches
Phase 2: Implementation   — Atomic commits on feature branches following commit-policy
Phase 3: PR Creation      — Clean history, self-review, create PR with full metadata, add to project board
Phase 4: Review & Merge   — Address feedback, squash fixups, rebase merge (default), post-merge cleanup
Phase 5: Tracking         — Update milestones, archive completed items, close parent issues
```

## Key Conventions

### Issue titles
```
Component: Imperative action description
```
No bracket prefixes. Parent-child relationships use GitHub's sub-issue API, not title conventions.

### PR titles
```
gh-<issue>: <imperative description>
```
Same format as commit messages — PR titles and commits are unified.

### Commit messages
```
gh-<issue>: <imperative summary> (#pr)     # Issue-tracked on main (preferred)
gh-<issue>: <imperative summary>           # Issue-tracked during development (PR not yet created)
<type>(<scope>): <imperative summary>      # Untracked
```
Every commit on main must include the `(#pr)` suffix referencing the PR it was merged through.

### Branch naming
```
feature/<parent-number>-<description>                    # Parent feature
feature/<parent-number>/<child-number>-<description>     # Child feature
bugfix/<issue-number>-<description>                      # Standalone bugfix
hotfix/<description>                                     # Emergency hotfix
```

### Merge strategy
- **Default**: Rebase and merge — preserves linear history with every commit visible on main
- **Squash**: Only when intermediary commits are broken (WIP, untested, messy)
- **Merge commit**: Never (except merging long-lived release branches)

## Visualization

The workflow uses Mermaid diagrams where they add genuine value:

- **GitGraph** — Complex branching plans (multiple sub-branches)
- **Flowchart** (`graph TD`) — Issue decomposition with parent→child relationships
- **State Diagram** — Issue/PR lifecycle transitions
- **Sequence Diagram** — Agent/human/CI interaction flows
- **Diff codeblocks** — Proposed changes before making them

Simple single-issue changes don't get diagrams.

## Requirements

- [GitHub CLI](https://cli.github.com/) (`gh`) with `project` scope: `gh auth refresh -s project`
- A GitHub repository with Issues enabled
- A GitHub Project board (optional but recommended)

## Installation

Via the dotclaude marketplace:

```
/plugin marketplace add Achxy/dotclaude
/plugin install gh-sdlc@dotclaude
```

Or load directly for development:

```bash
claude --plugin-dir ./plugins/gh-sdlc
```
