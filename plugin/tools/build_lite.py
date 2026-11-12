"""Build the Claude-directory edition of Viaduct (the repo's lite/ folder) from plugin/.

Claude's plugin directory only lists plugins from non-Verified organizations when they
contain no code: Markdown, text, JSON, YAML and images only, no hooks, no bin/. So the
directory edition ships just the skills, the reviewer agent and their references; on
first use the skills ask the user, then download the matching kipcb engine (this repo at
the same version tag) into ~/.viaduct/engine/<version>/.

    python3 tools/build_lite.py            # from plugin/: writes ../lite
    python3 tools/build_lite.py OUT_DIR    # anywhere else (used by the tests)
"""
import json
import os
import shutil
import sys

PLUGIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(PLUGIN)
ALLOWED = (".md", ".json", ".png")
MAX_BYTES = 256 * 1024

ENGINE = """## The kipcb engine

This plugin drives `kipcb`, Viaduct's open-source KiCad engine (MIT,
https://github.com/virajrungta/viaduct), which runs on the user's computer.
Below, `kipcb` means `"$HOME/.viaduct/engine/{v}/plugin/bin/kipcb"`; always call
it by that full path. Before the first kipcb command in a session:

1. Check it's there: `test -x "$HOME/.viaduct/engine/{v}/plugin/bin/kipcb" && echo installed`
2. If it isn't, tell the user Viaduct needs its engine: release V{v} of the
   open-source Viaduct repo, downloaded once from GitHub (about 3 MB) into
   `~/.viaduct/engine/{v}`. Ask with AskUserQuestion before downloading. If they
   agree, run these three commands:

   ```bash
   mkdir -p "$HOME/.viaduct/engine/{v}"
   curl -fsSL -o "$HOME/.viaduct/engine/v{v}.tar.gz" https://github.com/virajrungta/viaduct/archive/refs/tags/v{v}.tar.gz
   tar -xzf "$HOME/.viaduct/engine/v{v}.tar.gz" -C "$HOME/.viaduct/engine/{v}" --strip-components=1
   ```

   Then run `kipcb doctor` and tell the user plainly what's missing, if anything
   (KiCad 9 and Java 21+; `kipcb doctor` prints the install commands). If they
   decline, say that boards can't be built or checked without it, and help with
   what doesn't need it.
"""

SAVE = """
The user's defaults (manufacturer, build method, layer count, learning) are in
`kipcb settings`: JLCPCB, assembled by the manufacturer, auto layers and learning on
until the user changes them. When the user asks for different defaults, save them,
e.g. `kipcb settings --save --fab PCBWay --build "Hand soldering" --layers 4 --learning false`.
"""

ON_PATH = "`kipcb` is on PATH (fallback `${CLAUDE_PLUGIN_ROOT}/bin/kipcb`)."


def _sub(text, old, new, where):
    if old not in text:
        sys.exit("build_lite: %s no longer contains %r; update tools/build_lite.py" % (where, old[:60]))
    return text.replace(old, new)


def _engine(v, save):
    return ENGINE.format(v=v) + (SAVE.format(v=v) if save else "")


def skill(name, text, v):
    where = "skills/%s/SKILL.md" % name
    if name == "design":
        text = _sub(text, "`kipcb` (on PATH; fallback\n`${CLAUDE_PLUGIN_ROOT}/bin/kipcb`) turns",
                    "`kipcb` (see *The kipcb engine* below) turns", where)
        text = _sub(text, "\n## Work efficiently", "\n" + _engine(v, True) + "\n## Work efficiently", where)
        text = _sub(text, "- The session-start hook already checked the toolchain; run `kipcb doctor`\n"
                          "  only if it reported something missing.",
                    "- `kipcb doctor` checks the toolchain; run it after installing the engine\n"
                    "  or when a step fails.", where)
        text = _sub(text, "The user's defaults (manufacturer, build method, layers) are in the session\n"
                          "context and in `kipcb settings`",
                    "The user's defaults (manufacturer, build method, layers) are in\n"
                    "`kipcb settings` (see *The kipcb engine* above)",
                    where)
        text = _sub(text, "Claude Code's status bar also shows the bar live when the user kept the\n"
                          "plugin's \"Show design progress in the status bar\" option on (the default);\n"
                          "nothing to set up.\n", "", where)
        return text
    text = _sub(text, " " + ON_PATH if " " + ON_PATH in text else ON_PATH + "\n", "", where)
    # the engine section goes after the skill's first heading line
    head, sep, rest = text.partition("\n# ")
    title, nl, body = rest.partition("\n")
    return head + sep + title + nl + "\n" + _engine(v, name == "fab") + body


