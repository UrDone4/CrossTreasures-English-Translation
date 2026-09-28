#!/usr/bin/env python3
"""Repaint the Quest screen's title bar (an OBJ bank inside madu_quest.narc).

Members 12 (NCGR), 13 (NCLR), 11 (NCER). Cell 0 is the brown title bar クエスト,
now "Quest". Cells 1-4 are the friendship hearts and cell 5 the red クリア！
("Clear!") stamp on completed quests, now "CLEAR!". The stamp is 30x11 with a
7-row face, too small for the font (10px capitals), so the word is drawn from
the 4x7 pixel letters below. See skill_obj.py.

    quest_obj.py preview     write the title to work/gfx/quest_obj/
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import skill_obj as so  # noqa: E402

QUEST_MEMBERS = (12, 13, 11)
LABELS = [
    {"cell": 0, "entries": range(8), "box": (0, 1, 95, 16), "lines": ["Quest"]},
]


# 4x7 capitals for the Clear! stamp (white on its red face)
STAMP_FONT = {
    "C": (".###", "#...", "#...", "#...", "#...", "#...", ".###"),
    "L": ("#...", "#...", "#...", "#...", "#...", "#...", "####"),
    "E": ("####", "#...", "#...", "###.", "#...", "#...", "####"),
    "A": (".##.", "#..#", "#..#", "####", "#..#", "#..#", "#..#"),
    "R": ("###.", "#..#", "#..#", "###.", "#.#.", "#..#", "#..#"),
    "!": ("#", "#", "#", "#", "#", ".", "#"),
}
STAMP = {"cell": 5, "clear": (2, 1, 29, 10), "bg": 3, "ink": 11,
         "word": "CLEAR!", "at": (3, 2)}


def paint_stamp(bank, spec=STAMP):
    """Clear the stamp's face (rows 1-9 inside its red rim) and draw the word
    from STAMP_FONT, one pixel between letters."""
    ci = spec["cell"]
    entries = range(len(bank.cells[ci]))
    ox, oy = so.origin(bank, ci)
    x0, y0, x1, y1 = spec["clear"]
    for y in range(y0, y1):
        for x in range(x0, x1):
            pos = so.owner(bank, ci, entries, x + ox, y + oy)
            if pos is not None:
                bank.flat[pos] = spec["bg"]
    pen, top = spec["at"]
    for ch in spec["word"]:
        rows = STAMP_FONT[ch]
        for dy, row in enumerate(rows):
            for dx, c in enumerate(row):
                if c == "#":
                    pos = so.owner(bank, ci, entries, pen + dx + ox, top + dy + oy)
                    if pos is None:
                        raise SystemExit("Clear! stamp: (%d, %d) is outside the cell"
                                         % (pen + dx, top + dy))
                    bank.flat[pos] = spec["ink"]
        pen += len(rows[0]) + 1
    if pen - 1 > x1:
        raise SystemExit("Clear! stamp: the word runs past x %d" % x1)
    print("  cell %2d  %s  stamp" % (ci, spec["word"]))


def paint(narc, workdir):
    """As skill_obj.paint, plus the Clear! stamp."""
    bank = so.load(narc, workdir, QUEST_MEMBERS)
    font = so.load_font()
    ok = True
    for spec in LABELS:
        ok &= so.paint_label(bank, font, spec)
    paint_stamp(bank)
    out = os.path.join(workdir, "quest_obj_out.NCGR")
    bank.save(out)
    data = open(out, "rb").read()
    if len(data) != len(narc.file(QUEST_MEMBERS[0])):
        raise SystemExit("NCGR size changed -- refusing")
    narc.replace(QUEST_MEMBERS[0], data)
    return bank, ok


def main(argv):
    if len(argv) < 2 or argv[1] != "preview":
        print(__doc__)
        return 1
    import tempfile
    from narc import Narc
    root = os.path.dirname(HERE)
    narc = Narc(os.path.join(root, "extracted", "info", "subgraphics",
                             "madu_quest.narc"))
    bank, _ = paint(narc, tempfile.mkdtemp())
    out = os.path.join(root, "work", "gfx", "quest_obj")
    os.makedirs(out, exist_ok=True)
    im = so.render(bank, 0)
    from PIL import Image
    im.resize((im.width * 4, im.height * 4), Image.NEAREST).save(
        os.path.join(out, "quest_title.png"))
    print("wrote", out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
