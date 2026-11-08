"""Reference knowledge mined from open-source KiCad designs (built by pcb-knowledge).

`kipcb ref <part>` shows how real designs wire a part: which passives sit on
each pin, their values, and where they go. Layout statistics from real
boards also seed kipcb's local learning.
"""

import json
import os
import re


_DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data")
# The plugin ships the knowledge base split into small files (data/knowledge/: index.json plus
# parts-N.json), so no single file is large. A whole data/knowledge.json (from `pkb install`
# in a dev checkout) is used instead when it is there.
BUNDLED = (os.path.join(_DATA, "knowledge.json") if os.path.exists(os.path.join(_DATA, "knowledge.json"))
           else os.path.join(_DATA, "knowledge"))
SHARD_BYTES = 200 * 1024


def _built(path):
    """The build time a knowledge base records (first lines of the file), or "" if unreadable."""
    if os.path.isdir(path):
        path = os.path.join(path, "index.json")
    try:
        with open(path) as f:
            head = f.read(400)
    except OSError:
        return ""
    m = re.search(r'"built":\s*"([^"]+)"', head)
    return m.group(1) if m else ""


def kb_path():
    """KIPCB_KNOWLEDGE, else the newest of the locally built/installed base and the copy
    shipped with the plugin, so a plugin update never runs on an older local copy and a
    fresh `pkb build` is used straight away."""
    env = os.environ.get("KIPCB_KNOWLEDGE")
    if env:
        return env
    from . import kienv
    local = os.path.join(kienv.data_dir(), "knowledge.json")
    if not os.path.exists(local):
        return BUNDLED
    return local if _built(local) >= _built(BUNDLED) else BUNDLED


_cache = {}


def load(path=None):
    path = path or kb_path()
    if path in _cache:
        return _cache[path]
    try:
        if os.path.isdir(path):
            with open(os.path.join(path, "index.json")) as f:
                kb = json.load(f)
            kb["parts"] = {}
            for name in sorted(n for n in os.listdir(path) if n.startswith("parts-") and n.endswith(".json")):
                with open(os.path.join(path, name)) as f:
                    kb["parts"].update(json.load(f))
        else:
            with open(path) as f:
                kb = json.load(f)
    except (OSError, ValueError):
        kb = None
    _cache[path] = kb
    return kb


def find(kb, query):
    """Best-matching part keys for a symbol id, part name or value."""
    q = query.strip().upper()
    parts = kb.get("parts", {})
    if q in parts:
        return [q]
    if q in kb.get("aliases", {}):
        return [kb["aliases"][q]]
    tail = q.split(":")[-1]
    if tail in parts:
        return [tail]
    hits = [k for k in parts if tail in k or k in tail]
    return sorted(hits, key=lambda k: (-parts[k]["designs"], len(k)))[:5]


def print_part(query, path=None):
    kb = load(path)
    if kb is None:
        print("No knowledge base installed at %s.\nBuild one with the pcb-knowledge repo "
              "(pkb fetch / extract / build / install)." % (path or kb_path()))
        return 2
    keys = find(kb, query)
    if not keys:
        print("%r is not in the knowledge base (%d parts from %d open-source projects)." % (
            query, len(kb["parts"]), kb.get("projects", 0)))
        return 1
    key = keys[0]
    info = kb["parts"][key]
    n = info["designs"]
    print("%s: seen in %d open-source design repositories" % (key, n))
    if info.get("lib"):
        print("  symbol:     %s" % info["lib"])
    if info.get("footprints"):
        print("  footprints: %s" % ", ".join(info["footprints"]))
    print("  pin wiring (share of designs):")
    for pin, pats in sorted(info["pins"].items(), key=lambda kv: -kv[1][0][1]):
        txt = "; ".join("%s %d%%" % (p, round(100.0 * c / n)) for p, c in pats)
        print("    %-14s %s" % (pin, txt))
    if len(keys) > 1:
        print("  (also matched: %s)" % ", ".join(keys[1:]))
    print("Treat these as common practice, not a spec: the datasheet wins.")
    return 0


def layout_prior(layers=2):
    """Area per pad (mm²) at the 25th/50th percentile of real routed boards, or None."""
    kb = load()
    if not kb:
        return None
    d = (kb.get("layout", {}).get("area_per_pad_mm2") or {}).get(str(layers))
    if not d or d.get("n", 0) < 5:
        return None
    return d


def routed_density(layers=2):
    """Connections per cm² of fully routed real boards with this layer count (p50/p90), or None."""
    kb = load()
    d = ((kb or {}).get("design_rules", {}).get("routed_density_connections_per_cm2") or {}).get(str(layers))
    if not d or d.get("n", 0) < 5:
        return None
    return d


def pitch_rules(pitch):
    """What real boards use to reach pads at this pitch: {"track_at_pad_mm": {...}, "clearance_mm": {...}}."""
    kb = load()
    rules = (kb or {}).get("design_rules", {}).get("by_pitch") or {}
    for b in ("0.4", "0.5", "0.65", "0.8", "1"):
        if pitch <= float(b) + 0.02:
            r = rules.get(b)
            return r if r and r.get("footprints", 0) >= 5 else None
    return None


def placement():
    """Placement statistics of real routed boards (pcb-knowledge `pkb placement`), or None."""
    kb = load()
    pl = (kb or {}).get("placement")
    return pl if pl and pl.get("boards", 0) >= 30 else None


def shard(src, dest):
    """Split a knowledge.json into dest/index.json (everything but the parts, "built" first)
    and dest/parts-N.json files of about SHARD_BYTES each."""
    import shutil
    with open(src) as f:
        kb = json.load(f)
    parts = kb.pop("parts", {})
    if os.path.isdir(dest):
        shutil.rmtree(dest)
    os.makedirs(dest)
    index = {"version": kb.get("version"), "built": kb.get("built")}
    index.update(kb)
    with open(os.path.join(dest, "index.json"), "w") as f:
        json.dump(index, f, separators=(",", ":"))
    chunk, size, n = {}, 0, 0
    for key in sorted(parts):
        item = len(json.dumps({key: parts[key]}, separators=(",", ":")))
        if chunk and size + item > SHARD_BYTES:
            with open(os.path.join(dest, "parts-%02d.json" % n), "w") as f:
                json.dump(chunk, f, separators=(",", ":"))
            chunk, size, n = {}, 0, n + 1
        chunk[key] = parts[key]
        size += item
    if chunk:
        with open(os.path.join(dest, "parts-%02d.json" % n), "w") as f:
            json.dump(chunk, f, separators=(",", ":"))
    return n + 1


if __name__ == "__main__":
    import sys
    if len(sys.argv) == 4 and sys.argv[1] == "shard":
        print("%d parts files" % shard(sys.argv[2], sys.argv[3]))
    else:
        sys.exit("usage: python3 -m kipcb.knowledge shard <knowledge.json> <dest-dir>")
