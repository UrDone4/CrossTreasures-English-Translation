#!/usr/bin/env python3
"""Repaint the Medals screen's title bar (an OBJ bank inside madu_medal.narc).

Members 18 (NCGR), 19 (NCLR), 17 (NCER). Cell 0 is the brown title bar メダリオン,
now "Medals" -- the screen's own captions say Medals, so the bar and the main-menu
button follow. Cell 1 is the "NEW!" tag, already English. See skill_obj.py.

    medal_obj.py preview     write the title to work/gfx/medal_obj/
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import skill_obj as so  # noqa: E402

MEDAL_MEMBERS = (18, 19, 17)
LABELS = [
    {"cell": 0, "entries": range(8), "box": (0, 1, 95, 17), "lines": ["Medals"]},
]


def paint(narc, workdir):
    return so.paint(narc, workdir, MEDAL_MEMBERS, LABELS)


def main(argv):
    if len(argv) < 2 or argv[1] != "preview":
        print(__doc__)
        return 1
    import tempfile
    from narc import Narc
    root = os.path.dirname(HERE)
    narc = Narc(os.path.join(root, "extracted", "info", "subgraphics",
                             "madu_medal.narc"))
    bank, _ = paint(narc, tempfile.mkdtemp())
    out = os.path.join(root, "work", "gfx", "medal_obj")
    os.makedirs(out, exist_ok=True)
    im = so.render(bank, 0)
    from PIL import Image
    im.resize((im.width * 4, im.height * 4), Image.NEAREST).save(
        os.path.join(out, "medal_title.png"))
    print("wrote", out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
