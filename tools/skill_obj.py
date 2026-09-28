#!/usr/bin/env python3
"""Repaint the skill screen's sprite labels (an OBJ bank inside the NARC).

`madu_skill_<class>.narc` members 23 (NCER), 24 (NCGR), 25 (NCLR) are a sprite
bank -- byte-identical in all four classes -- holding the screen title, the two
skill-type pills and the info-box headers. Unlike the title-screen banks these
are not loose files, and their cells share tiles, which changes how they must
be edited:

* **Priority is inverted.** On the DS a lower OAM index is drawn on top, so the
  text pieces (listed first) sit above the shared frame pieces. Compositing in
  list order -- what `ngfx.py cells` does -- clips both ends of every header.
  `render()` here paints in the right order.
* **Writes must go through the label's own pieces only.** `gfxtext.Bank.put`
  writes to every OAM covering a pixel, which here would scribble on the frame
  tiles that all eight headers share. Each label names the entries it may edit.
* The pills' second line (スキル) lives in a body tile shared by both pills, so
  it is edited once, from the first pill.

    skill_obj.py preview     write a contact sheet to work/gfx/skill_obj/
"""

import collections
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from gfxtext import Bank  # noqa: E402
from bgtext import load_font  # noqa: E402

TILE = 8

# One entry per label. `entries` are the OAM entries the label may edit; `box`
# is in cell coordinates; `lines` are drawn centred, top to bottom. bg/ink are
# palette indices, found from the pixels when omitted (bg = commonest opaque
# index in the box, ink = the index farthest from it in colour).
LABELS = [
    # screen title. The bar is 104x24 but its shadow/border sits in rows 16-23,
    # so the box stops at row 16 -- a taller one repainted the border brown.
    {"cell": 0, "entries": range(8), "box": (0, 1, 95, 16), "lines": ["Skills"]},
    # skill-type pills. The pill's interior is x 5-65 (its outline is at x 1-4 and
    # 65-69), so both lines are boxed inside that -- the "Skill" line used to run
    # to x 68 and repainted the right-hand outline. Line 1 differs per pill; line 2
    # ("Skill") is a body tile shared by both pills.
    {"cell": 4, "entries": [0, 1, 2], "box": (5, 2, 65, 16), "lines": ["Action"]},
    {"cell": 5, "entries": [0, 1, 2], "box": (5, 2, 65, 16), "lines": ["Passive"]},
    {"cell": 4, "entries": [3, 4], "box": (5, 16, 65, 27), "lines": ["Skill"],
     "shared_ok": True},
    # info-box headers
    {"cell": 6, "entries": [0, 1], "box": (12, 1, 60, 12), "lines": ["MP Cost"]},
    {"cell": 7, "entries": [2, 3], "box": (12, 1, 60, 12), "lines": ["Recharge"]},
    {"cell": 7, "entries": [0, 1], "box": (47, 17, 68, 28), "lines": ["sec"],
     "align": "right", "shared_ok": True},
    {"cell": 8, "entries": [0, 1], "box": (16, 1, 80, 12), "lines": ["Damage Type"]},
    {"cell": 9, "entries": [0, 1, 2], "box": (11, 1, 91, 12), "lines": ["Status Effect"]},
    {"cell": 10, "entries": [0], "box": (12, 1, 44, 12), "lines": ["Power"]},
    {"cell": 11, "entries": [0, 1, 2], "box": (0, 1, 56, 12), "lines": ["Defense"]},
    {"cell": 12, "entries": [0, 1], "box": (4, 1, 52, 12), "lines": ["Combos"]},
    {"cell": 13, "entries": [0, 1], "box": (4, 1, 68, 12), "lines": ["Duration"]},
    {"cell": 13, "entries": [2, 3], "box": (46, 17, 67, 28), "lines": ["sec"],
     "align": "right", "shared_ok": True},
]


SKILL_MEMBERS = (24, 25, 23)      # NCGR, NCLR, NCER


def load(narc, workdir, members=SKILL_MEMBERS):
    os.makedirs(workdir, exist_ok=True)
    base = os.path.join(workdir, "skill_obj")
    for ext, idx in zip(("NCGR", "NCLR", "NCER"), members):
        with open("%s.%s" % (base, ext), "wb") as fh:
            fh.write(narc.file(idx))
    return Bank(base)