def agent(text, v):
    return _sub(text, "(`kipcb` is on PATH; if not, look for `bin/kipcb` in the plugin root.)",
                "(`kipcb` is `\"$HOME/.viaduct/engine/%s/plugin/bin/kipcb\"`; if it's missing, say so\n"
                "   and review from the spec and datasheets alone.)" % v, "agents/circuit-reviewer.md")


README = """# Viaduct for Claude's plugin directory

This is the edition of [Viaduct](https://viaduct-pcb.github.io/) listed in Claude's plugin
directory. It holds only the skills, the circuit-reviewer agent and their reference
guides. It's built from [`plugin/`](../plugin) by `plugin/tools/build_lite.py`, so don't
edit it by hand.

**What runs on your computer**: the first time you use a Viaduct command, Claude asks
before downloading Viaduct's open-source engine (`kipcb`, release V{v} of
[this repository](https://github.com/virajrungta/viaduct), about 3 MB) into
`~/.viaduct/engine/{v}`. kipcb drives KiCad 9 on your computer. It goes online only for
JLCPCB/EasyEDA part lookups and, after asking, to download the Freerouting autorouter.
It sends no personal data, files or credentials anywhere.

Install it from Claude's plugin directory (search for **Viaduct** under Plugins). You need
KiCad 9 and Java 21+. See the [main README](../README.md) for what Viaduct does,
and the [privacy section](../README.md#privacy-and-what-runs-on-your-computer) for details.
"""


def build(out, version=None):
    manifest = json.load(open(os.path.join(PLUGIN, ".claude-plugin", "plugin.json")))
    v = version or manifest["version"]
    if os.path.isdir(out):
        shutil.rmtree(out)
    os.makedirs(os.path.join(out, ".claude-plugin"))

    manifest["version"] = v
    manifest.pop("userConfig", None)     # the directory can't check option values used in skills
    manifest["description"] = (
        "Describe a circuit board and get a manufacturable KiCad PCB: requirements, parts, "
        "schematic, placement, autorouting, ERC/DRC and fab outputs. Downloads its open-source "
        "engine on first use, after asking.")
    with open(os.path.join(out, ".claude-plugin", "plugin.json"), "w") as f:
        f.write(json.dumps(manifest, indent=2) + "\n")
    shutil.copy(os.path.join(PLUGIN, ".claude-plugin", "icon.png"), os.path.join(out, ".claude-plugin"))

    for root, _dirs, files in os.walk(os.path.join(PLUGIN, "skills")):
        for fn in files:
            if not fn.endswith(".md"):
                continue
            src = os.path.join(root, fn)
            rel = os.path.relpath(src, PLUGIN)
            text = open(src, encoding="utf-8").read()
            if fn == "SKILL.md":
                text = skill(os.path.basename(root), text, v)
            dest = os.path.join(out, rel)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, "w", encoding="utf-8", newline="\n") as f:
                f.write(text)

    os.makedirs(os.path.join(out, "agents"))
    for fn in os.listdir(os.path.join(PLUGIN, "agents")):
        text = open(os.path.join(PLUGIN, "agents", fn), encoding="utf-8").read()
        if fn == "circuit-reviewer.md":
            text = agent(text, v)
        with open(os.path.join(out, "agents", fn), "w", encoding="utf-8", newline="\n") as f:
            f.write(text)

    with open(os.path.join(out, "README.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write(README.format(v=v))
    if os.path.exists(os.path.join(REPO, "LICENSE")):
        shutil.copy(os.path.join(REPO, "LICENSE"), out)
    problems = check(out)
    if problems:
        sys.exit("build_lite: " + "; ".join(problems))
    return out


def check(out):
    """What Claude's plugin directory would refuse from a non-Verified organization."""
    problems = []
    for root, dirs, files in os.walk(out):
        for d in dirs:
            if d in ("bin", "hooks"):
                problems.append("%s/ folder" % os.path.relpath(os.path.join(root, d), out))
        for fn in files:
            p = os.path.join(root, fn)
            rel = os.path.relpath(p, out)
            data = open(p, "rb").read()
            if not (fn.endswith(ALLOWED) or fn == "LICENSE"):
                problems.append("%s: file type not allowed" % rel)
            if not fn.endswith(".png"):
                if len(data) > MAX_BYTES:
                    problems.append("%s: over 256 KiB" % rel)
                if data.startswith(b"#!") or b"\0" in data:
                    problems.append("%s: starts with #! or has NUL bytes" % rel)
                try:
                    data.decode("utf-8")
                except UnicodeDecodeError:
                    problems.append("%s: not UTF-8" % rel)
    manifest = json.load(open(os.path.join(out, ".claude-plugin", "plugin.json")))
    if "hooks" in manifest or "mcpServers" in manifest:
        problems.append("plugin.json declares hooks or servers")
    return problems


if __name__ == "__main__":
    print("built", build(sys.argv[1] if len(sys.argv) > 1 else os.path.join(REPO, "lite")))
