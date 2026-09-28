#!/usr/bin/env python3
"""Repaint the dungeon lower screen's L / R skill-page pills (an OBJ bank).

madu_battle_<class>.narc members 11 (NCGR), 12 (NCLR), 10 (NCER); the download-play
"_c" archives keep the same trio at 2, 3, 1. Cell 2 is "スキル1" (beside the L badge),
cell 3 is "スキル2" (beside the R badge). See skill_obj.py.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import skill_obj as so  # noqa: E402

MEMBERS = (11, 12, 10)
MEMBERS_C = (2, 3, 1)
LABELS = [
    {"cell": 2, "entries": range(2), "box": (24, 0, 69, 17), "lines": ["Skill 1"]},
    {"cell": 3, "entries": range(2), "box": (2, 0, 47, 17), "lines": ["Skill 2"]},
]


def paint(narc, workdir, members=MEMBERS):
    return so.paint(narc, workdir, members, LABELS)


def main(argv):
    import tempfile
    from narc import Narc
    from PIL import Image
    root = os.path.dirname(HERE)
    narc = Narc(os.path.join(root, "extracted", "info", "subgraphics",
                             "madu_battle_soldier.narc"))
    bank, _ = paint(narc, tempfile.mkdtemp())
    out = os.path.join(root, "work", "gfx", "battle_obj")
    os.makedirs(out, exist_ok=True)
    ims = [so.render(bank, c) for c in (2, 3)]
    sheet = Image.new("RGBA", (ims[0].width * 4, sum(i.height * 4 + 6 for i in ims)),
                      (110, 110, 110, 255))
    y = 0
    for im in ims:
        j = im.resize((im.width * 4, im.height * 4), Image.NEAREST)
        sheet.paste(j, (0, y), j)
        y += j.height + 6
    sheet.save(os.path.join(out, "battle_pills.png"))
    print("wrote", out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