def sheet_pos(bank, e, col, row):
    """Offset into the tilesheet for pixel (col, row) of OAM entry e."""
    if e["flip_h"]:
        col = e["w"] - 1 - col
    if e["flip_v"]:
        row = e["h"] - 1 - row
    t = e["tile"] + (row // TILE) * (e["w"] // TILE) + (col // TILE)
    sx = (t % bank.tiles_w) * TILE + col % TILE
    sy = (t // bank.tiles_w) * TILE + row % TILE
    return sy * bank.w + sx


def origin(bank, ci):
    ents = bank.cells[ci]
    return min(e["x"] for e in ents), min(e["y"] for e in ents)


def owner(bank, ci, entries, ax, ay):
    """Sheet position of the entry that is *visible* at (ax, ay), if allowed.

    Topmost = lowest index among entries with an opaque pixel there. If that
    entry is not one this label may edit, the pixel is left alone.
    """
    for k, e in enumerate(bank.cells[ci]):
        if e["x"] <= ax < e["x"] + e["w"] and e["y"] <= ay < e["y"] + e["h"]:
            pos = sheet_pos(bank, e, ax - e["x"], ay - e["y"])
            if bank.flat[pos] == 0:
                continue                      # transparent: the next one shows
            return pos if k in entries else None
    return None


def rgb(bank, ci, entry_idx, idx):
    e = bank.cells[ci][entry_idx]
    return tuple(bank.palette[e["palette"] * 16 + idx][:3])


def cell_tiles(bank, ci, entries=None):
    out = set()
    for k, e in enumerate(bank.cells[ci]):
        if entries is not None and k not in entries:
            continue
        for r in range(e["h"] // TILE):
            for c in range(e["w"] // TILE):
                out.add(e["tile"] + r * (e["w"] // TILE) + c)
    return out


def paint_label(bank, font, spec):
    ci = spec["cell"]
    entries = set(spec["entries"])
    ox, oy = origin(bank, ci)
    x0, y0, x1, y1 = spec["box"]
    first = min(entries)

    cover = {}
    for y in range(y0, y1):
        for x in range(x0, x1):
            pos = owner(bank, ci, entries, x + ox, y + oy)
            if pos is not None:
                cover[(x, y)] = pos
    if not cover:
        print("  cell %d: nothing editable in %s" % (ci, spec["box"]))
        return False

    hist = {}
    for pos in cover.values():
        hist[bank.flat[pos]] = hist.get(bank.flat[pos], 0) + 1
    bg = spec.get("bg", max(hist, key=hist.get))

    def dist(i):
        a, b = rgb(bank, ci, first, i), rgb(bank, ci, first, bg)
        return sum((p - q) ** 2 for p, q in zip(a, b))
    ink = spec.get("ink", max(hist, key=dist))

    # a tile another cell also uses would change that cell too
    mine = {(p // bank.w // TILE) * bank.tiles_w + (p % bank.w) // TILE
            for p in cover.values()}
    for other in range(len(bank.cells)):
        if other != ci and mine & cell_tiles(bank, other) and not spec.get("shared_ok"):
            print("  !! cell %d shares tiles %s with cell %d"
                  % (ci, sorted(mine & cell_tiles(bank, other))[:6], other))

    # clear the old lettering (and its antialiasing) to the face colour
    clear = set(cover)
    orig = {xy: bank.flat[pos] for xy, pos in cover.items()}
    # rowfill: a gradient pill (lighter centre, darker bands) -- each row's
    # fill is its own commonest colour across the box, not one flat colour
    # (a flat fill showed as a darker box round the word)
    row_bg = {}
    if spec.get("rowfill"):
        for y in range(y0, y1):
            row = collections.Counter(orig[(x, y)] for x in range(x0, x1)
                                      if (x, y) in orig and orig[(x, y)])
            if row:
                row_bg[y] = row.most_common(1)[0][0]
    if spec.get("inpaint") is not None:
        # a strip over a varied backdrop (a curve of greens): only lettering
        # pixels -- anything not in the `inpaint` backdrop list -- change, each
        # to the nearest backdrop pixel on its own row
        keep = set(spec["inpaint"])
        for (x, y) in cover:
            if orig[(x, y)] in keep:
                continue
            for d in range(1, 40):
                hit = [orig.get((xx, y)) for xx in (x - d, x + d)
                       if orig.get((xx, y)) in keep]
                if hit:
                    bank.flat[cover[(x, y)]] = hit[0]
                    break
        clear = set()
    elif spec.get("keep_edges"):
        # Clear only inside the face, row by row: from the first to the last
        # face-coloured pixel of each row. Outside that span is the pill's
        # outline and rounded ends; a row with no face at all is a border or
        # highlight row. Clearing the whole box squared the ends off and erased
        # outlines wherever the box had to be wide enough for every Japanese
        # glyph. (The outline is often the same colour as the lettering, so
        # colour alone cannot tell them apart.)
        clear = set()
        for y in range(y0, y1):
            want = row_bg.get(y, bg)
            xs = [x for x in range(x0, x1)
                  if (x, y) in cover and bank.flat[cover[(x, y)]] == want]
            if xs:
                clear |= {(x, y) for x in range(min(xs), max(xs) + 1)
                          if (x, y) in cover}
    for xy in clear:
        bank.flat[cover[xy]] = row_bg.get(xy[1], bg)

    lines = spec["lines"]
    pitch = font.cell_h
    total = len(lines) * pitch
    top = y0 + (y1 - y0 - total) // 2
    clipped = 0
    # bold: double-strike each glyph 1px to the right (and widen the advance
    # to match), for lettering replacing heavy Japanese on a large face
    bold = 1 if spec.get("bold") else 0
    for i, line in enumerate(lines):
        width = sum(font.advance(ord(c)) + bold for c in line) - bold
        if spec.get("align") == "right":
            pen = x1 - 2 - width
        elif spec.get("align") == "left":
            pen = x0 + spec.get("indent", 0)
        else:
            pen = x0 + (x1 - x0 - width) // 2
        for ch in line:
            gi = font.cmap.get(ord(ch))
            if gi is not None:
                bits = font.bitmap(gi)
                for r in range(font.cell_h):
                    for c in range(font.cell_w):
                        if not bits[r][c]:
                            continue
                        for dx in range(bold + 1):
                            pos = cover.get((pen + c + dx, top + i * pitch + r))
                            if pos is None:
                                clipped += 1
                            else:
                                bank.flat[pos] = ink
            pen += font.advance(ord(ch)) + bold
    print("  cell %2d  %-14s bg=%d ink=%d%s"
          % (ci, "/".join(lines), bg, ink,
             "  !! %d px outside the editable pieces" % clipped if clipped else ""))
    return not clipped


def render(bank, ci):
    """Composite one cell with DS priority (lower OAM index on top)."""
    from PIL import Image
    ents = bank.cells[ci]
    ox, oy = origin(bank, ci)
    w = max(e["x"] + e["w"] for e in ents) - ox
    h = max(e["y"] + e["h"] for e in ents) - oy
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    for e in reversed(ents):
        for r in range(e["h"]):
            for c in range(e["w"]):
                v = bank.flat[sheet_pos(bank, e, c, r)]
                if v:
                    im.putpixel((e["x"] - ox + c, e["y"] - oy + r),
                                tuple(bank.palette[e["palette"] * 16 + v][:3]) + (255,))
    return im


def paint(narc, workdir, members=SKILL_MEMBERS, labels=None):
    """Apply every label and write the NCGR back into the archive."""
    bank = load(narc, workdir, members)
    font = load_font()
    ok = True
    for spec in (LABELS if labels is None else labels):
        ok &= paint_label(bank, font, spec)
    out = os.path.join(workdir, "skill_obj_out.NCGR")
    bank.save(out)
    data = open(out, "rb").read()
    if len(data) != len(narc.file(members[0])):
        raise SystemExit("NCGR size changed -- refusing")
    narc.replace(members[0], data)
    return bank, ok


def main(argv):
    if len(argv) < 2 or argv[1] != "preview":
        print(__doc__)
        return 1
    import tempfile
    from narc import Narc
    root = os.path.dirname(HERE)
    narc = Narc(os.path.join(root, "extracted", "info", "subgraphics",
                             "madu_skill_soldier.narc"))
    tmp = tempfile.mkdtemp()
    bank, _ = paint(narc, tmp)
    out = os.path.join(root, "work", "gfx", "skill_obj")
    os.makedirs(out, exist_ok=True)
    from PIL import Image
    ims = [render(bank, ci) for ci in range(len(bank.cells))]
    cols = 4
    cw = max(i.width for i in ims) * 4 + 10
    ch = max(i.height for i in ims) * 4 + 10
    sheet = Image.new("RGBA", (cols * cw, ((len(ims) + cols - 1) // cols) * ch),
                      (110, 110, 110, 255))
    for k, i in enumerate(ims):
        j = i.resize((i.width * 4, i.height * 4), Image.NEAREST)
        sheet.paste(j, ((k % cols) * cw + 5, (k // cols) * ch + 5), j)
    sheet.save(os.path.join(out, "skill_obj.png"))
    print("wrote", os.path.join(out, "skill_obj.png"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
