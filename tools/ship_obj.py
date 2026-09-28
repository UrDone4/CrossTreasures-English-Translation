#!/usr/bin/env python3
"""Repaint the Ship menu's buttons (an OBJ bank in madu_ship.narc).

Members 9 (NCGR), 10 (NCLR), 8 (NCER). Cells 3-6 are the ship's actions
(いどうする / プレゼントこうかん / みんなであそぶ / かいさんする), cells 7-9 the
destinations (おうさまのおしろ / じげんのめいきゅう / ちかくのしま). Never painted
until 2026-09-24.

Each group shares tiles -- the rounded ends, plain face tiles at the edges and
the bottom strip -- but every button's lettering sits in OAM entries of its
own, so each label writes only through those (`entries`); the shared tiles
stay as drawn.

    ship_obj.py preview     contact sheet in work/gfx/ship_obj/
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import skill_obj as so  # noqa: E402

MEMBERS = (9, 10, 8)
INK = 14            # (123, 74, 0), the Japanese's dark brown
LABELS = [
    {"cell": 3, "entries": range(4, 10), "box": (32, 4, 112, 18), "lines": ["Travel"], "ink": INK},
    {"cell": 4, "entries": range(0, 8), "box": (8, 4, 136, 18), "lines": ["Gift Trade"], "ink": INK},
    {"cell": 5, "entries": range(2, 10), "box": (16, 4, 128, 18), "lines": ["Multiplayer"], "ink": INK},
    {"cell": 6, "entries": range(4, 10), "box": (24, 4, 120, 18), "lines": ["Disband"], "ink": INK},
    {"cell": 7, "entries": range(3, 11), "box": (16, 3, 128, 21), "lines": ["King's Castle"], "ink": INK},
    {"cell": 8, "entries": range(0, 9), "box": (8, 3, 136, 21), "lines": ["Dimensional Labyrinth"], "ink": INK},
    {"cell": 9, "entries": range(0, 9), "box": (16, 3, 128, 21), "lines": ["Nearby Island"], "ink": INK},
]


def paint(narc, workdir):
    return so.paint(narc, workdir, MEMBERS, LABELS)


def main(argv):
    import tempfile
    from narc import Narc
    from PIL import Image
    root = os.path.dirname(HERE)
    narc = Narc(os.path.join(root, "extracted", "info", "subgraphics", "madu_ship.narc"))
    bank, _ = paint(narc, tempfile.mkdtemp())
    out = os.path.join(root, "work", "gfx", "ship_obj")
    os.makedirs(out, exist_ok=True)
    ims = [so.render(bank, l["cell"]) for l in LABELS]
    sheet = Image.new("RGBA", (460, sum(i.height * 3 + 6 for i in ims)), (110, 110, 110, 255))
    y = 0
    for im in ims:
        big = im.resize((im.width * 3, im.height * 3), Image.NEAREST)
        sheet.paste(big, (0, y), big)
        y += big.height + 6
    sheet.save(os.path.join(out, "ship_obj.png"))
    print("wrote", os.path.join(out, "ship_obj.png"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
