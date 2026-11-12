# Viaduct for Claude's plugin directory

This is the edition of [Viaduct](https://viaduct-pcb.github.io/) listed in Claude's plugin
directory. It holds only the skills, the circuit-reviewer agent and their reference
guides. It's built from [`plugin/`](../plugin) by `plugin/tools/build_lite.py`, so don't
edit it by hand.

**What runs on your computer**: the first time you use a Viaduct command, Claude asks
before downloading Viaduct's open-source engine (`kipcb`, release V2.13 of
[this repository](https://github.com/virajrungta/viaduct), about 3 MB) into
`~/.viaduct/engine/2.13`. kipcb drives KiCad 9 on your computer. It goes online only for
JLCPCB/EasyEDA part lookups and, after asking, to download the Freerouting autorouter.
It sends no personal data, files or credentials anywhere.

Install it from Claude's plugin directory (search for **Viaduct** under Plugins). You need
KiCad 9 and Java 21+. See the [main README](../README.md) for what Viaduct does,
and the [privacy section](../README.md#privacy-and-what-runs-on-your-computer) for details.
