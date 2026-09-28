#!/usr/bin/env python3
"""Repaint the Items screen's title bars (an OBJ bank inside madu_item.narc).

Members 12 (NCGR), 13 (NCLR), 11 (NCER). Cell 0 is the brown title bar アイテム
("Items"); cell 2 is the green title bar つけこみ shown on the soaking screen (the
NPC's pickling jar; see the item_14 layer). See skill_obj.py for the machinery.

    item_obj.py preview     write the titles to work/gfx/item_obj/
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import skill_obj as so  # noqa: E402

ITEM_MEMBERS = (12, 13, 11)
LABELS = [
    {"cell": 0, "entries": range(3), "box": (0, 1, 96, 17), "lines": ["Items"]},
    {"cell": 2, "entries": range(4), "box": (0, 1, 96, 17), "lines": ["Soaking"]},
]


def paint(narc, workdir):
    return so.paint(narc, workdir, ITEM_MEMBERS, LABELS)


def main(argv):
    if len(argv) < 2 or argv[1] != "preview":
        print(__doc__)
        return 1
    import tempfile
    from narc import Narc
    from PIL import Image
    root = os.path.dirname(HERE)
    narc = Narc(os.path.join(root, "extracted", "info", "subgraphics",
                             "madu_item.narc"))
    bank, _ = paint(narc, tempfile.mkdtemp())
    out = os.path.join(root, "work", "gfx", "item_obj")
    os.makedirs(out, exist_ok=True)
    ims = [so.render(bank, ci) for ci in (0, 2)]
    sheet = Image.new("RGBA", (ims[0].width * 4 + 8, sum(i.height * 4 + 8 for i in ims)),
                      (110, 110, 110, 255))
    y = 4
    for im in ims:
        j = im.resize((im.width * 4, im.height * 4), Image.NEAREST)
        sheet.paste(j, (4, y), j)
        y += j.height + 8
    sheet.save(os.path.join(out, "item_titles.png"))
    print("wrote", out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
