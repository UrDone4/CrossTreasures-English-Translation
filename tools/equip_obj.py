#!/usr/bin/env python3
"""Repaint the Equipment screen's sprite banks (three OBJ banks in madu_equip.narc).

  members 28/29/27  cell 0     the screen title そうび -> "Equipment"
  members 18/19/17  cells 0-4  quality tags ふつう よい すごい さいこう かんぺき
  members  6/ 7/ 5  cells 0-63 the 32 equipment-effect tags: a long form (cells
                               0-31, 48px) and a short form (32-63, 21px)

The same two banks also exist as **loose files** (`info/common/icon_qua.*`,
`info/common/icon_eff.*`, byte-identical to members 18/19/17 and 6/7/5); the
Workshop's Details / Effect pages draw from those, so `apply_loose()` paints them
too (written to <gfx_out>/common/, installed by build_patch). Found 2026-09-25
from hardware shots still showing ふつう / ムキムキ in the Workshop.

**The long form is the short form drawn twice.** ワクワク is ワク + ワク: cell N and
cell N+32 point at the same six tiles, and the long cell places them at two x
positions inside one 48px pill (frame tiles shared by all 32). So painting the
short cell paints both, and the English shows twice ("Fire Fire"), as the
Japanese does -- which is at least a familiar shape for a doubled nickname.
Distinct text per half would need 32 x 6 more tiles and the sheet has ~20 spare
(the game uploads only the original tile count, so it cannot grow). Removing the
left copy instead leaves that half of the pill transparent. Hence 3-4 letter tags,
each at most 21px, and the description beside the tag says what the effect is.

The effect tags are the onomatopoeia nicknames of equip_effect.dat's 32 traits
(ワクワク = item drops up, ドクドク = poison attack ...). The descriptions beside
them live in that table and are translated in work/data_text.tsv; the tags
themselves are graphics. Their pills are banded top to bottom, so the fill under
the old lettering is taken row by row from the pill's own left edge rather than
one flat colour. See skill_obj.py for the sprite machinery (inverted OAM
priority, writes only through a cell's own entries).

    equip_obj.py preview     contact sheets in work/gfx/equip_obj/
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import skill_obj as so  # noqa: E402
from bgtext import load_font  # noqa: E402

TITLE = (28, 29, 27)
QUALITY = (18, 19, 17)
EFFECT = (6, 7, 5)

# (long form, short form) per effect id 0..31. Only the short form is drawn (see
# above; the long is kept for the record). The pill is 21px inside; anything
# wider is reported, not clipped. Wording chosen with the user (2026-09-26):
# Refl (was Thn), Thd = Thunder (the game's word; was Bolt), Luv, Rch (was
# Chg), HP+/MP+ for recover-on-kill and HP↑/MP↑ (GLYPHS) for max up.
# Tag N = effect N is verified from the Japanese art (トゲ reflect, ジワ / キラ
# kill-recover, タフ / マナ max HP / MP ...).
EFFECTS = [
    ("Item Get", "Item"), ("Gold Get", "Gold"), ("Growth", "Grw"),
    ("Reflect", "Refl"), ("Fire Atk", "Fire"), ("Ice Atk", "Ice"),
    ("Thunder Atk", "Thd"), ("Love Atk", "Luv"), ("Kill HP", "HP+"),
    ("Kill MP", "MP+"), ("Attack", "Atk"), ("Defense", "Def"),
    ("Critical", "Crit"), ("Power", "Pow"), ("Speed", "Spd"),
    ("Magic", "Mag"), ("Max HP", "HP\u2191"), ("Max MP", "MP\u2191"),
    ("Move", "Mov"), ("Fire Res", "Fire"), ("Ice Res", "Ice"),
    ("Thunder Res", "Thd"), ("Nullify", "Null"), ("Recharge", "Rch"),
    ("Dizzy", "Diz"), ("Poison", "Psn"), ("Para", "Par"),
    ("Sleep", "Slp"), ("Diz Res", "Diz"), ("Psn Res", "Psn"),
    ("Par Res", "Par"), ("Slp Res", "Slp"),
]
# Hand-drawn glyphs the font lacks, usable in any tag: rows top-down on the
# font's 10-row cap height, and the advance (width + 1px gap).
GLYPHS = {
    "\u2191": (6, ["..#..",       # up arrow, for "HP\u2191" = Max HP up
                   ".###.",
                   "#####",
                   "..#..",
                   "..#..",
                   "..#..",
                   "..#..",
                   "..#..",
                   "..#..",
                   "..#.."]),
}

# "Perfect" (40px) does not fit the 36px pill; "Ideal" keeps the ladder
QUALITIES = ["Normal", "Good", "Great", "Best", "Ideal"]


def lum(c):
    return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]


def paint_tag(bank, font, ci, text, box, bgcol=None, top=2, flat=False, ink_rgb=None):
    """Clear a banded pill's lettering row by row and draw `text` centred.

    `ink_rgb=(r,g,b)` is for pills where luminance can't separate lettering
    from fill -- a gradient fill with *white* lettering (e.g.
    shop_equip_obj.py's stat pills) has background rows running from near-
    white to deep colour, so both "darkest colour present" and "lightest
    colour present" can land on a fill shade instead of the real ink,
    depending on the row. Match the known ink colour exactly instead.
    """
    ents = set(range(len(bank.cells[ci])))
    ox, oy = so.origin(bank, ci)
    x0, y0, x1, y1 = box
    cover, bg_row = {}, {}
    for y in range(y0, y1):
        for x in range(x0, x1):
            pos = so.owner(bank, ci, ents, x + ox, y + oy)
            if pos is not None:
                cover[(x, y)] = pos
    if not cover:
        print("  cell %d: nothing editable" % ci)
        return False
    # ink: the darkest index present, i.e. the lettering's own colour -- or an
    # exact colour match, for a gradient-fill pill (see ink_rgb above)
    used = {bank.flat[p] for p in cover.values()}
    if ink_rgb is not None:
        matches = [i for i in used if so.rgb(bank, ci, 0, i) == ink_rgb]
        if not matches:
            print("  !! cell %d: no colour matches ink_rgb=%r" % (ci, ink_rgb))
            return False
        ink = matches[0]
    else:
        ink = min(used, key=lambda i: lum(so.rgb(bank, ci, 0, i)))
    # the fill of each row is read from the pill's own edge: the last interior
    # column (or `bgcol`), which the lettering never reaches. A per-row mode does
    # not work -- on the rows that are mostly lettering it picks the lettering.
    edge = x1 - 1 if bgcol is None else bgcol
    for y in range(y0, y1):
        p = cover.get((edge, y))
        if p is not None:
            bg_row[y] = bank.flat[p]
    if flat:                          # a flat-filled pill: one colour throughout
        import collections
        mode = collections.Counter(bank.flat[p] for p in cover.values()
                                   if bank.flat[p] != ink).most_common(1)[0][0]
        bg_row = {y: mode for y in range(y0, y1)}
    for (x, y), pos in cover.items():
        if y in bg_row:
            bank.flat[pos] = bg_row[y]
    def adv(c):
        return GLYPHS[c][0] if c in GLYPHS else font.advance(ord(c))
    width = sum(adv(c) for c in text)
    room = x1 - x0
    pen = x0 + (room - width) // 2
    clipped = 0
    for ch in text:
        gi = font.cmap.get(ord(ch))
        if ch in GLYPHS:
            for r, row in enumerate(GLYPHS[ch][1]):
                for c, px in enumerate(row):
                    if px == "#":
                        pos = cover.get((pen + c, top + r))
                        if pos is None:
                            clipped += 1
                        else:
                            bank.flat[pos] = ink
        elif gi is not None:
            bits = font.bitmap(gi)
            for r in range(font.cell_h):
                for c in range(font.cell_w):
                    if bits[r][c]:
                        pos = cover.get((pen + c, top + r))
                        if pos is None:
                            clipped += 1
                        else:
                            bank.flat[pos] = ink
        pen += adv(ch)
    if width > room or clipped:
        print("  !! cell %d %r: %dpx in %dpx, %d px clipped"
              % (ci, text, width, room, clipped))
        return False
    return True


def single_long(ncer):
    """Show the long effect tags' word once, with no frame (user, 2026-09-25:
    "Par Par" looked silly; a framed single word left the frame half empty, and
    the sheet has no spare tiles to fill it -- 198 tiles, all used).

    Cells 0-31 draw the short tag's tiles twice -- entries 0-1 at x 22 / 38,
    entries 2-3 at x 1 / 17 -- inside a 48px frame (entries 4-7). Both copies
    move to x 12 / 28, exactly on top of each other (the word appears once,
    centred in the old frame's place), and the frame entries are hidden: OAM
    attr0 bit 9 (OBJ disable; no rotation on these) plus an x of -256 so they
    would be off-screen anyway. Only OAM attributes change."""
    import struct
    d = bytearray(ncer)
    off = d.find(b"KBEC")
    n_cells, bank_type = struct.unpack_from("<HH", d, off + 8)
    base = off + 8 + struct.unpack_from("<I", d, off + 12)[0]
    step = 16 if bank_type == 1 else 8
    oam_base = base + n_cells * step
    for ci in range(32):
        n_oam, _attr, oam_off = struct.unpack_from("<HHI", d, base + ci * step)
        assert n_oam == 8, (ci, n_oam)
        for k, (old_x, new_x) in enumerate(((22, 12), (38, 28), (1, 12), (17, 28))):
            p = oam_base + oam_off + k * 6
            a0, a1 = struct.unpack_from("<HH", d, p)
            assert a1 & 0x1FF == old_x, (ci, k, a1 & 0x1FF)
            struct.pack_into("<H", d, p + 2, (a1 & ~0x1FF) | new_x)
        for k in range(4, 8):
            p = oam_base + oam_off + k * 6
            a0, a1 = struct.unpack_from("<HH", d, p)
            assert not a0 & 0x100, "frame entry uses rotation"
            struct.pack_into("<H", d, p, a0 | 0x200)
            struct.pack_into("<H", d, p + 2, (a1 & ~0x1FF) | 0x100)
    return bytes(d)


def paint_bank(narc, workdir, members, fn):
    bank = so.load(narc, workdir, members)
    font = load_font()
    ok = fn(bank, font)
    out = os.path.join(workdir, "out.NCGR")
    bank.save(out)
    data = open(out, "rb").read()
    if len(data) != len(narc.file(members[0])):
        raise SystemExit("NCGR size changed -- refusing")
    narc.replace(members[0], data)
    return bank, ok


def _title(bank, font):
    return so.paint_label(bank, font, {
        "cell": 0, "entries": range(len(bank.cells[0])),
        "box": (0, 1, 95, 16), "lines": ["Equipment"]})


def _quality(bank, font):
    ok = True
    for ci, text in enumerate(QUALITIES):
        ok &= paint_tag(bank, font, ci, text, (2, 2, 38, 14), flat=True)
    return ok


def _effects(bank, font):
    ok = True
    for i, (_long, short) in enumerate(EFFECTS):
        # マナマナ runs to the right edge, so its band is read from the left one
        ok &= paint_tag(bank, font, 32 + i, short, (0, 0, 21, 13), top=1,
                        bgcol=0 if i == 17 else None)
    return ok


def paint(narc, workdir):
    ok = True
    for name, members, fn in (("title", TITLE, _title),
                              ("quality", QUALITY, _quality),
                              ("effects", EFFECT, _effects)):
        _bank, good = paint_bank(narc, os.path.join(workdir, name), members, fn)
        ok &= bool(good)
    narc.replace(EFFECT[2], single_long(narc.file(EFFECT[2])))
    return ok


class _Loose:
    """Minimal NARC stand-in over a loose NCGR/NCLR/NCER trio (members 0/1/2)."""

    def __init__(self, base):
        self.paths = [base + ext for ext in (".NCGR", ".NCLR", ".NCER")]
        self.data = [open(p, "rb").read() for p in self.paths]

    def file(self, i):
        return self.data[i]

    def replace(self, i, blob):
        self.data[i] = blob


def apply_loose(outdir):
    """Paint info/common/icon_qua and icon_eff; write <outdir>/common/*.NCGR."""
    import tempfile
    root = os.path.dirname(HERE)
    dst = os.path.join(outdir, "common")
    os.makedirs(dst, exist_ok=True)
    ok = True
    for name, fn in (("icon_qua", _quality), ("icon_eff", _effects)):
        loose = _Loose(os.path.join(root, "extracted", "info", "common", name))
        _bank, good = paint_bank(loose, tempfile.mkdtemp(), (0, 1, 2), fn)
        ok &= bool(good)
        with open(os.path.join(dst, name + ".NCGR"), "wb") as fh:
            fh.write(loose.file(0))
        print("  wrote %s/common/%s.NCGR" % (outdir, name))
        if name == "icon_eff":
            with open(os.path.join(dst, name + ".NCER"), "wb") as fh:
                fh.write(single_long(loose.file(2)))
            print("  wrote %s/common/%s.NCER" % (outdir, name))
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
                             "madu_equip.narc"))
    tmp = tempfile.mkdtemp()
    out = os.path.join(root, "work", "gfx", "equip_obj")
    os.makedirs(out, exist_ok=True)
    for name, members, fn, cells, cols in (
            ("title", TITLE, _title, [0], 1),
            ("quality", QUALITY, _quality, list(range(5)), 5),
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
