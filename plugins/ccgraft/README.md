# ccgraft

A Claude Code plugin for exporting, importing, and restoring sessions. Share sessions between machines, archive conversations for reference, or transfer context between projects — with manifest validation, UUID regeneration, and pre-import snapshots for safe rollback.

## Overview

Claude Code stores session data in `~/.claude/projects/<normalized-path>/` as JSONL files. ccgraft reads these files, bundles them with all associated artifacts (agent sub-sessions, file history, plans, todos, config), and packages everything into a portable `.claude-sessions/` export directory. On import, UUIDs are regenerated so the session integrates cleanly into the target environment without colliding with existing data.

## Architecture

```
src/ccgraft/
├── __init__.py          # Version, logging setup
├── _io.py               # Atomic writes, advisory file locking (fcntl), watchdog filesystem events
├── cli/
│   ├── export.py        # CLI: ccgraft-export
│   ├── import_.py       # CLI: ccgraft-import
│   └── restore.py       # CLI: ccgraft-restore
├── config.py            # Collects .claude/ config (commands, skills, hooks, agents, rules, settings, CLAUDE.md)
├── errors.py            # Exception hierarchy (CcgraftError → SessionNotFoundError, ManifestError, etc.)
├── exporter.py          # Export pipeline: discover → extract metadata → collect artifacts → render → write manifest
├── importer.py          # Import pipeline: validate manifest → snapshot → regenerate UUIDs → place artifacts → log
├── manifest.py          # .ccgraft-manifest.json schema, serialization, and validation
├── paths.py             # Claude Code path normalization (project path → internal directory name)
├── session.py           # Session discovery, JSONL reading/writing, active session identification, UUID regeneration
└── snapshot.py          # Pre-import snapshots: create, inspect, restore, and import audit logging
```

## Skills

| Skill | Command | Description |
|-------|---------|-------------|
| **export-session** | `/ccgraft:export-session` | Export the current session to `.claude-sessions/` |
| **import-session** | `/ccgraft:import-session <path>` | Import an exported session with UUID regeneration |
| **restore-backup** | `/ccgraft:restore-backup` | Revert to pre-import state from snapshot |

## How It Works

### Export

1. **Discovers the active session** — uses watchdog filesystem events to detect which JSONL file is being written to, falling back to most-recent-by-mtime
2. **Extracts metadata** — session ID, timestamps, message counts, tool uses, models, Claude Code version, git branch
3. **Collects artifacts** — agent sub-sessions, file history snapshots, plan files, todos, session environment
4. **Collects config** — commands, skills, hooks, agents, rules, settings.json, CLAUDE.md from the project's `.claude/` directory
5. **Renders output** — RENDERED.md (GitHub-optimized markdown with collapsible thinking blocks) and conversation.xml
6. **Writes manifest** — `.ccgraft-manifest.json` with version, session data pointers, original context, and config snapshot paths

### Import

1. **Validates the manifest** — checks required fields, parses session data and context
2. **Creates a pre-import snapshot** — full backup of the target session directory for rollback
3. **Regenerates UUIDs** — new sessionId, uuid, parentUuid, agentId, and cwd while preserving Anthropic-tied fields (message.id, requestId, thinking signatures, tool_use.id, timestamps)
4. **Places artifacts** — session JSONL, file history, todos, plans, and config into their expected locations
5. **Logs the import** — audit trail in `~/.claude-session-imports/` with timestamp, original/new session IDs, and summary

### Restore

1. **Shows snapshot info** (`--info`) — age, target directory, whether prior state was saved, import source
2. **Restores on confirmation** (`--force`) — replaces the target directory with the snapshot contents, then cleans up the snapshot

## Export Directory Structure

```
.claude-sessions/<export-name>/
├── .ccgraft-manifest.json       # Export manifest with validation metadata
├── RENDERED.md                  # Human-readable markdown rendering
├── conversation.xml             # Structured XML rendering
├── session/
│   ├── main.jsonl               # Primary session data
│   ├── agents/                  # Agent sub-session JSONL files
│   ├── file-history/            # File modification snapshots
│   ├── plan.md                  # Session plan (if any)
│   ├── todos.json               # Consolidated todos
│   └── session-env/             # Session environment files
└── config/
    ├── commands/                # .claude/commands/*.md
    ├── skills/                  # .claude/skills/**/SKILL.md
    ├── hooks/                   # .claude/hooks/*
    ├── agents/                  # .claude/agents/*.md
    ├── rules/                   # .claude/rules/*.md
    ├── settings.json            # .claude/settings.json
    └── CLAUDE.md                # Project CLAUDE.md
```

## Auto-Export Hook

The plugin includes an optional hook that automatically exports the session when Claude Code stops:

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "bash \"${CLAUDE_PLUGIN_ROOT}/hooks/auto_export.sh\""
          }
        ]
      }
    ]
  }
}
```

The auto-export uses `--max-age 3600` (1 hour) to only export sessions that were recently active. To disable, remove the Stop hook from `hooks/hooks.json`.

## CLI Reference

### ccgraft-export

```
ccgraft-export [options]

Options:
  --session-id ID      Export a specific session (default: auto-detect active)
  --export-name NAME   Name for the export folder (default: timestamp)
  --output-dir DIR     Custom output directory
  --format {md,xml,all}  Output format (default: all)
  --max-age SECONDS    Max session age in seconds (default: 300)
  --anonymize          Exclude user identity from manifest
  --no-in-repo         Export to ~/claude_sessions/ instead of .claude-sessions/
  -v, --verbose        Verbose output
```

### ccgraft-import

```
ccgraft-import <export-path> [options]

Arguments:
  export-path          Path to export directory containing .ccgraft-manifest.json

Options:
  --target-project DIR   Import into a different project (default: cwd)
  --skip-config          Don't import config files
  --skip-snapshot        Don't create pre-import backup
  -v, --verbose          Verbose output
```

### ccgraft-restore

```
ccgraft-restore [options]

Options:
  --info       Show snapshot details without restoring
  --force      Restore without confirmation prompt
  -v, --verbose  Verbose output
```

## Safety Features

- **Atomic writes** — All file operations use temp-file-then-rename to prevent corruption on interruption
- **Advisory file locking** — Shared locks for reads, exclusive locks for writes (fcntl on Unix, no-op on Windows)
- **Pre-import snapshots** — Full backup before every import, restorable via `/ccgraft:restore-backup`
- **UUID regeneration** — Prevents session ID collisions; preserves Anthropic-tied identifiers
- **Manifest validation** — Required fields checked before import proceeds
- **No-overwrite guarantee** — Import refuses to write to existing session files

## Requirements

- Python >= 3.10
- [uv](https://docs.astral.sh/uv/) (used by bin scripts to run in the plugin's virtual environment)
- [watchdog](https://github.com/gorakhargosh/watchdog) >= 4.0 (active session detection)

## Testing

Tests run across Python 3.10–3.14 via GitHub Actions:

```bash
cd plugins/ccgraft
uv run pytest tests/ -v
```

## Installation

Via the dotclaude marketplace:

```
/plugin marketplace add Achxy/dotclaude
/plugin install ccgraft@dotclaude
```

Or load directly for development:

```bash
claude --plugin-dir ./plugins/ccgraft
```
