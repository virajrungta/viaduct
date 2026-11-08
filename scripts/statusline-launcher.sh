#!/usr/bin/env bash
# Copied by session-start.sh to ~/.local/share/kipcb/statusline.sh, the stable path in Claude
# Code's statusLine setting. The plugin's own folder changes with each version, so this runs
# the status line of the version recorded next to it in plugin-root.
HERE="$(dirname "${BASH_SOURCE[0]}")"
ROOT_FILE="$HERE/plugin-root"
[ -f "$ROOT_FILE" ] || exit 0
ROOT="$(cat "$ROOT_FILE")"
TARGET="$ROOT/scripts/statusline.sh"
[ -f "$TARGET" ] && exec bash "$TARGET"
exit 0
