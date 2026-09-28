#!/usr/bin/env python3
"""Repaint the Memo screen's title bar (an OBJ bank inside madu_memo.narc).

Members 13 (NCGR), 14 (NCLR), 12 (NCER). Cell 0 is the brown title bar メモ,
now "Memos". Cells 1-3 are the closed/open envelope icons and the scroll marker
(no text). See skill_obj.py.

    memo_obj.py preview     write the title to work/gfx/memo_obj/
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import skill_obj as so  # noqa: E402

MEMO_MEMBERS = (13, 14, 12)
LABELS = [
    {"cell": 0, "entries": range(3), "box": (0, 1, 95, 17), "lines": ["Memos"]},
]


def paint(narc, workdir):
    return so.paint(narc, workdir, MEMO_MEMBERS, LABELS)


def main(argv):
    if len(argv) < 2 or argv[1] != "preview":
        print(__doc__)
        return 1
    import tempfile
    from narc import Narc
    root = os.path.dirname(HERE)
    narc = Narc(os.path.join(root, "extracted", "info", "subgraphics",
                             "madu_memo.narc"))
    bank, _ = paint(narc, tempfile.mkdtemp())
    out = os.path.join(root, "work", "gfx", "memo_obj")
    os.makedirs(out, exist_ok=True)
    im = so.render(bank, 0)
    from PIL import Image
    im.resize((im.width * 4, im.height * 4), Image.NEAREST).save(
        os.path.join(out, "memo_title.png"))
    print("wrote", out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
