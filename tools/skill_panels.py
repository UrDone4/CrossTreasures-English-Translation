#!/usr/bin/env python3
"""Repaint the skill-name triangles on the skill screens.

`madu_skill_<class>.narc` member 26/27/28 is one tall background layer holding
ten triangular skill panels in a 2x5 grid of 128x96 slots. The lettering is
dark brown over a faint illustration, and its direction follows the triangle:
the sideways triangles (A / Y buttons) set the name **vertically, one character
per line**, the upright ones (B / X buttons) set it horizontally.

English keeps the same split. Horizontal names are drawn as one line, or two
when they will not fit the triangle. Vertical names are stacked letter by
letter, one column per word -- the same convention the Japanese uses, and the
only way to fit a name into a strip ~11px wide.

Each panel is measured, not hardcoded: the ink bbox gives the position and the
orientation, and the triangle's own border gives the room available.

    skill_panels.py <class>     preview one class to work/gfx/skill_panels/
"""

import collections
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from bgtext import BgLayer, load_font  # noqa: E402

SLOT_W, SLOT_H = 128, 96

# Row-major, two panels per row (left slot, right slot). Names follow
# work/ui_translations.py (text/skill_name.txt); the basic actions that have no
# entry there (Attack, Power Attack, Power Stamp, Quick Act, Mana Drain) are named
# to match the descriptions in work/narc_text.tsv.
NAMES = {
    "magic": [
        ("Attack", "Mana Drain"),
        ("Fireball", "Inferno"),
        ("Deep Freeze", "Ice Lance"),
        ("Poison Sting", "Sleep"),
        ("Stasis", "Ultimate"),
    ],
    "priest": [
        ("Attack", "Power Stamp"),
        ("Healas", "Curas"),
        ("Knock Away", "Wide Swing"),
        ("Lightning", "Thunderclap"),
        ("Love Pulse", "Love Beam"),
    ],
    "soldier": [
        ("Attack", "Power Attack"),
        ("Spin Slash", "Jump Slash"),
        ("Vacuum Slash", "Shield Bash"),
        ("Charge", "Spirit Flame"),
        ("Cheer", "War Cry"),
    ],
    "thief": [
        ("Attack", "Quick Act"),
        ("Blade Storm", "Double Slash"),
        ("Dash Thrust", "Paralyze Shot"),
        ("Poison Shot", "Hand Bomb"),
        ("Time Bomb", "Quick Charge"),
    ],
}


def lum(c):
    return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]


def is_ink(c):
    """The dark brown lettering, in any of its per-panel shades."""
    return (c is not None and lum(c) <= 100 and c[0] > c[1] >= c[2]
            and c[0] - c[2] >= 90)


def is_border(c):
    """Transparent, or the green outline of the triangle."""
    return c is None or (c[1] - c[0] >= 45 and lum(c) < 170)


def is_outline(layer, x, y):
    """The triangle's green outline: border-coloured *and* at the transparent
    edge. Colour alone is not enough -- thief's green sword art passes
    is_border, and the redraw transfer skipped it all."""
    if not is_border(layer.rgb_at(x, y)):
        return False
    return any(layer.rgb_at(x + dx, y + dy) is None
               for dy in range(-2, 3) for dx in range(-2, 3))


