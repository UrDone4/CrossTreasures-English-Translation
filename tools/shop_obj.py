#!/usr/bin/env python3
"""Repaint the shop screen's title pills (an OBJ bank in madu_shop.narc).

Members 14 (NCGR), 15 (NCLR), 13 (NCER). Cell 0 かう (Buy), cell 1 うる (Sell),
cell 10 こうかん (Exchange), cell 11 ひつようなかず (the "needed" tag); cell 6, the
quantity counter コ, is blanked. See skill_obj.py.

    shop_obj.py preview
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import skill_obj as so  # noqa: E402

MEMBERS = (14, 15, 13)
LABELS = [
    # face x 1-57, y 1-16; keep_edges leaves the rounded corners' outline alone.
    # Buy and Exchange had the old (x, 4, x, 20) boxes: row 3 of the Japanese
    # survived and the bottom border and shadow were cleared (hardware, 2026-09-24)
    {"cell": 0, "entries": range(4), "box": (1, 1, 58, 17), "lines": ["Buy"], "keep_edges": True},
    {"cell": 1, "entries": range(4), "box": (1, 1, 58, 17), "lines": ["Sell"], "keep_edges": True},
    {"cell": 10, "entries": range(4), "box": (1, 1, 58, 17), "lines": ["Exchange"], "keep_edges": True},
    # the face's interior is x 3-59, y 3-15: the old box ran over the ends and
    # stopped short of the bottom row, leaving the outline dotted. A plain clear
    # of the exact interior, since ひ and ず's dakuten touch the frame itself
    {"cell": 11, "entries": range(2), "box": (3, 3, 60, 16), "lines": ["Needed"]},
]


# Cell 6 is the quantity counter コ ("pieces") drawn after the digits in the
# Buy / Sell quantity box -- read as a backwards C on hardware (2026-09-25).
# English needs no counter word ("3"), so its two tiles (60-61, used by no other
# cell) are made fully transparent; the white box behind is the background.
BLANK_TILES = (60, 61)


def _blank_tiles(narc, member, tiles):
    import struct
    data = bytearray(narc.file(member))
    off = data.find(b"RAHC")
    assert off >= 0 and struct.unpack_from("<I", data, off + 0xC)[0] == 3, "4bpp NCGR"
    base = off + 0x20
    for t in tiles:
        data[base + t * 32:base + t * 32 + 32] = bytes(32)
    narc.replace(member, bytes(data))


def paint(narc, workdir):
    ok = so.paint(narc, workdir, MEMBERS, LABELS)
    _blank_tiles(narc, MEMBERS[0], BLANK_TILES)
    return ok


def main(argv):
    import tempfile
    from narc import Narc
    from PIL import Image
    root = os.path.dirname(HERE)
    narc = Narc(os.path.join(root, "extracted", "info", "subgraphics", "madu_shop.narc"))
    bank, _ = paint(narc, tempfile.mkdtemp())
    out = os.path.join(root, "work", "gfx", "shop_obj")
    os.makedirs(out, exist_ok=True)
    ims = [so.render(bank, l["cell"]) for l in LABELS]
    sheet = Image.new("RGBA", (300, sum(i.height * 3 + 6 for i in ims)), (110, 110, 110, 255))
    y = 0
    for im in ims:
        j = im.resize((im.width * 3, im.height * 3), Image.NEAREST)
        sheet.paste(j, (0, y), j)
        y += j.height + 6
    sheet.save(os.path.join(out, "shop_obj.png"))
    print("wrote", out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
