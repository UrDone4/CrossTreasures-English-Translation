#!/usr/bin/env python3
"""Repaint the four skill/potion triangles on the dungeon (battle) lower screen.

`madu_battle_<class>.narc` members 0-2 / 3-5 / 6-8 are three tall background layers
(one per skill page: base actions, skill 1, skill 2). Each holds the four triangles
(A right, B bottom, X top, Y left) twice -- once spread out and once assembled -- so
every ink group found is painted. The triangle art and the vertical/horizontal lettering
convention are the same as the skill screen, so this reuses skill_panels' layout.

Buttons are told apart by geometry: vertical names are A (right) or Y (left); of the
horizontal ones, going down the layer they run B, X, X, B (checked against the icons
in the preview).

    battle_panels.py <class> <page>     preview to work/gfx/battle_panels/
"""

import collections
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import skill_panels as sp  # noqa: E402
from bgtext import BgLayer, load_font  # noqa: E402

# page -> {button: name}
BASE = {"A": "Attack", "X": "Life Potion", "Y": "Mana Potion"}
PAGES = {
    "soldier": [
        dict(BASE, B="Power Attack"),
        {"A": "Shield Bash", "B": "Charge", "X": "War Cry", "Y": "Cheer"},
        {"A": "Spin Slash", "B": "Jump Slash", "X": "Vacuum Slash", "Y": "Spirit Flame"},
    ],
    "magic": [
        dict(BASE, B="Mana Drain"),
        {"A": "Poison Sting", "B": "Sleep", "X": "Ultimate", "Y": "Stasis"},
        {"A": "Fireball", "B": "Deep Freeze", "X": "Inferno", "Y": "Ice Lance"},
    ],
    "priest": [
        dict(BASE, B="Power Stamp"),
        {"A": "Knock Away", "B": "Wide Swing", "X": "Healas", "Y": "Curas"},
        {"A": "Lightning", "B": "Love Pulse", "X": "Thunderclap", "Y": "Love Beam"},
    ],
    "thief": [
        dict(BASE, B="Quick Act"),
        {"A": "Hand Bomb", "B": "Time Bomb", "X": "Dash Thrust", "Y": "Quick Charge"},
        {"A": "Double Slash", "B": "Blade Storm", "X": "Poison Shot", "Y": "Paralyze Shot"},
    ],
}


