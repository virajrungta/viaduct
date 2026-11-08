#!/usr/bin/env bash
# SessionStart hook for the Viaduct plugin.
#  - saves the install-time settings where kipcb can read them
#  - welcomes the user after install, and announces new versions after an update
#  - warns (only) when a required tool is missing
# Fast and dependency-free: checks for files, never loads KiCad, never goes online.
# Written so each command stands on its own (no commands hidden inside strings).
set -u

ROOT="${CLAUDE_PLUGIN_ROOT:-}"
if [[ -z "$ROOT" ]]; then
  HERE="$(dirname "${BASH_SOURCE[0]}")"
  ROOT="$(cd "$HERE/.." && pwd)"
fi
DATA="${CLAUDE_PLUGIN_DATA:-$HOME/.claude/plugins/data/pcb}"

# Windows: Claude Code runs hooks in Git Bash. Use the same folders as kipcb's Python side
# (kienv.data_dir / cache_dir): %LOCALAPPDATA%\kipcb instead of ~/.local/share and ~/.cache.
OS_NAME="$(uname -s 2>/dev/null)"
IS_WINDOWS=0
case "$OS_NAME" in MINGW*|MSYS*|CYGWIN*) IS_WINDOWS=1 ;; esac
SETTINGS_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/kipcb"
CACHE="${KIPCB_CACHE:-$HOME/.cache/kipcb}"
if [[ $IS_WINDOWS == 1 && -z "${XDG_DATA_HOME:-}" && -n "${LOCALAPPDATA:-}" ]]; then
  LAD="$(cygpath -u "$LOCALAPPDATA" 2>/dev/null)"
  [[ -z "$LAD" ]] && LAD="$LOCALAPPDATA"
  SETTINGS_DIR="$LAD/kipcb"
  CACHE="${KIPCB_CACHE:-$LAD/kipcb/cache}"
fi
mkdir -p "$DATA" "$SETTINGS_DIR" 2>/dev/null

SETUP="$ROOT/scripts/statusline_setup.py"
if [[ $IS_WINDOWS == 1 ]]; then
  WIN_SETUP="$(cygpath -w "$SETUP" 2>/dev/null)"
  [[ -n "$WIN_SETUP" ]] && SETUP="$WIN_SETUP"
fi

# 1. settings from the install dialog (exported by Claude Code as CLAUDE_PLUGIN_OPTION_<KEY>)
FAB="${CLAUDE_PLUGIN_OPTION_FAB_HOUSE:-JLCPCB}"
BUILD="${CLAUDE_PLUGIN_OPTION_BUILD_METHOD:-Assembled by the manufacturer}"
LAYERS="${CLAUDE_PLUGIN_OPTION_LAYERS:-Auto}"
LAYERS_JSON="${LAYERS//[^0-9]/}"
if [[ -z "$LAYERS_JSON" ]]; then
  LAYERS="auto"
  LAYERS_JSON='"auto"'
fi
LEARN="${CLAUDE_PLUGIN_OPTION_LEARNING:-true}"
LEARN_JSON=true
if [[ "$LEARN" == "false" || "$LEARN" == "0" ]]; then
  LEARN_JSON=false
fi
# JSON-escape the two free-text values (backslashes, then quotes)
FAB_J="${FAB//\\/\\\\}"
FAB_J="${FAB_J//\"/\\\"}"
BUILD_J="${BUILD//\\/\\\\}"
BUILD_J="${BUILD_J//\"/\\\"}"
printf '{"fab_house": "%s", "build_method": "%s", "layers": %s, "learning": %s}\n' \
  "$FAB_J" "$BUILD_J" "$LAYERS_JSON" "$LEARN_JSON" > "$SETTINGS_DIR/settings.json" 2>/dev/null

# stable launcher for Claude Code's status line (the plugin's own folder changes per version):
# "statusLine": {"type": "command", "command": "~/.local/share/kipcb/statusline.sh"}
LAUNCHER="$SETTINGS_DIR/statusline.sh"
cp "$ROOT/scripts/statusline-launcher.sh" "$LAUNCHER" 2>/dev/null
chmod +x "$LAUNCHER" 2>/dev/null
printf '%s\n' "$ROOT" > "$SETTINGS_DIR/plugin-root" 2>/dev/null

# install option "Show design progress in the status bar": set it up (never replacing a status
# line the user already has), or take ours away again when the option is turned off
SHOW_PROGRESS="${CLAUDE_PLUGIN_OPTION_PROGRESS_STATUSLINE:-true}"
ACTION=install
if [[ "$SHOW_PROGRESS" == "false" || "$SHOW_PROGRESS" == "0" ]]; then
  ACTION=uninstall
fi
# a Python that really runs (on Windows "python3" can be the Microsoft Store stub)
export PYTHONUTF8=1
if command -v python3 >/dev/null 2>&1 && python3 -c 'import json' >/dev/null 2>&1; then
  python3 "$SETUP" "$ACTION" >/dev/null 2>&1
