#!/usr/bin/env python3
"""Repaint the Jump screen's title bar (an OBJ bank inside madu_jump.narc).

Members 17 (NCGR), 18 (NCLR), 16 (NCER). Cell 2 is the brown title bar ジャンプ,
now "Jump". Cells 0, 1 and 3 are the selection frames (no text). See skill_obj.py.

    jump_obj.py preview     write the title to work/gfx/jump_obj/
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import skill_obj as so  # noqa: E402

JUMP_MEMBERS = (17, 18, 16)
LABELS = [
    {"cell": 2, "entries": range(3), "box": (0, 1, 95, 17), "lines": ["Jump"]},
]


def paint(narc, workdir):
    return so.paint(narc, workdir, JUMP_MEMBERS, LABELS)


def main(argv):
    if len(argv) < 2 or argv[1] != "preview":
        print(__doc__)
        return 1
    import tempfile
    from narc import Narc
    root = os.path.dirname(HERE)
    narc = Narc(os.path.join(root, "extracted", "info", "subgraphics",
                             "madu_jump.narc"))
    bank, _ = paint(narc, tempfile.mkdtemp())
    out = os.path.join(root, "work", "gfx", "jump_obj")
    os.makedirs(out, exist_ok=True)
    im = so.render(bank, 2)
    from PIL import Image
    im.resize((im.width * 4, im.height * 4), Image.NEAREST).save(
        os.path.join(out, "jump_title.png"))
    print("wrote", out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
