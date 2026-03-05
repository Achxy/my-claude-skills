---
name: export-session
description: Export current Claude Code session for sharing or backup. Creates a portable .claude-sessions/ export with manifest, rendered markdown, and full session data.
---

Run this exact command. If the user provided a name for the export, append `--export-name "<name>"`:

```bash
bash "${CLAUDE_PLUGIN_ROOT}/bin/ccgraft-export"
```

The export will be created in `.claude-sessions/<timestamp>/` within the current project. Show the command output to the user — it will tell them the exact path and session name.
