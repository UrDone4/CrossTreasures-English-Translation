#!/usr/bin/env python3
"""Repaint the Map screen's sprite labels (an OBJ bank inside madu_map.narc).

Members 21 (NCGR), 22 (NCLR), 20 (NCER). Same machinery and the same caveats as
the skill screen's bank -- see skill_obj.py (inverted OAM priority, shared frame
tiles, writes only through a label's own entries). Cells:

    0   マップ            the screen title
    28  A みる            the *greyed-out* hint, shown when the highlighted
                          dungeon is the player's own (nothing to view)
    32  ワールドチェンジ  the World Change title
    33  A けってい        the greyed-out OK hint

The enabled versions of the hints are part of the background hint strip
(hint_bars.py); these are the disabled-state sprites drawn over it.

A new cell is added after the 34 originals:

    34  (new)             the dungeon-name tab: a mirror of the Map tab, flush
                          with the right edge, 120x24 (drawn at 136,2 by
                          tools/map_floor_name.py, which puts the name in it)

It is built only from the Map tab's own frame tiles -- body 5 (16x16), bottom
edge 0 (16x8), rounded end 2 / 4 (8x16 / 8x8, flipped for the left end) --
which the "Map" lettering does not touch, so it needs no new tiles, only OAM
entries (the NCER grows by one cell; attribute 0x1F, scaled from cell 0's 0x1B
for its 104x24 box).

    map_obj.py preview     write a contact sheet to work/gfx/map_obj/
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import skill_obj as so  # noqa: E402

MAP_MEMBERS = (21, 22, 20)

# Titles: white lettering on the brown bar (interior kept clear of the frame).
# Hints: the dimmed grey word right of the grey A icon, left-aligned like the
# enabled hints. "View": the sprite sits at x=60 on screen and the background's
# own "View" starts at 81, so the pen is 21 (indent 2); its last ink column (39)
# is transparent in the original, so it is claimed -- otherwise the background
# word's last column shows through as a stray brown line.
LABELS = [
    {"cell": 0, "entries": range(13), "box": (0, 1, 95, 16), "lines": ["Map"]},
    {"cell": 32, "entries": range(11), "box": (0, 1, 95, 16),
     "lines": ["World Change"]},
    {"cell": 28, "entries": [0, 1], "box": (19, 2, 40, 14), "lines": ["View"],
     "align": "left", "indent": 2, "claim": True, "bg": 4, "ink": 12},
    {"cell": 33, "entries": [0, 1], "box": (19, 2, 60, 14), "lines": ["OK"],
     "align": "left"},
]


# The dungeon-name tab, cell 34: (x, y, w, h, tile, flip_h). Rounded end on
# the left, then seven body pieces to x 120 (the screen's right edge, drawn at
# x 136): a 112px body for names up to 90px.
TAB_CELL = 34
TAB_ATTR = 0x1F           # cells' bounding value ~ half the diagonal / 2 (cell 0: 0x1B)
TAB = ([(0, 0, 8, 16, 2, True), (0, 16, 8, 8, 4, True)]
       + [p for k in range(7) for p in ((8 + 16 * k, 0, 16, 16, 5, False),
                                        (8 + 16 * k, 16, 16, 8, 0, False))])


def tab_entries():
    """The tab as read_ncer-style dicts (for render / preview)."""
    return [{"x": x, "y": y, "w": w, "h": h, "tile": t, "palette": 0,
             "flip_h": f, "flip_v": False} for x, y, w, h, t, f in TAB]


def add_tab(ncer):
    """NCER bytes with the tab appended as cell 34."""
    from ngfx import ncer_raw, oam_words, rebuild_ncer
    raw = ncer_raw(ncer)
    assert len(raw) == TAB_CELL, "madu_map NCER: expected %d cells" % TAB_CELL
    template = raw[0][3]                      # cell 0's body piece (tile 5)
    assert template[2] & 0x3FF == 5
    cell = []
    for x, y, w, h, t, f in TAB:
        a0, a1, a2 = oam_words(template, x, y, w, h, t)
        cell.append((a0, a1 | (0x1000 if f else 0), a2))
    return rebuild_ncer(ncer, raw + [cell], new_attrs=(TAB_ATTR,))


def paint(narc, workdir):
    bank, ok = so.paint(narc, workdir, MAP_MEMBERS, LABELS)
    narc.regrow(MAP_MEMBERS[2], add_tab(narc.file(MAP_MEMBERS[2])))
    return bank, ok


def main(argv):
    if len(argv) < 2 or argv[1] != "preview":
        print(__doc__)
        return 1
    import tempfile
    from narc import Narc
    from PIL import Image
    root = os.path.dirname(HERE)
    narc = Narc(os.path.join(root, "extracted", "info", "subgraphics",
                             "madu_map.narc"))
    tmp = tempfile.mkdtemp()
    paint(narc, tmp)
    bank = so.load(narc, os.path.join(tmp, "reread"), MAP_MEMBERS)  # the rebuilt NCER
    out = os.path.join(root, "work", "gfx", "map_obj")
    os.makedirs(out, exist_ok=True)
    cells = [0, 28, 32, 33, TAB_CELL]
    ims = [so.render(bank, ci) for ci in cells]
    sheet = Image.new("RGBA", (sum(i.width * 4 + 8 for i in ims),
                               max(i.height for i in ims) * 4 + 8),
                      (110, 110, 110, 255))
    x = 4
    for i in ims:
        j = i.resize((i.width * 4, i.height * 4), Image.NEAREST)
        sheet.paste(j, (x, 4), j)
        x += j.width + 8
    sheet.save(os.path.join(out, "map_obj.png"))
    print("wrote", os.path.join(out, "map_obj.png"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
