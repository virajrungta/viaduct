---
name: fab
description: Export manufacturing files (Gerbers, drill, BOM, pick-and-place) from a KiCad project and walk through ordering boards from JLCPCB or another fab. Use when the user wants to order, manufacture, fabricate or get assembly files for a PCB, or asks for Gerbers, a BOM or a CPL/pick-and-place file.
argument-hint: "[project dir or .kicad_pro]"
---

# Fabrication outputs and ordering

`kipcb` is on PATH (fallback `${CLAUDE_PLUGIN_ROOT}/bin/kipcb`).

1. Locate the project (the argument, or the single `.kicad_pro` nearby).
2. Run `kipcb drc <project>`. If there are errors or unconnected items, stop
   and explain them. Offer to fix them (via `/viaduct:design` for kipcb specs, or
   directly in KiCad). `kipcb fab --force` exists, but only use it if the user
   explicitly accepts the risk.
3. Run `kipcb fab <project>`. The output format follows the user's manufacturer
   setting (see `kipcb settings`); pass `--fab jlcpcb` or `--fab generic` to override.
4. Read `fab/<name>-bom.csv`. Flag parts without an LCSC number when the user
   wants JLCPCB assembly, and never make one up: find candidates with
   `kipcb lcsc -s "<part> <package>"` (live stock, basic parts first) and let the
   user confirm, or suggest JLCPCB's BOM tool, hand-soldering or DNP. `kipcb fab`
   also warns about BOM parts that are out of stock at JLCPCB; relay those.
5. Run `kipcb cost <project>` and relay the rough cost (5, 10 and 100 boards,
   per-board price, the priciest parts, extended-part fees). Say it's an
   estimate without shipping; the live quote is the real price. If one part
   dominates or extended fees add up, suggest a cheaper basic part
   (`kipcb lcsc -s ... --basic`) but let the user decide.
6. Mention `fab/<name>.step`, a 3D model of the assembled board for designing
   an enclosure in Fusion 360, Onshape, FreeCAD or SolidWorks.
7. Show `previews/review.png` (render it with `kipcb render <project> --what review`
   if it's missing) so the user sees what they're ordering. `kipcb report <project>`
   prints the summary with the project location and file list.
8. Hand off with the file paths and the ordering checklist from
   `${CLAUDE_PLUGIN_ROOT}/skills/design/references/manufacturing.md`: upload the
   Gerber zip, confirm size/layers/thickness/finish, then upload the BOM and
   CPL for assembly and check rotations in the preview.

Don't place orders, upload files to a fab, or enter payment details on the
user's behalf. Prepare the files and explain the steps; the user does the ordering.