elif command -v python >/dev/null 2>&1 && python -c 'import json' >/dev/null 2>&1; then
  python "$SETUP" "$ACTION" >/dev/null 2>&1
elif command -v py >/dev/null 2>&1 && py -c 'import json' >/dev/null 2>&1; then
  py "$SETUP" "$ACTION" >/dev/null 2>&1
fi

# 2. toolchain check (files only)
missing=()
have_kicad=0
if [[ -x /Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli ]]; then have_kicad=1; fi
if [[ -x "$HOME/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli" ]]; then have_kicad=1; fi
if command -v kicad-cli >/dev/null 2>&1; then have_kicad=1; fi
if [[ -n "${KIPCB_KICAD_CLI:-}" ]]; then have_kicad=1; fi
if [[ $IS_WINDOWS == 1 && $have_kicad == 0 ]]; then
  for root in "${KIPCB_KICAD_ROOT:-}" "${ProgramW6432:+$ProgramW6432/KiCad/9.0}" \
              "${PROGRAMFILES:+$PROGRAMFILES/KiCad/9.0}" "${LOCALAPPDATA:+$LOCALAPPDATA/Programs/KiCad/9.0}"; do
    [[ -z "$root" ]] && continue
    unix_root="$(cygpath -u "$root" 2>/dev/null)"
    [[ -z "$unix_root" ]] && unix_root="$root"
    [[ -f "$unix_root/bin/kicad-cli.exe" ]] && have_kicad=1
  done
fi
if [[ $have_kicad == 0 ]]; then
  if [[ $IS_WINDOWS == 1 ]]; then
    missing+=("KiCad 9 (winget install KiCad.KiCad)")
  else
    missing+=("KiCad 9 (https://www.kicad.org/download/)")
  fi
fi
if command -v java >/dev/null 2>&1; then
  java_info="$(java -version 2>&1)"
  jv="$(printf '%s\n' "$java_info" | sed -n 's/.*version "\([0-9]*\).*/\1/p' | head -1)"
  if [[ -n "$jv" && "$jv" -lt 21 ]]; then
    missing+=("Java 21+ for the autorouter (found Java $jv)")
  fi
elif [[ $IS_WINDOWS == 1 ]]; then
  missing+=("Java 21+ for the autorouter (winget install EclipseAdoptium.Temurin.21.JDK)")
else
  missing+=("Java 21+ for the autorouter (macOS: brew install --cask temurin)")
fi
router_missing=1
if [[ -n "${KIPCB_FREEROUTING_JAR:-}" ]]; then router_missing=0; fi
for jar in "$CACHE"/freerouting-*.jar; do
  [[ -f "$jar" ]] && router_missing=0
done

# 3. welcome / update notice
VERSION="$(sed -n 's/.*"version": *"\([^"]*\)".*/\1/p' "$ROOT/.claude-plugin/plugin.json" | head -1)"
SEEN_FILE="$DATA/last-version"
SEEN=""
[[ -f "$SEEN_FILE" ]] && SEEN="$(cat "$SEEN_FILE" 2>/dev/null)"
msg=""
if [[ -z "$SEEN" ]]; then
  msg="Viaduct V$VERSION installed. Try: /viaduct:design a USB-C powered board with an ESP32 and a temperature sensor. Defaults: $FAB, $BUILD, layers $LAYERS (change with /plugin configure viaduct@viaduct)."
elif [[ "$SEEN" != "$VERSION" ]]; then
  msg="Viaduct updated to V$VERSION. What's new: https://github.com/virajrungta/viaduct/releases/tag/v$VERSION"
fi
echo "$VERSION" > "$SEEN_FILE" 2>/dev/null

if (( ${#missing[@]} )); then
  needs=""
  for item in "${missing[@]}"; do
    needs="${needs:+$needs; }$item"
  done
  msg="${msg:+$msg }Viaduct needs: $needs. Run kipcb doctor for details."
fi

context="Viaduct (PCB design plugin) defaults from the user's settings: manufacturer $FAB; build: $BUILD; layers: $LAYERS (auto = let kipcb choose from the design; a number = use it as board.layers); learning ${LEARN}."
if [[ $router_missing == 1 ]]; then
  context="$context Freerouting is not installed yet; ask the user before running kipcb setup-router (downloads ~65 MB)."
fi

# 4. hook output
# JSON-escape the two messages (backslashes, then quotes; neither has newlines)
MSG_J="${msg//\\/\\\\}"
MSG_J="${MSG_J//\"/\\\"}"
CONTEXT_J="${context//\\/\\\\}"
CONTEXT_J="${CONTEXT_J//\"/\\\"}"
printf '{'
if [[ -n "$msg" ]]; then
  printf '"systemMessage": "%s", ' "$MSG_J"
fi
printf '"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "%s"}}\n' "$CONTEXT_J"