class Panel:
    def __init__(self, layer, index):
        self.index = index
        self.x0 = (index % 2) * SLOT_W
        self.y0 = (index // 2) * SLOT_H
        xs, ys, hist = [], [], collections.Counter()
        for y in range(self.y0, self.y0 + SLOT_H):
            for x in range(self.x0, self.x0 + SLOT_W):
                c = layer.rgb_at(x, y)
                if is_ink(c):
                    xs.append(x)
                    ys.append(y)
                    hist[c] += 1
        if not xs:
            raise ValueError("panel %d has no lettering" % index)
        self.bbox = (min(xs), min(ys), max(xs) + 1, max(ys) + 1)
        self.ink = hist.most_common(1)[0][0]
        w = self.bbox[2] - self.bbox[0]
        h = self.bbox[3] - self.bbox[1]
        self.vertical = h > w * 1.6
        self.cx = (self.bbox[0] + self.bbox[2]) // 2
        self.cy = (self.bbox[1] + self.bbox[3]) // 2
        # the region to clear: the Japanese ink, a little generous for its
        # antialiasing, never near the icon or the border
        b = self.bbox
        self.clear = (b[0] - 2, b[1] - 2, b[2] + 2, b[3] + 2)
        self.keeps = self._backdrop(layer)

    def _backdrop(self, layer):
        x0, y0, x1, y1 = self.clear
        hist = collections.Counter()
        for y in range(y0, y1):
            for x in range(x0, x1):
                c = layer.rgb_at(x, y)
                if c is not None and lum(c) >= 170 and not is_border(c):
                    hist[c] += 1
        area = (x1 - x0) * (y1 - y0)
        # light colours only: the lettering's own brown antialiasing covers a
        # large area too, and must count as lettering, not backdrop
        keeps = tuple(c for c, n in hist.most_common() if n >= area * 0.05)
        return keeps or tuple(c for c, _ in hist.most_common(1))


def span(layer, x, y, dx, dy, limit=60):
    """Free pixels from (x, y) along (dx, dy) until the triangle's border."""
    n = 0
    while n < limit and not is_border(layer.rgb_at(x + dx * (n + 1),
                                                   y + dy * (n + 1))):
        n += 1
    return n


def glyph_pixels(font, ch, ox, oy):
    """Set pixels of one glyph with its cell's top-left at (ox, oy)."""
    gi = font.cmap.get(ord(ch))
    if gi is None:
        return []
    bits = font.bitmap(gi)
    return [(ox + c, oy + r) for r in range(font.cell_h)
            for c in range(font.cell_w) if bits[r][c]]


def ink_extent(font, ch):
    gi = font.cmap.get(ord(ch))
    bits = font.bitmap(gi)
    rows = [r for r in range(font.cell_h) if any(bits[r])]
    cols = [c for c in range(font.cell_w)
            if any(bits[r][c] for r in range(font.cell_h))]
    return (min(rows), max(rows), min(cols), max(cols)) if rows else (0, 0, 0, 0)


def width_of(font, text):
    return sum(font.advance(ord(c)) for c in text)


def layout_horizontal(layer, font, panel, name):
    """One line if it fits inside the triangle at its own height, else two."""
    room = (span(layer, panel.cx, panel.cy, -1, 0)
            + span(layer, panel.cx, panel.cy, 1, 0) - 6)
    lines = [name]
    if width_of(font, name) > room and " " in name:
        head, tail = name.split(" ", 1)
        lines = [head, tail]
    pitch = font.cell_h
    top = panel.cy - (len(lines) * pitch) // 2
    px = []
    for i, line in enumerate(lines):
        pen = panel.cx - width_of(font, line) // 2
        for ch in line:
            px += glyph_pixels(font, ch, pen, top + i * pitch)
            pen += font.advance(ord(ch))
    return px, max(width_of(font, l) for l in lines) <= room


def stack_column(font, word, cx, cy, gap):
    """Letters of `word` one above the next, centred on (cx, cy)."""
    ext = [ink_extent(font, ch) for ch in word]
    heights = [e[1] - e[0] + 1 for e in ext]
    total = sum(heights) + gap * (len(word) - 1)
    y = cy - total // 2
    px = []
    for ch, e, h in zip(word, ext, heights):
        cell_x = cx - (e[2] + e[3] + 1) // 2
        px += glyph_pixels(font, ch, cell_x, y - e[0])
        y += h + gap
    return px, total


def layout_vertical(layer, font, panel, name):
    """One stacked column per word, first word leftmost."""
    words = name.split(" ")
    room = (span(layer, panel.cx, panel.cy, 0, -1)
            + span(layer, panel.cx, panel.cy, 0, 1) - 4)
    for gap in (2, 1, 0):
        cols = [stack_column(font, w, 0, 0, gap)[1] for w in words]
        if max(cols) <= room:
            break
    pitch = 10
    px = []
    for i, w in enumerate(words):
        cx = panel.cx + int((i - (len(words) - 1) / 2) * pitch)
        px += stack_column(font, w, cx, panel.cy, gap)[0]
    return px, max(cols) <= room


_PAGE_CACHE = {}


def _pages(cls):
    """[(page, original-with-magenta rows, done image, (dx, dy))] for a class's
    battle redraws, the originals as plain lists for fast lookup."""
    if cls not in _PAGE_CACHE:
        import battle_panels as bp
        out = []
        for page in range(3):
            rd = bp.load_redraw(cls, page)
            if rd:
                a, b, off = rd
                rows = [[a.getpixel((x, y)) for x in range(a.width)] for y in range(a.height)]
                out.append((page, rows, b, off))
        _PAGE_CACHE[cls] = out
    return _PAGE_CACHE[cls]


def _match(pts, rows, cap_frac):
    """Best (bad, n, ox, oy) placing the panel points on a page image."""
    H, W = len(rows), len(rows[0])
    best = None
    for oy in range(-SLOT_H, H):
        for ox in range(-SLOT_W, W):
            bad = n = 0
            cap = len(pts) * cap_frac
            for x, y, c in pts:
                X, Y = x + ox, y + oy
                if not (0 <= X < W and 0 <= Y < H):
                    continue
                pa = rows[Y][X]
                if pa[3] != 255 or pa[:3] == (255, 0, 255):
                    continue
                n += 1
                if abs(pa[0] - c[0]) + abs(pa[1] - c[1]) + abs(pa[2] - c[2]) > 24:
                    bad += 1
                    if bad > cap:
                        break
            # most of the panel must land on the page: a sliver overlapping
            # the page edge can match perfectly and win (thief Blade Storm
            # took 490 pixels of the wrong place)
            if n >= len(pts) // 2 and bad <= cap and (
                    best is None or bad / n < best[0] / best[1]):
                best = (bad, n, ox, oy)
    return best


