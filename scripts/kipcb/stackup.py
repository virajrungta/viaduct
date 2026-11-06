"""Copper stackups for boards with more than 2 layers: solid planes on the inner layers.

A 4-layer board earns its cost through its planes, not through two more routing layers:
a ground plane right under the top layer gives every signal a short return path (far
less noise and EMI), and a power plane feeds every chip with low impedance. The
default stackups are the usual ones (and JLCPCB's default layer order):

    4 layers   F.Cu signal | In1.Cu GND plane | In2.Cu power plane | B.Cu signal
    6 layers   F.Cu signal | In1.Cu GND plane | In2.Cu signal | In3.Cu signal |
               In4.Cu power plane | B.Cu signal

Plane layers are marked as power layers, so the autorouter never runs tracks on them:
it connects GND and the plane's rail with vias. A spec can choose the nets:

    "board": {"layers": 4, "planes": {"In1.Cu": "GND", "In2.Cu": "+5V"}}

and "planes": {} keeps every inner layer for signals (no planes).
"""

import re

from .kicad import pcbnew

FOUR_LAYER_VOTE = 0.62    # share of similar real boards on 4+ layers that tips "auto" to 4
# Kept conservative: today kipcb routes fine-pitch QFNs (RP2040...) more reliably on 2
# layers, so "auto" picks 4 only when 2 layers is a poor fit, never just for pin pitch.
# parts whose signals want a reference plane right under them (impedance, return paths)
HIGH_SPEED = re.compile(r"LAN8[0-9]|KSZ8|KSZ9|DP83|RTL8[0-9]|88E1|SDRAM|DDR|LPDDR|HDMI|TFP4|USB3|TUSB[0-9]|MIPI|"
                        r"PCIE|SERDES|GTX|ETHERNET_PHY", re.I)

DEFAULT = {4: [("In1.Cu", "GND"), ("In2.Cu", "POWER")],
           6: [("In1.Cu", "GND"), ("In4.Cu", "POWER")]}


def _main_rail(design, ground):
    """The supply rail with the most pins: the one worth a whole plane."""
    rails = []
    for net in (getattr(design, "power_nets", None) or []):
        if net != ground and net in design.nets:
            rails.append((len(design.nets[net]), net))
    if not rails:
        from .wiring import net_class
        rails = [(len(p), n) for n, p in design.nets.items() if n != ground and net_class(n) == "PWR"]
    return max(rails)[1] if rails else None


def plan(design):
    """{"In1.Cu": "GND", "In2.Cu": "+3V3"} for this design, or {} (2 layers / no planes)."""
    layers = int(design.board.get("layers", 2))
    if layers <= 2:
        return {}
    ground = design.board.get("ground_pour") or "GND"
    if "planes" in design.board:
        return {k: v for k, v in (design.board.get("planes") or {}).items() if v}
    out = {}
    for layer, role in DEFAULT.get(layers, DEFAULT[4]):
        net = ground if role == "GND" else _main_rail(design, ground)
        if net and net in design.nets:
            out[layer] = net
    return out


def check(design):
    """Spec errors for the planes (unknown layer or net, a plane on an outer layer)."""
    errors = []
    layers = int(design.board.get("layers", 2))
    inner = ["In%d.Cu" % i for i in range(1, max(layers - 1, 1))]
    for layer, net in (design.board.get("planes") or {}).items():
        if layer not in inner:
            errors.append("board.planes: %s isn't an inner layer of a %d-layer board (use %s)" % (
                layer, layers, ", ".join(inner) or "4+ layers"))
        elif net and net not in design.nets:
            errors.append("board.planes: net %s for %s isn't in the design" % (net, layer))
    if design.board.get("planes") and layers <= 2:
        errors.append("board.planes needs \"layers\": 4 or 6")
    return errors


def apply(board, planes, clearance=0.3):
    """Mark plane layers as power layers and pour each one over the whole board."""
    if not planes:
        return 0
    pn = pcbnew()
    from .route import add_pours
    # a pad reaches its plane through a via right beside it: a net class's big power via
    # (0.8/0.4 mm) doesn't fit between closely spaced pads, so the router gave up on the
    # whole plane net. The standard via carries ~1 A; plane nets use it.
    ns = board.GetDesignSettings().m_NetSettings
    default = ns.GetDefaultNetclass()
    for net in set(planes.values()):
        ni = board.FindNet(net)
        if ni is None:
            continue
        name = ni.GetNetClassName() if hasattr(ni, "GetNetClassName") else ""
        nc = ns.GetNetClassByName(name) if name and ns.HasNetclass(name) else None
        if nc is not None and name != default.GetName() and nc.GetViaDiameter() > default.GetViaDiameter():
            nc.SetViaDiameter(default.GetViaDiameter())
            nc.SetViaDrill(default.GetViaDrill())
    n = 0
    for name, net in planes.items():
        layer = board.GetLayerID(name)
        if layer < 0:
            continue
        board.SetLayerType(layer, pn.LT_POWER)
        n += add_pours(board, net, clearance, layers=[layer])
    return n


def choose(design):
    """Layer count for a spec with "layers": "auto" (or none): (layers, [reasons]).

    4 layers when the design needs it: a BGA, a high-speed interface (Ethernet PHY, DDR,
    HDMI, USB 3...), or when a clear majority of the real routed boards that look like it
    (pads, connections, fine-pitch share) use 4+ layers.
    Otherwise 2, which is cheaper. 6 layers only on request."""
    reasons = []
    for c in design.components:
        text = "%s %s %s" % (c.value, c.symbol_id, c.footprint_id)
        if "BGA" in c.footprint_id.upper():
            reasons.append("%s (%s) is a BGA" % (c.ref, c.value))
        elif HIGH_SPEED.search(text):
            reasons.append("%s (%s) carries high-speed signals that want a plane under them" % (c.ref, c.value))
    from . import sizemodel
    f = sizemodel.features(design)
    share, n = sizemodel.layer_vote(f)
    if share is not None and share >= FOUR_LAYER_VOTE:
        reasons.append("%d of the %d most similar real boards use 4+ layers" % (round(share * n), n))
    elif share is None and f["conns"] >= 160:          # no knowledge base: where real boards switch
        reasons.append("%d connections (real designs mostly go to 4 layers above ~200)" % f["conns"])
    if reasons:
        return 4, reasons
    if share is not None and share >= 0.35:
        return 2, ["2 layers route this reliably (%d of the %d most similar real boards use 4+; "
                   "ask for \"layers\": 4 for planes)" % (round(share * n), n)]
    why = ("only %d of the %d most similar real boards use 4+ layers" % (round(share * n), n)) if share is not None \
        else "a simple design (%d connections)" % f["conns"]
    return 2, [why]
