"""What a board costs to have made: bare boards, assembly and parts, for a few quantities.

A rough JLCPCB model (data/pricing.json, with its sources and date): bare-board price by
layer count and area, Economic PCBA (setup fee, a fee per solder joint, a loading fee per
extended part), and part prices from JLCPCB's live parts library (lcsc.py). Shipping,
tax and promotions are left out, so the live quote at jlcpcb.com/quote is the real price;
this answers "roughly how much, and what makes it expensive?" before ordering.
"""

import csv
import json
import math
import os

from . import paths

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data")
QUANTITIES = (5, 10, 100)


def pricing():
    with open(os.path.join(DATA, "pricing.json")) as f:
        return json.load(f)


def pcb_price(w, h, layers, qty, model=None):
    """Bare boards: JLCPCB's promo price when it applies, else area x rate, with a floor."""
    m = (model or pricing())["pcb"]
    layers = 2 if layers <= 2 else (4 if layers <= 4 else 6)
    for p in m["promo"]:
        if p["layers"] == layers and qty <= p["qty"] and max(w, h) <= max(p["max_w"], p["max_h"]) \
                and min(w, h) <= min(p["max_w"], p["max_h"]):
            return p["price"]
    area = (w * h) / 1e6 * qty
    return round(max(m["minimum"][str(layers)], area * m["per_m2"][str(layers)]), 2)


def assembly_price(joints, extended, qty, model=None):
    """Economic PCBA: one setup fee, a fee per solder joint per board, and a loading fee
    for each extended (non-basic, non-preferred) part type."""
    a = (model or pricing())["assembly"]
    return round(a["setup"] + a["per_joint"] * joints * qty + a["extended_part_fee"] * extended, 2)


def estimate(w, h, layers, lines, joints, quantities=QUANTITIES, model=None):
    """lines: [{"refs": [...], "qty": n, "lcsc": code, "price": unit or None, "class": str}].
    Returns {"rows": [{qty, pcb, assembly, parts, total, each}], "extended": [...], "unpriced": [...]}."""
    model = model or pricing()
    extended = sorted({l["lcsc"] for l in lines if l.get("class") == "extended"})
    unpriced = [", ".join(l["refs"]) for l in lines if l.get("price") is None]
    rows = []
    for q in quantities:
        parts = sum((l.get("price") or 0.0) * l["qty"] * q for l in lines)
        pcb = pcb_price(w, h, layers, q, model)
        asm = assembly_price(joints, len(extended), q, model)
        total = pcb + asm + parts
        rows.append({"qty": q, "pcb": round(pcb, 2), "assembly": round(asm, 2), "parts": round(parts, 2),
                     "total": round(total, 2), "each": round(total / q, 2)})
    # what drives the cost at the middle quantity: the priciest lines and the extended fees
    drivers = sorted((((l.get("price") or 0.0) * l["qty"], l) for l in lines), key=lambda t: -t[0])[:3]
    return {"rows": rows, "extended": extended, "unpriced": unpriced,
            "drivers": [{"refs": l["refs"], "lcsc": l["lcsc"], "per_board": round(v, 2)} for v, l in drivers if v > 0],
            "as_of": model.get("as_of"), "currency": model.get("currency", "USD")}


def _bom_lines(bom_csv):
    lines = []
    with open(bom_csv, newline="") as f:
        for r in csv.DictReader(f):
            refs = [x.strip() for x in (r.get("Designator") or "").replace(";", ",").split(",") if x.strip()]
            code = (r.get("LCSC Part #") or "").strip()
            try:
                qty = int(r.get("Qty") or len(refs))
            except ValueError:
                qty = len(refs)
            lines.append({"refs": refs, "qty": qty, "lcsc": code, "value": r.get("Comment", "")})
    return lines


def _joints(pcb_path, refs):
    """Solder joints JLCPCB assembles: pads of the parts it places (in the BOM with an LCSC number)."""
    from .kicad import pcbnew
    board = pcbnew().LoadBoard(pcb_path)
    n = 0
    for fp in board.GetFootprints():
        if fp.GetReference() in refs:
            n += len({p.GetNumber() for p in fp.Pads() if p.GetNumber()}) or len(list(fp.Pads()))
    return n


def run(pdir, name, quiet=False):
    """Estimate from a project's fab outputs; writes reports/cost.json. None when it can't."""
    from . import lcsc, ui
    bom = os.path.join(paths.fab(pdir), "%s-bom.csv" % name)
    pcb = os.path.join(pdir, name + ".kicad_pcb")
    if not os.path.exists(bom) or not os.path.exists(pcb):
        if not quiet:
            ui.always("no BOM yet: run `kipcb fab %s` first" % pdir)
        return None
    lines = _bom_lines(bom)
    codes = [l["lcsc"] for l in lines if l["lcsc"]]
    info = lcsc.lookup(codes) if codes and os.environ.get("KIPCB_OFFLINE") != "1" else {}
    if any(v.get("error") for v in info.values()):
        info = {}
    for l in lines:
        i = info.get(l["lcsc"]) or {}
        l["price"] = i.get("price") if i.get("found") else None
        l["class"] = i.get("class")
    assembled = {r for l in lines if l["lcsc"] for r in l["refs"]}
    joints = _joints(pcb, assembled)
    b = paths.load_json(os.path.join(paths.reports(pdir), "build.json"), {}) or {}
    w, h, layers = b.get("width"), b.get("height"), int(b.get("layers") or 2)
    if not w:
        from .kicad import pcbnew
        bb = pcbnew().LoadBoard(pcb).GetBoardEdgesBoundingBox()
        w, h = bb.GetWidth() / 1e6, bb.GetHeight() / 1e6
        layers = pcbnew().LoadBoard(pcb).GetCopperLayerCount()
    est = estimate(w, h, layers, lines, joints)
    est.update({"board": {"width": w, "height": h, "layers": layers}, "joints": joints, "offline": not info})
    paths.save_json(os.path.join(paths.reports(pdir), "cost.json"), est)
    if not quiet:
        print(text(est))
    return est


def text(est):
    cur = "$" if est.get("currency", "USD") == "USD" else est["currency"] + " "
    b = est["board"]
    out = ["Cost estimate (JLCPCB, Economic PCBA, %s prices; shipping not included)" % est.get("as_of", ""),
           "Board %.0f x %.0f mm, %d layers, %d solder joints assembled" % (b["width"], b["height"], b["layers"], est["joints"]),
           "",
           "  boards     pcb   assembly     parts      total   per board"]
    for r in est["rows"]:
        out.append("  %6d  %6s   %8s  %8s  %9s   %9s" % (r["qty"], cur + "%.2f" % r["pcb"], cur + "%.2f" % r["assembly"],
                                                        cur + "%.2f" % r["parts"], cur + "%.2f" % r["total"],
                                                        cur + "%.2f" % r["each"]))
    if est.get("offline"):
        out.append("\n  parts not priced: JLCPCB's parts library couldn't be reached")
    if est["drivers"]:
        out.append("\n  priciest parts per board: " + "; ".join(
            "%s %s%.2f" % (",".join(d["refs"][:3]), cur, d["per_board"]) for d in est["drivers"]))
    if est["extended"]:
        out.append("  extended parts (+%s3 loading fee each): %s" % (cur, ", ".join(est["extended"])))
    if est["unpriced"]:
        out.append("  no price (no LCSC number or not found): %s" % "; ".join(est["unpriced"]))
    out.append("  real price: upload the Gerbers, BOM and CPL at jlcpcb.com/quote")
    return "\n".join(out)