def redraw_for_panel(layer, cls, panel_index, name):
    """({pixel: rgb} the user repainted, {pixel: rgb} the redraw maps to)
    for this skill-screen panel -- the first is every pixel that differs
    (the Japanese and its drop shadow), the second every interior pixel the
    redraw covers -- or ({}, {}) if no battle triangle matches.

    The skill screen's triangles are the same drawings as the assembled battle
    triangles. Every page is searched (not just the one the name suggests), on
    the panel's opaque non-lettering pixels; the skill-screen copy can differ
    from the battle art in a few pixels (palette quantisation), so some mismatch
    is accepted -- only the pixels the user repainted are carried over, never
    the outline, and never where the two copies' art disagrees."""
    import battle_panels as bp
    x0, y0 = (panel_index % 2) * SLOT_W, (panel_index // 2) * SLOT_H
    pts = [(x - x0, y - y0, layer.rgb_at(x, y))
           for y in range(y0, y0 + SLOT_H, 3) for x in range(x0, x0 + SLOT_W, 3)
           if layer.rgb_at(x, y) is not None and not is_ink(layer.rgb_at(x, y))]
    found = None
    # strict first; the looser pass only for panels it misses (the two copies
    # are the same drawing, but their palettes quantise it slightly apart --
    # thief Quick Charge ~13%). The copy below never touches the outline and
    # only repaints pixels the two copies agree on, so a loose match is safe
    for cap in (0.06, 0.16):
        for page, rows, b, off in _pages(cls):
            m = _match(pts, rows, cap)
            if m and (found is None or m[0] / m[1] < found[0][0] / found[0][1]):
                found = (m, page, rows, b, off)
        if found:
            break
    if found is None:
        print("    !! %s %r: panel not found on any battle page" % (cls, name))
        return {}, {}
    (bad, n, ox, oy), page, rows, b, (dx, dy) = found
    out, full = {}, {}
    sw = bp.SWATCHES
    for y in range(y0, y0 + SLOT_H):
        for x in range(x0, x0 + SLOT_W):
            if layer.rgb_at(x, y) is None:
                continue
            X, Y = x - x0 + ox, y - y0 + oy
            if not (0 <= X < len(rows[0]) and 0 <= Y < len(rows)):
                continue
            if sw[0] <= X < sw[2] and sw[1] <= Y < sw[3]:
                continue
            pa = rows[Y][X]
            if pa[3] != 255:
                continue
            Xb, Yb = X + dx, Y + dy
            if not (0 <= Xb < b.width and 0 <= Yb < b.height):
                continue
            pb = b.getpixel((Xb, Yb))
            if pb[3] != 255 or pb[:3] == (255, 0, 255):
                continue
            c = layer.rgb_at(x, y)
            if is_outline(layer, x, y):
                continue        # the outline stays exactly as the skill screen draws it
            # the same drawing: wherever the skill screen visibly differs from
            # the user's redraw (the Japanese, its drop shadow), take the redraw.
            # Matching the battle *original* first missed the shadows, whose
            # colours the two palettes quantise apart
            full[(x, y)] = pb[:3]
            if pa[:3] == (255, 0, 255) or sum(abs(pb[k] - c[k]) for k in range(3)) > 24:
                out[(x, y)] = pb[:3]
    return out, full


def paint_panels(layer, font, cls):
    """Repaint all ten panels of one class. Returns (starved, cells)."""
    names = [n for row in NAMES[cls] for n in row]
    panels = [Panel(layer, i) for i in range(10)]
    # the user's hand-redrawn battle triangles are the same drawings: use them
    # for every pixel they repaint (lettering and its drop shadow), so the
    # skill screen matches the battle screen (hardware: the old shadows showed)
    redraws = [redraw_for_panel(layer, cls, i, n) for i, n in enumerate(names)]

    jobs = []
    for panel, name in zip(panels, names):
        px, fits = (layout_vertical if panel.vertical else layout_horizontal)(
            layer, font, panel, name)
        if not fits:
            print("    !! %r does not fit its triangle" % name)
        axis = "row" if panel.vertical else "col"
        targets = layer.inpaint_targets(panel.clear, panel.keeps, reach=8,
                                        axis=axis, spare_icons=False)
        # the clear box can reach the tapering edge of the triangle: leave the
        # outline (and the transparency outside it) exactly as drawn
        for xy in targets:
            c = layer.rgb_at(*xy)
            if is_border(c):
                targets[xy] = c
        rd, full = redraws[panel.index]
        if rd:
            # widen the box to every repainted pixel, and inside it take the
            # redraw wherever it maps (the erase would otherwise wipe art that
            # was already right -- thief Blade Storm lost its swords)
            xs = [x for x, _ in rd] + [panel.clear[0], panel.clear[2] - 1]
            ys = [y for _, y in rd] + [panel.clear[1], panel.clear[3] - 1]
            panel.clear = (min(xs), min(ys), max(xs) + 1, max(ys) + 1)
            x0, y0, x1, y1 = panel.clear
            for y in range(y0, y1):
                for x in range(x0, x1):
                    if (x, y) in full:
                        targets[(x, y)] = full[(x, y)]
                    elif (x, y) not in targets:
                        targets[(x, y)] = layer.rgb_at(x, y)
        cells = {(y // 8) * layer.sw + (x // 8) for x, y in px
                 if 0 <= x < layer.width and 0 <= y < layer.height}
        jobs.append((panel, name, px, targets, cells))

    for panel, _n, _px, targets, _c in jobs:
        layer.clear_private(panel.clear, targets)
    claims = [c | layer.dirty_cells(p.clear, t) for p, _n, _x, t, c in jobs]

    for i, (panel, name, px, targets, _c) in enumerate(jobs):
        layer.free_by_dedupe(protect=set().union(*claims[i:]))
        need = sum(1 for ci in claims[i]
                   if len(layer.tile_users[layer.cells[ci]["tile"]]) > 1)
        if need > len(layer.free_pool):
            layer.free_by_dedupe(protect=set().union(*claims), tol=2)
            need = sum(1 for ci in claims[i]
                       if len(layer.tile_users[layer.cells[ci]["tile"]]) > 1)
        if need > len(layer.free_pool):
            print("    -- left in Japanese: %r needs %d tiles, %d free"
                  % (name, need, len(layer.free_pool)))
            continue
        layer.privatise_cells(claims[i])
        layer.clear_private(panel.clear, targets)
        for x, y in px:
            layer.put_rgb(x, y, panel.ink)
    return layer.starved, len(set().union(*claims))


def main(argv):
    if len(argv) < 2 or argv[1] not in NAMES:
        print(__doc__)
        return 1
    import tempfile
    from narc import Narc
    root = os.path.dirname(HERE)
    cls = argv[1]
    narc = Narc(os.path.join(root, "extracted", "info", "subgraphics",
                             "madu_skill_%s.narc" % cls))
    tmp = tempfile.mkdtemp()
    paths = []
    for k in range(3):
        p = os.path.join(tmp, "%d.bin" % k)
        with open(p, "wb") as fh:
            fh.write(narc.file(26 + k))
        paths.append(p)
    layer = BgLayer(*paths)
    print(paint_panels(layer, load_font(), cls))
    out = os.path.join(root, "work", "gfx", "skill_panels")
    os.makedirs(out, exist_ok=True)
    layer.render(os.path.join(out, "%s.png" % cls))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
