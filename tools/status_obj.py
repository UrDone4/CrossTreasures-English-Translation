#!/usr/bin/env python3
"""Repaint the Status screen's title bar (an OBJ bank inside madu_status.narc).

Members 33 (NCGR), 34 (NCLR), 32 (NCER). Cell 0 is the brown title bar that
reads つよさ on every tab of the screen -- formerly "Strength", now "Status" (the
screen is really a set of tabs about the player: level, stats, nutrition, hot
spring, ramen, artisan). Cells 1 and 2 are the empty ramen / hot-spring effect
frames and carry no text. See skill_obj.py for the machinery.

    status_obj.py preview     write the title to work/gfx/status_obj/
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import skill_obj as so  # noqa: E402

STATUS_MEMBERS = (33, 34, 32)
LABELS = [
    {"cell": 0, "entries": range(4), "box": (0, 1, 95, 16), "lines": ["Status"]},
]


def paint(narc, workdir):
    return so.paint(narc, workdir, STATUS_MEMBERS, LABELS)


def main(argv):
    if len(argv) < 2 or argv[1] != "preview":
        print(__doc__)
        return 1
    import tempfile
    from narc import Narc
    root = os.path.dirname(HERE)
    narc = Narc(os.path.join(root, "extracted", "info", "subgraphics",
                             "madu_status.narc"))
    bank, _ = paint(narc, tempfile.mkdtemp())
    out = os.path.join(root, "work", "gfx", "status_obj")
    os.makedirs(out, exist_ok=True)
    im = so.render(bank, 0)
    from PIL import Image
    im.resize((im.width * 4, im.height * 4), Image.NEAREST).save(
        os.path.join(out, "status_title.png"))
    print("wrote", out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
