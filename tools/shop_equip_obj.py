#!/usr/bin/env python3
"""Repaint two of madu_shop_equip.narc's sprite banks (Tika's Equipment Sell page).

This is the shop's *own* copy of graphics equip_obj.py already handles for the
player's regular Equipment screen -- same tags, same banded-pill painter
(tools/equip_obj.py's paint_tag), different narc, so the shop was left showing
Japanese even after the main Equipment screen was translated.

  members 15/14/13   cells 0-4   quality tags ふつう よい すごい さいこう かんぺき
                                  (identical wording/order to equip_obj.py's
                                  QUALITY bank -- same QUALITIES list reused)
  members 23/22/21   cells 5-8   stat-name pills こうげきりょく/ぼうぎょりょく
                                  (Attack/Defense), two sizes (104px cells 5-6,
                                  80px cells 7-8) -- cell 9 is an unused blank
                                  template pill, left alone
  members  5/ 6/ 4   cells 0-63  the 32 equipment-effect tags (ヒエヒエ, ムキムキ ...):
                                  byte-identical to madu_equip's 6/7/5, painted
                                  with equip_obj's _effects (short forms, drawn
                                  twice in the long cells). Missed until the
                                  user's 2026-09-25 hardware shots of the shop's
                                  equipment Effect page.

    shop_equip_obj.py preview     contact sheets in work/gfx/shop_equip_obj/
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import skill_obj as so  # noqa: E402
from bgtext import load_font  # noqa: E402
from equip_obj import paint_tag, paint_bank, QUALITIES, _effects, single_long  # noqa: E402

QUALITY = (14, 15, 13)
STATS = (22, 23, 21)
EFFECT = (5, 6, 4)


def _quality(bank, font):
    ok = True
    for ci, text in enumerate(QUALITIES):
        ok &= paint_tag(bank, font, ci, text, (2, 2, 38, 14), flat=True)
    return ok


def _stats(bank, font):
    # Two-tone, like "Made By" on the equip screen itself: a solid-colour
    # label chip (white lettering) beside a blank white value field that is
    # part of the same pill; the box stops short of the field so flat-fill's
    # "most common non-ink colour" is the chip's.
    #
    # Cells 5+6 (and 7+8) share their border tiles (5/6: tile 44, the 16x8
    # strips along the top and bottom, plus the right-hand end tiles), but
    # each cell's lettering sits in two entries of its *own* that are drawn
    # on top of those strips: x 3-66, rows 6-21 in cells 5/6 (tiles 18-33 /
    # 48-63), x 3-50, rows 5-20 in cells 7/8. The Japanese never leaves them
    # (rows 6-15 / 6-14). The old boxes reached rows 0-5 and drew from row 2,
    # i.e. into the shared tiles, so each pill painted over the other's
    # borders -- the "garbled" pills seen on hardware. Keeping the clear and
    # the text inside the private rows (text from row 6 / 5; the font's
    # capitals are 10px) touches no shared tile, so no privatisation needed.
    ok = True
    for ci in (5, 6):
        ok &= paint_tag(bank, font, ci, "Attack" if ci == 5 else "Defense",
                        (3, 6, 62, 22), ink_rgb=(255, 255, 255), flat=True, top=6)
    for ci in (7, 8):
        ok &= paint_tag(bank, font, ci, "Attack" if ci == 7 else "Defense",
                        (3, 5, 51, 16), ink_rgb=(255, 255, 255), flat=True, top=5)
    return ok


def paint(narc, workdir):
    ok = True
    for name, members, fn in (("quality", QUALITY, _quality),
                              ("stats", STATS, _stats),
                              ("effects", EFFECT, _effects)):
        _bank, good = paint_bank(narc, os.path.join(workdir, name), members, fn)
        ok &= bool(good)
    narc.replace(EFFECT[2], single_long(narc.file(EFFECT[2])))
    return ok


def main(argv):
    if len(argv) < 2 or argv[1] != "preview":
        print(__doc__)
        return 1
    import tempfile
    from narc import Narc
    from PIL import Image
    root = os.path.dirname(HERE)
    narc = Narc(os.path.join(root, "extracted", "info", "subgraphics",
                             "madu_shop_equip.narc"))
    tmp = tempfile.mkdtemp()
    out = os.path.join(root, "work", "gfx", "shop_equip_obj")
    os.makedirs(out, exist_ok=True)
    for name, members, fn, cells, cols in (
            ("quality", QUALITY, _quality, list(range(5)), 5),
            ("stats", STATS, _stats, [5, 6, 7, 8], 4),
            ("effects", EFFECT, _effects, list(range(64)), 8)):
        bank, _ = paint_bank(narc, os.path.join(tmp, name), members, fn)
        ims = [so.render(bank, ci) for ci in cells]
        cw = max(i.width for i in ims) * 3 + 6
        ch = max(i.height for i in ims) * 3 + 6
        sheet = Image.new("RGBA", (cols * cw, ((len(ims) + cols - 1) // cols) * ch),
                          (110, 110, 110, 255))
        for k, im in enumerate(ims):
            j = im.resize((im.width * 3, im.height * 3), Image.NEAREST)
            sheet.paste(j, ((k % cols) * cw + 3, (k // cols) * ch + 3), j)
        sheet.save(os.path.join(out, name + ".png"))
    print("wrote", out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
