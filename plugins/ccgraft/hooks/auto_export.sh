#!/bin/bash
# ccgraft auto-export hook
# Triggers on Stop event -- exports the session automatically when Claude finishes.
# Optional. To disable, remove the Stop hook from hooks/hooks.json.

set -euo pipefail

PLUGIN_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CWD=$(jq -r '.cwd // "."' 2>/dev/null || pwd)

cd "$CWD" || exit 0

bash "$PLUGIN_ROOT/bin/ccgraft-export" --max-age 3600 2>/dev/null || true

exit 0