def ink_groups(layer, gap=9):
    """Connected groups of lettering pixels (dilated by `gap`)."""
    pts = set()
    for y in range(layer.height):
        for x in range(layer.width):
            if sp.is_ink(layer.rgb_at(x, y)):
                pts.add((x, y))
    seen, groups = set(), []
    cell = collections.defaultdict(list)
    for p in pts:
        cell[(p[0] // gap, p[1] // gap)].append(p)
    for p in sorted(pts):
        if p in seen:
            continue
        stack, grp = [p], []
        seen.add(p)
        while stack:
            q = stack.pop()
            grp.append(q)
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    for r in cell.get((q[0] // gap + dx, q[1] // gap + dy), ()):
                        if r not in seen and abs(r[0] - q[0]) <= gap and abs(r[1] - q[1]) <= gap:
                            seen.add(r)
                            stack.append(r)
        if len(grp) >= 12:
            groups.append(grp)
    return groups


def make_panel(layer, grp):
    p = sp.Panel.__new__(sp.Panel)
    xs = [q[0] for q in grp]
    ys = [q[1] for q in grp]
    hist = collections.Counter(layer.rgb_at(*q) for q in grp)
    p.bbox = (min(xs), min(ys), max(xs) + 1, max(ys) + 1)
    p.ink = hist.most_common(1)[0][0]
    w, h = p.bbox[2] - p.bbox[0], p.bbox[3] - p.bbox[1]
    p.vertical = h > w * 1.6
    p.cx, p.cy = (p.bbox[0] + p.bbox[2]) // 2, (p.bbox[1] + p.bbox[3]) // 2
    b = p.bbox
    p.clear = (b[0] - 2, b[1] - 2, b[2] + 2, b[3] + 2)
    p.keeps = p._backdrop(layer)
    return p


REDRAW = os.path.join(os.path.dirname(HERE), "work", "redraw")
REDRAW_DONE = os.path.join(os.path.dirname(HERE), "work", "redraw_done")
BAND_Y = 512          # the redraw PNGs hold layer rows 512-767


class _Rgba:
    """Minimal stand-in for a Pillow image, backed by ngfx.read_png.

    The redraw PNGs are 8-bit RGBA and non-interlaced, which the in-repo reader
    already handles, so this avoids a hard Pillow dependency (Homebrew's Python
    refuses `pip install` under PEP 668). If some other editor ever writes a
    palette or interlaced PNG, _open falls back to Pillow.
    """

    __slots__ = ("width", "height", "_rows")

    def __init__(self, width, height, rows):
        self.width, self.height, self._rows = width, height, rows

    def getpixel(self, xy):
        x, y = xy
        row = self._rows[y]
        o = x * 4
        return (row[o], row[o + 1], row[o + 2], row[o + 3])


def _open(path):
    try:
        from ngfx import read_png
        w, h, rows = read_png(path)
        return _Rgba(w, h, rows)
    except Exception:
        from PIL import Image          # only needed for exotic PNG flavours
        return Image.open(path).convert("RGBA")


def load_redraw(cls, page):
    """Hand-redrawn art for one page, aligned to the exported original.

    work/redraw/<cls>_page<N>.png is the original with the lettering pixels magenta;
    work/redraw_done/ holds the same file with the holes painted in. The editor may
    have moved the canvas, so the offset is found by matching the untouched pixels.
    Returns (original, done, (dx, dy)) or None.
    """
    name = "%s_page%d.png" % (cls, page)
    a_path, b_path = os.path.join(REDRAW, name), os.path.join(REDRAW_DONE, name)
    if not (os.path.exists(a_path) and os.path.exists(b_path)):
        return None
    a = _open(a_path)
    b = _open(b_path)
    pts = [(x, y, a.getpixel((x, y))) for y in range(0, a.height, 2)
           for x in range(0, a.width, 2)
           if a.getpixel((x, y))[3] == 255 and a.getpixel((x, y))[:3] != (255, 0, 255)]
    best = None
    for dx in range(-40, 41):
        for dy in range(-40, 41):
            bad = n = 0
            for x, y, pa in pts[::3]:
                X, Y = x + dx, y + dy
                if not (0 <= X < b.width and 0 <= Y < b.height):
                    continue
                n += 1
                pb = b.getpixel((X, Y))
                if pb[3] != 255 or sum(abs(pa[i] - pb[i]) for i in range(3)) > 30:
                    bad += 1
            if n > 100 and (best is None or bad / n < best[0]):
                best = (bad / n, dx, dy)
    if best is None or best[0] > 0.1:
        print("    !! %s: could not align the redraw with the original" % name)
        return None
    return a, b, (best[1], best[2])


def redraw_pixel(rd, x, y):
    """The redrawn colour for layer pixel (x, y) of the assembled band, or None."""
    a, b, (dx, dy) = rd
    bx, by = x, y - BAND_Y
    if not (0 <= bx < a.width and 0 <= by < a.height):
        return None
    if a.getpixel((bx, by))[:3] != (255, 0, 255):
        return None                             # not one of the lettering pixels
    X, Y = bx + dx, by + dy
    if not (0 <= X < b.width and 0 <= Y < b.height):
        return None                             # canvas edge cut it off
    c = b.getpixel((X, Y))
    if c[3] != 255 or c[:3] == (255, 0, 255):
        return None
    return c[:3]


# the palette swatches added to each redraw_done file (x 1-150, y 16-24): not art
SWATCHES = (1, 16, 151, 25)


def redraw_art(layer, rd, panels):
    """{layer pixel: colour} for every pixel the redraw decides, and the pixels
    it leaves open (still magenta: no colour given yet).

    The redraw is the art, exactly: a pixel repainted anywhere in the band --
    not only where the Japanese was -- replaces the original, and so does its
    counterpart in the spread-out copy higher up the layer (the copies sit a
    fixed number of rows above; a pixel maps there only where the original art
    around it matches, 5x5). Must run on the untouched layer.
    """
    a, b, (dx, dy) = rd
    offs = sorted({q.bbox[1] - p.bbox[1] for p in panels for q in panels
                   if p.cy >= BAND_Y > q.cy and p.vertical == q.vertical
                   and p.bbox[0] == q.bbox[0]})

    def same(x, y, off):
        for yy in range(y - 2, y + 3):
            for xx in range(x - 2, x + 3):
                if (0 <= xx < layer.width and 0 <= yy < layer.height
                        and 0 <= yy + off < layer.height
                        and layer.rgb_at(xx, yy) != layer.rgb_at(xx, yy + off)):
                    return False
        return True

    known, open_ = {}, set()
    for by in range(a.height):
        for bx in range(a.width):
            if SWATCHES[0] <= bx < SWATCHES[2] and SWATCHES[1] <= by < SWATCHES[3]:
                continue
            pa = a.getpixel((bx, by))
            if pa[3] != 255:
                continue                            # transparent in the original
            X, Y = bx + dx, by + dy
            pb = b.getpixel((X, Y)) if 0 <= X < b.width and 0 <= Y < b.height else None
            x, y = bx, by + BAND_Y
            spots = [(x, y)] + [(x, y + o) for o in offs if same(x, y, o)]
            if pb is None or pb[3] != 255 or pb[:3] == (255, 0, 255):
                open_.update(spots)
                continue
            for q in spots:
                known[q] = pb[:3]
    return known, open_


def apply_repaints(layer, pix):
    """Write repainted art pixels, sharing tiles wherever that is exact.

    The band and its copy higher up usually use the *same* tiles, so a repaint
    applied to both is one change to one tile. A tile is edited in place when
    every cell using it wants the same change; only cells that disagree with the
    others on their tile get a private copy (exact duplicates freed first --
    never a near-copy merge, which would alter the art).
    """
    TILE = 8
    by_cell = collections.defaultdict(dict)
    for (x, y), c in pix.items():
        ci = (y // TILE) * layer.sw + x // TILE
        cell = layer.cells[ci]
        idx = layer.nearest(cell["palette"], c)
        by_cell[ci][layer._in_tile(cell, x, y)] = (idx, x, y)

    def want(ci):
        return frozenset((k, v[0]) for k, v in by_cell.get(ci, {}).items())

    split = set()
    for ci in by_cell:
        users = layer.tile_users[layer.cells[ci]["tile"]]
        if any(u < 0 for u in users) or len({want(u) for u in users}) > 1:
            split.add(ci)
    if split:
        layer.free_by_dedupe(protect=set(by_cell))
        need = sum(1 for ci in split if not layer.exclusive(ci))
        if need > len(layer.free_pool):
            print("    !! repainted art: %d cells need a private tile, %d free -- "
                  "those cells left as they were" % (need, len(layer.free_pool)))
        layer.privatise_cells(split)
    done = skipped = 0
    for ci, px in by_cell.items():
        users = layer.tile_users[layer.cells[ci]["tile"]]
        shared_ok = all(u >= 0 and want(u) == want(ci) for u in users)
        if not (layer.exclusive(ci) or shared_ok):
            skipped += 1
            continue
        for _k, (idx, x, y) in px.items():
            layer.put(x, y, idx, allow_shared=True)
        done += 1
    print("    repainted art: %d cells written%s"
          % (done, ", %d left as they were" % skipped if skipped else ""))


def is_icon(c):
    """The orange button icon (and its white letter) next to the lettering."""
    return c is not None and ((c[0] >= 230 and 90 <= c[1] <= 175 and c[2] <= 60)
                              or (c[0] > 235 and c[1] > 235 and c[2] > 235))


def erase_targets(layer, p):
    """Per-pixel fill that keeps the illustration behind the lettering.

    Backdrop colours are the light, common colours around the lettering (cream and
    the pastel drawing); anything else inside the box is lettering or its
    antialiasing and takes the colour of the nearest backdrop pixel in 2D, so the
    drawing continues through where the Japanese was instead of being cut out.
    """
    x0, y0, x1, y1 = p.clear
    pad = 12
    hist = collections.Counter()
    for y in range(y0 - pad, y1 + pad):
        for x in range(x0 - pad, x1 + pad):
            c = layer.rgb_at(x, y) if 0 <= x < layer.width and 0 <= y < layer.height else None
            if c is not None and sp.lum(c) >= 170 and not sp.is_border(c)                     and not is_icon(c):
                hist[c] += 1
    anchors = [c for c, n in hist.items() if n >= 150]

    def on_ramp(c):
        """Lies on the line from the ink colour to an anchor: antialiasing."""
        for a in anchors:
            if c == a:
                continue
            d = [a[i] - p.ink[i] for i in range(3)]
            dd = sum(v * v for v in d)
            s = max(0.0, min(1.0, sum((c[i] - p.ink[i]) * d[i] for i in range(3)) / dd))
            q = [p.ink[i] + s * d[i] for i in range(3)]
            if sum((c[i] - q[i]) ** 2 for i in range(3)) ** 0.5 <= 18:
                return True
        return False

    palette = {c for c, n in hist.items() if n >= 12}
    ramp = {c for c in palette if on_ramp(c)}

    def near_ink(x, y):
        return any(sp.is_ink(layer.rgb_at(x + dx, y + dy))
                   for dx in range(-2, 3) for dy in range(-2, 3)
                   if 0 <= x + dx < layer.width and 0 <= y + dy < layer.height)

    def backdrop(x, y):
        c = layer.rgb_at(x, y)
        return c in palette and not (c in ramp and near_ink(x, y))
    dominant = max(hist, key=hist.get)
    mask = set()
    out = {}
    for y in range(y0, y1):
        for x in range(x0, x1):
            c = layer.rgb_at(x, y)
            if c is None or backdrop(x, y) or sp.is_border(c) or is_icon(c):
                out[(x, y)] = c
            else:
                mask.add((x, y))

    def probe(x, y, dx, dy):
        """Backdrop colour and distance met walking from (x, y), or None if blocked."""
        for d in range(1, 9):
            q = (x + dx * d, y + dy * d)
            if q in mask:
                continue
            c = layer.rgb_at(*q) if 0 <= q[0] < layer.width and 0 <= q[1] < layer.height else None
            return (c, d) if c in palette else None
        return None

    # onion-peel: fill the pixels that touch known backdrop first, each from a
    # distance-weighted vote of the known pixels around it (radius 3). Filled pixels
    # then count as known, so region edges are carried across the stroke coherently
    # instead of speckling.
    known = {}
    for y in range(y0 - 4, y1 + 4):
        for x in range(x0 - 4, x1 + 4):
            if (x, y) in mask or not (0 <= x < layer.width and 0 <= y < layer.height):
                continue
            if backdrop(x, y):
                known[(x, y)] = layer.rgb_at(x, y)
    todo = set(mask)
    while todo:
        ring = []
        for (x, y) in todo:
            votes = collections.Counter()
            for dy in range(-3, 4):
                for dx in range(-3, 4):
                    c = known.get((x + dx, y + dy))
                    if c is not None and (dx or dy):
                        votes[c] += 1.0 / (dx * dx + dy * dy)
            if votes:
                ring.append(((x, y), votes, sum(votes.values())))
        if not ring:
            for q in todo:
                out[q] = dominant
            break
        # only the best-supported half this round, so edges grow inward gradually
        ring.sort(key=lambda r: -r[2])
        for q, votes, _w in ring[:max(1, len(ring) // 2)]:
            known[q] = votes.most_common(1)[0][0]
            out[q] = known[q]
            todo.discard(q)
    # smooth: the vote can leave one-pixel speckle where two tones meet, so let each
    # filled pixel take the majority of its 5x5 neighbourhood (known + filled), twice
    for _ in range(2):
        nxt = {}
        for q in mask:
            votes = collections.Counter()
            for dy in range(-2, 3):
                for dx in range(-2, 3):
                    c = out.get((q[0] + dx, q[1] + dy)) if (q[0] + dx, q[1] + dy) in mask                         else known.get((q[0] + dx, q[1] + dy))
                    if c is not None:
                        votes[c] += 1
            nxt[q] = votes.most_common(1)[0][0] if votes else out[q]
        out.update(nxt)
    return out


def _set_cell(layer, ci, entry):
    old = layer.cells[ci]["tile"]
    layer.tile_users[old].discard(ci)
    layer.users[old] -= 1
    layer.cells[ci] = dict(entry)
    layer.tile_users[entry["tile"]].add(ci)
    layer.users[entry["tile"]] += 1


def _detach_twin(layer):
    """For a single-triangle layer: the spread copy (above BAND_Y) is the
    assembled copy (below) cell for cell, a whole number of cells higher, and
    the two share every tile -- so the 64-tile layer has none to spare for
    giving each its own lettering. Point the upper copy's cells at a
    transparent cell for now (the lower copy then owns its tiles) and return
    [(upper cell, lower cell)] for _reattach."""
    panels = sorted((make_panel(layer, g) for g in ink_groups(layer)), key=lambda p: p.cy)
    up, low = panels[0], panels[-1]
    off = low.bbox[1] - up.bbox[1]
    assert len(panels) == 2 and off % 8 == 0 and up.cy < BAND_Y <= low.cy, \
        [(p.bbox, p.cy) for p in panels]
    step = off // 8 * layer.sw
    def empty(i):
        return all(layer.get(x, y) == 0
                   for y in range(i // layer.sw * 8, i // layer.sw * 8 + 8)
                   for x in range(i % layer.sw * 8, i % layer.sw * 8 + 8))
    blank = next(i for i in range(len(layer.cells)) if empty(i))
    pairs = []
    for ci in range(BAND_Y // 8 * layer.sw):
        cj = ci + step
        if cj < len(layer.cells) and not empty(ci):
            assert layer.cells[ci] == layer.cells[cj], ("copies differ", ci)
            pairs.append((ci, cj))
    for ci, _cj in pairs:
        _set_cell(layer, ci, layer.cells[blank])
    return pairs


def _reattach(layer, pairs):
    for ci, cj in pairs:
        _set_cell(layer, ci, layer.cells[cj])


def paint_battle(layer, font, cls, page, single=None):
    """Paint one page's triangles. `single` = a button letter for a layer that
    holds just that one triangle of `page` (the download-play archives' extra
    layers, twice: spread and assembled); the page's redraw applies, limited to
    the pixels this layer actually draws."""
    names = PAGES[cls][page]
    pairs = _detach_twin(layer) if single else None
    panels = [make_panel(layer, g) for g in ink_groups(layer)]
    horiz = sorted((p for p in panels if not p.vertical), key=lambda p: p.cy)
    order = ["B", "X", "X", "B"]
    buttons = {}
    for p in panels:
        if p.vertical:
            buttons[id(p)] = "A" if p.cx >= 190 else "Y"
    if single:
        for p in panels:
            buttons[id(p)] = single
    elif len(horiz) == 4:
        for p, b in zip(horiz, order):
            buttons[id(p)] = b
    else:                                   # a page with one assembled set only
        for p, b in zip(horiz, ("X", "B")):
            buttons[id(p)] = b
    rd = load_redraw(cls, page)
    known, open_ = {}, set()
    if rd:
        print("    hand-redrawn art applied for %s page %d%s (offset %s)"
              % (cls, page, " %s only" % single if single else "", rd[2]))
        known, open_ = redraw_art(layer, rd, panels)
        if single:                          # the other triangles aren't here
            known = {q: c for q, c in known.items() if layer.rgb_at(*q) is not None}
            open_ = {q for q in open_ if layer.rgb_at(*q) is not None}
        if open_:
            print("    %d pixels still magenta in the redraw -- filled automatically"
                  % len({q for q in open_ if q[1] >= BAND_Y}))
    asm = {}
    for p in panels:
        if p.cy >= BAND_Y:
            asm[buttons[id(p)]] = p
    jobs = []
    for p in panels:
        name = names[buttons[id(p)]]
        px, fits = (sp.layout_vertical if p.vertical else sp.layout_horizontal)(
            layer, font, p, name)
        if not fits:
            print("    !! %r does not fit its triangle" % name)
        targets = erase_targets(layer, p)
        if rd:
            # the redraw decides every pixel it covers; the automatic erase only
            # fills what it leaves open (still magenta)
            for q in list(targets):
                if q in known:
                    targets[q] = known[q]
                elif q not in open_:
                    targets[q] = layer.rgb_at(*q)
        cells = {(y // 8) * layer.sw + (x // 8) for x, y in px
                 if 0 <= x < layer.width and 0 <= y < layer.height}
        jobs.append((p, name, px, targets, cells))
    if rd:
        # repaints outside the lettering boxes: a job with no text, written
        # pixel by pixel (box None)
        inside = set()
        for _p, _n, _px, t, _c in jobs:
            inside |= set(t)
        rest = {q: c for q, c in known.items()
                if q not in inside and c != layer.rgb_at(*q)}

    def clear(p, targets):
        if p is not None:
            layer.clear_private(p.clear, targets)
            return
        for (x, y), c in targets.items():
            if layer.exclusive((y // 8) * layer.sw + x // 8):
                layer.put_rgb(x, y, c)

    def dirty(p, targets):
        if p is not None:
            return layer.dirty_cells(p.clear, targets)
        return {(y // 8) * layer.sw + x // 8 for (x, y), c in targets.items()
                if layer.rgb_at(x, y) != c}

    for p, _n, _px, targets, _c in jobs:
        clear(p, targets)
    claims = [c | dirty(p, t) for p, _n, _x, t, c in jobs]
    for i, (p, name, px, targets, _c) in enumerate(jobs):
        # exact duplicates only: a near-copy merge (tol) would change the art
        layer.free_by_dedupe(protect=set().union(*claims[i:]))
        need = sum(1 for ci in claims[i]
                   if len(layer.tile_users[layer.cells[ci]["tile"]]) > 1)
        if need > len(layer.free_pool):
            print("    !! %s: %r needs %d private tiles, %d free -- left as it was"
                  % ("art not applied" if p is None else "left in Japanese",
                     name, need, len(layer.free_pool)))
            continue
        layer.privatise_cells(claims[i])
        clear(p, targets)
        for x, y in px:
            layer.put_rgb(x, y, p.ink)
    if rd and rest:
        apply_repaints(layer, rest)
    if pairs:
        _reattach(layer, pairs)
    return layer.starved, len(set().union(*claims))


def main(argv):
    import tempfile
    from narc import Narc
    root = os.path.dirname(HERE)
    cls, page = argv[1], int(argv[2])
    n = Narc(os.path.join(root, "extracted", "info", "subgraphics",
                          "madu_battle_%s.narc" % cls))
    tmp = tempfile.mkdtemp()
    paths = []
    for k in range(3):
        p = os.path.join(tmp, "%d.bin" % k)
        with open(p, "wb") as fh:
            fh.write(n.file(page * 3 + k))
        paths.append(p)
    layer = BgLayer(*paths)
    print(paint_battle(layer, load_font(), cls, page))
    out = os.path.join(root, "work", "gfx", "battle_panels")
    os.makedirs(out, exist_ok=True)
    layer.render(os.path.join(out, "%s_%d.png" % (cls, page)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
