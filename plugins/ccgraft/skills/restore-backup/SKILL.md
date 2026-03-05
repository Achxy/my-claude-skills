---
name: restore-backup
description: Restore from pre-import snapshot after a failed or unwanted session import. Reverts to the state before the last ccgraft import.
---

First show what the restore will do:

```bash
bash "${CLAUDE_PLUGIN_ROOT}/bin/ccgraft-restore" --info
```

**STOP HERE.** Show the output to the user and ask whether they want to proceed. Do NOT run the restore command until the user explicitly confirms.

If `--info` fails with "No pre-import snapshot found", tell the user no snapshot is available and do not attempt a restore.

After the user confirms they want to proceed, run:

```bash
bash "${CLAUDE_PLUGIN_ROOT}/bin/ccgraft-restore" --force
```
