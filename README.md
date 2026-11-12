<div align="center">

<img src="plugin/.claude-plugin/icon.png" alt="Viaduct logo" width="88">

# Viaduct

**Describe a circuit board in plain English. Get a KiCad project you can manufacture.**

A Claude Code plugin that takes a board from idea to Gerbers: requirements, parts, schematic,
placement, routing, checks and ordering files.

<a href="https://github.com/virajrungta/viaduct/releases"><img src="https://img.shields.io/github/v/release/virajrungta/viaduct?label=release&color=2ea44f" alt="Latest release"></a>
<a href="https://github.com/virajrungta/viaduct/actions/workflows/ci.yml"><img src="https://github.com/virajrungta/viaduct/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
<img src="https://img.shields.io/badge/KiCad-9-314cb0" alt="KiCad 9">
<img src="https://img.shields.io/badge/macOS%20%C2%B7%20Windows-555" alt="macOS and Windows">
<a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue" alt="MIT license"></a>

[Website](https://viaduct-pcb.github.io/) · [Getting started](plugin/docs/getting-started.md) · [How it works](plugin/docs/how-it-works.md) · [CLI reference](plugin/docs/cli.md) · [Troubleshooting](plugin/docs/troubleshooting.md)

<a href="https://viaduct-pcb.github.io/#demo"><img src="plugin/docs/images/demo.jpg" alt="Watch the Viaduct demo video: a board described in one sentence, then designed, routed and checked" width="720"></a>

<sub>▶ Watch the demo (about a minute)</sub>

</div>

## What it does

Type one sentence:

```text
/viaduct:design a USB-C powered ESP32-C3 board with an RGB status LED, reset and boot buttons, and a 4-pin sensor header
```

Claude then:

1. **Asks first**: board size, power, which edge each connector sits on, how you'll build it, and anything noise-sensitive.
2. **Picks real parts**: verified building blocks (USB-C, regulators, LiPo charging, ESP32, RP2040, ATmega, LEDs, buttons, sensors) and parts with live JLCPCB stock and prices.
3. **Draws the schematic** from each chip's datasheet and checks every pin.
4. **Lays out the board**: connectors flush to their edges, decoupling capacitors at their pins, noisy parts kept apart. It looks at its own renders and fixes what it sees.
5. **Routes it** (2, 4 or 6 layers) with ground pours, then runs ERC, DRC, electrical and noise checks.
6. **Hands you the files** a manufacturer needs: Gerbers, drill, BOM and pick-and-place, plus a cost estimate.

Everything is a normal **KiCad 9 project** you can open and edit at any point.

<table>
  <tr>
    <td align="center" width="50%">
      <img src="plugin/docs/images/c3_sensor_top.png" alt="ESP32-C3 sensor board, top view" width="100%"><br>
      <sub><b>ESP32-C3 sensor node</b>: 0 DRC errors, antenna keep-out respected,<br>decoupling within 2 mm of every supply pin</sub>
    </td>
    <td align="center" width="50%">
      <img src="plugin/docs/images/c3_sensor_schematic.png" alt="Generated schematic for the ESP32-C3 sensor node" width="100%"><br>
      <sub><b>Its schematic</b>: grouped by function, labelled nets,<br>ERC-clean and editable in KiCad</sub>
    </td>
  </tr>
</table>

## Commands

| Command | What it does |
|---|---|
| `/viaduct:design [idea]` | The whole workflow, from idea to manufacturing files |
| `/viaduct:review [project]` | Reviews any KiCad project and returns a prioritized list of fixes |
| `/viaduct:inquiry [question or design]` | Answers PCB questions, or gives quick feedback on a design, schematic image or Gerbers |
| `/viaduct:fab [project]` | Gerbers, BOM, pick-and-place and an ordering checklist |

A `circuit-reviewer` subagent gives an independent second opinion on any circuit, and the
`kipcb` engine behind all of it can be used on its own ([CLI reference](plugin/docs/cli.md)).

## Install

**1. Install KiCad 9 and Java 21+** (Java runs the autorouter).

| macOS (Terminal, with [Homebrew](https://brew.sh)) | Windows (PowerShell) |
|---|---|
| `brew install --cask kicad` | `winget install KiCad.KiCad` |
| `brew install --cask temurin` | `winget install EclipseAdoptium.Temurin.21.JDK` |
| | `winget install Git.Git` (Claude Code on Windows uses Git Bash) |

**2. Add the plugin to [Claude Code](https://claude.com/claude-code):**

```bash
claude plugin marketplace add virajrungta/viaduct
claude plugin install viaduct@viaduct
```

In the desktop app instead: **Code** tab → **+** → **Plugins** → **Add plugin** → marketplace `virajrungta/viaduct` → **Viaduct**.

**3. Start a new session and design a board:**

```text
/viaduct:design a 30 x 20 mm USB-C LED blinker with an ATtiny85 and an ISP header
```

The first session welcomes you and says if KiCad or Java is missing. Ask Claude to *"run kipcb doctor"*
for a full check. The [getting started guide](plugin/docs/getting-started.md) walks through a first board, opening
it in KiCad and ordering it.

### Settings

Change these with `/plugin configure viaduct@viaduct`, or pass them at install
(`--config fab_house=JLCPCB --config layers=2`).

| Setting | Options | What it changes |
|---|---|---|
| Default PCB manufacturer | JLCPCB · PCBWay · OSH Park · Other | File formats and the design rules Claude aims for |
| How boards get built | Assembled by the manufacturer · Hand soldering | Part sizes and stocked-part preference |
| Default layer count | Auto · 2 · 4 · 6 | Layer count for new boards (Auto compares your design with real boards) |
| Learn from my boards | on · off | Whether kipcb remembers what worked, on your computer only |
| Show design progress in the status bar | on · off | A live progress bar while a board is designed |

### Updating and removing

```bash
claude plugin marketplace update viaduct
claude plugin update viaduct@viaduct
```

Or turn on auto-update: `/plugin` → **Marketplaces** → **viaduct** → **Enable auto-update**.
To remove it: `claude plugin uninstall viaduct@viaduct` (your boards and settings stay on disk).

## Try an example

From a clone of this repo, one command runs the whole pipeline in about 20 seconds:

```bash
plugin/bin/kipcb run plugin/examples/c3_sensor.json
```

```text
READY TO ORDER: ESP32-C3 sensor node
Board     58 x 43 mm, 2 layers, 20 parts, 14 nets
Checks    ERC ok, DRC ok, parity ok, noise 13 pass / 3 warn / 0 fail
Power     U1 (AMS1117-3.3) 5V->3.3V at 363 mA dissipates 0.62 W; SOT-223 handles about 1.0 W
Fab       fab/c3_sensor-gerbers.zip, fab/c3_sensor-bom.csv, fab/c3_sensor-cpl.csv
Time      check 0s, build 10s, route 7s, fab 2s (total 19s)
```

<table>
  <tr>
    <td align="center" width="50%">
      <img src="plugin/docs/images/usb_blinker_angle.png" alt="USB-C ATtiny85 LED blinker" width="100%"><br>
      <sub><a href="examples/usb_blinker.json"><code>usb_blinker.json</code></a>: 30 × 22 mm, ATtiny85, USB-C power, ISP header</sub>
    </td>
    <td align="center" width="50%">
      <img src="plugin/docs/images/usb_blinker_top.png" alt="USB-C LED blinker, top view" width="100%"><br>
      <sub>Routed on top so the bottom stays a solid ground plane</sub>
    </td>
  </tr>
</table>

Each project folder holds the KiCad files, `fab/` (send these to the manufacturer), `previews/` and `reports/`.

## Privacy and what runs on your computer

Viaduct runs locally. It sends no personal data, files or credentials anywhere, and only goes online for:

- **Part lookups**: part numbers and search terms go to JLCPCB's and EasyEDA's public parts APIs (with `curl`) for stock, price and footprint data. Results are cached locally.
- **The autorouter**: `kipcb setup-router` downloads the Freerouting release from GitHub once, after asking you.
- **Datasheets**: Claude may fetch a part's datasheet when a question needs it.

At the start of each session, a short script ([`session-start.sh`](plugin/scripts/session-start.sh)) saves your
settings for kipcb, looks for KiCad and Java (without running KiCad), shows the welcome or update note, and,
unless you turned the status bar option off, adds Viaduct's progress line to `~/.claude/settings.json` when you
don't already have a status line. It never goes online.

| What | macOS | Windows |
|---|---|---|
| Your boards | `hardware/<name>/` in the folder you design in | `hardware\<name>\` in the folder you design in |
| Settings and learning | `~/.local/share/kipcb` | `%LOCALAPPDATA%\kipcb` |
| Downloads and caches | `~/.cache/kipcb` | `%LOCALAPPDATA%\kipcb\cache` |

## Limits

Autorouted boards work but aren't optimal. Switching-regulator layout, RF, controlled impedance and high-speed
signals (USB 480 Mb/s, Ethernet, DDR) need human review or hand routing, and Viaduct flags them rather than
hiding them. Fine-pitch chips like the RP2040 can leave a connection or two to finish by hand. **Always review a
design before ordering boards.**

## Documentation

| Guide | For |
|---|---|
| [Getting started](plugin/docs/getting-started.md) | Installing, your first board, opening it in KiCad, ordering |
| [How it works](plugin/docs/how-it-works.md) | The pipeline, placement, routing, checks and learning |
| [CLI reference](plugin/docs/cli.md) | Every `kipcb` command and environment variable |
| [Design spec format](plugin/skills/design/references/spec-format.md) | The JSON spec: parts, nets, placement hints, custom parts |
| [Circuit patterns](plugin/skills/design/references/circuit-patterns.md) | Proven sub-circuits and values Claude follows |
| [Layout and noise guidelines](plugin/skills/design/references/layout-guidelines.md) | Placement, routing and noise-check criteria |
| [Manufacturing](plugin/skills/design/references/manufacturing.md) | Fab rules, JLCPCB assembly and the ordering checklist |
| [Troubleshooting](plugin/docs/troubleshooting.md) | Common problems and fixes |

## Releases

The latest versions are below. Every version is in [RELEASES.md](plugin/RELEASES.md), with full notes in the
[changelog](plugin/CHANGELOG.md).

| Version | Date | What's new |
|---|---|---|
| [V2.14](https://github.com/virajrungta/viaduct/releases/tag/v2.14) | 2026-11-11 | Plugin directory fix |
| [V2.13](https://github.com/virajrungta/viaduct/releases/tag/v2.13) | 2026-11-11 | Plugin directory fix |
| [V2.12](https://github.com/virajrungta/viaduct/releases/tag/v2.12) | 2026-11-11 | A tidier repository, and an edition for Claude's plugin directory |
| [V2.11](https://github.com/virajrungta/viaduct/releases/tag/v2.11) | 2026-11-08 | A clearer README, with the demo video |
| [V2.10](https://github.com/virajrungta/viaduct/releases/tag/v2.10) | 2026-11-08 | New website address: [viaduct-pcb.github.io](https://viaduct-pcb.github.io/) |
| [V2.9](https://github.com/virajrungta/viaduct/releases/tag/v2.9) | 2026-11-08 | Startup script the plugin directory can read |
| [V2.8](https://github.com/virajrungta/viaduct/releases/tag/v2.8) | 2026-11-07 | Ready for Claude's plugin directory |
| [V2.7](https://github.com/virajrungta/viaduct/releases/tag/v2.7) | 2026-11-06 | What a board will cost, a 3D model for its enclosure, and tighter decoupling around dense chips. |
| [V2.6](https://github.com/virajrungta/viaduct/releases/tag/v2.6) | 2026-11-05 | The plugin is now Viaduct. |

## Contributing

Issues and pull requests are welcome. See [CONTRIBUTING.md](plugin/CONTRIBUTING.md) for the development setup, tests and
release process.

The plugin lives in [`plugin/`](plugin). [`lite/`](lite) is a code-free edition for Claude's plugin directory,
generated from it, which downloads the same engine on first use after asking.

## License

[MIT](LICENSE) © Viraj Rungta
