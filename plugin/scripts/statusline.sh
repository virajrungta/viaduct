#!/usr/bin/env bash
# Claude Code status line: the PCB design progress bar while a design is in progress
# (empty otherwise). Uses a plain Python (no KiCad needed), so it's instant.
cat >/dev/null 2>&1 &   # Claude Code sends session JSON on stdin; we don't need it
HERE="$(dirname "${BASH_SOURCE[0]}")"
HERE="$(cd "$HERE" && pwd)"
SCRIPT="$HERE/statusline.py"
case "$(uname -s 2>/dev/null)" in
  MINGW*|MSYS*|CYGWIN*)
    WIN_SCRIPT="$(cygpath -w "$SCRIPT" 2>/dev/null)"
    [ -n "$WIN_SCRIPT" ] && SCRIPT="$WIN_SCRIPT"
    ;;
esac
export PYTHONIOENCODING=utf-8 PYTHONUTF8=1
if command -v python3 >/dev/null 2>&1; then
  out="$(python3 "$SCRIPT" 2>/dev/null)" && { printf '%s\n' "$out"; exit 0; }
fi
if command -v python >/dev/null 2>&1; then
  out="$(python "$SCRIPT" 2>/dev/null)" && { printf '%s\n' "$out"; exit 0; }
fi
if command -v py >/dev/null 2>&1; then
  out="$(py "$SCRIPT" 2>/dev/null)" && { printf '%s\n' "$out"; exit 0; }
fi
exit 0
