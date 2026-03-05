---
name: import-session
description: Import a ccgraft session export into Claude Code. Validates manifest, regenerates UUIDs, and imports session data with pre-import snapshots for recovery.
---

The argument is the path to a `.claude-sessions/<name>/` export directory (containing `.ccgraft-manifest.json`).

If the user provided an export path, run:

```bash
bash "${CLAUDE_PLUGIN_ROOT}/bin/ccgraft-import" $ARGUMENTS
```

If no path was provided, show available exports in the current project:

```bash
ls -la .claude-sessions/ 2>/dev/null || echo "No exports found in this directory. Run /ccgraft:export-session in the source project first, then provide the path here."
```

After import, tell the user: **To continue the imported session, run `claude --continue` in a new terminal.**

Note: The import runs in the current directory by default. If the user needs to import into a different project, they can pass `--target-project <path>`.
