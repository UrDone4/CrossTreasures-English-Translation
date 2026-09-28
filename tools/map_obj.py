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
# enabled hints.
LABELS = [
    {"cell": 0, "entries": range(13), "box": (0, 1, 95, 16), "lines": ["Map"]},
    {"cell": 32, "entries": range(11), "box": (0, 1, 95, 16),
     "lines": ["World Change"]},
    {"cell": 28, "entries": [0, 1], "box": (19, 2, 40, 14), "lines": ["View"],
     "align": "left"},
    {"cell": 33, "entries": [0, 1], "box": (19, 2, 60, 14), "lines": ["OK"],
     "align": "left"},
]


def paint(narc, workdir):
    return so.paint(narc, workdir, MAP_MEMBERS, LABELS)


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
    bank, _ = paint(narc, tempfile.mkdtemp())
    out = os.path.join(root, "work", "gfx", "map_obj")
    os.makedirs(out, exist_ok=True)
    cells = [0, 28, 32, 33]
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
