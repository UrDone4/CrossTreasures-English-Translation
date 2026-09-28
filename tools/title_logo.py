#!/usr/bin/env python3
"""The title screen's "START をおしてね！！" prompt, repainted as "START to begin!".

The pill is not a sprite: it is baked into the logo layer
`info/title/title_rog_000.ncg` -- an **8bpp** NCCG (768 tiles, one per screen
cell; the .nsc map is the identity), which nbg.py's 4bpp-first guess misreads as
garbage. The pill sits at x 78-173, y 162-176; the orange START badge ends at
x 110 and the Japanese is brown (palette 31, dark 123,74,0) with anti-aliasing
on the white face (palette 94) at x 111-171, y 165-173. (`info/title/title_start`
is an unused leftover with the same art -- options_obj still paints it, harmlessly.)

`build()` returns (rel_path, bytes) for build_patch.py; `preview OUT.png` writes a
3x crop of the result for checking.
"""

import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import nbg  # noqa: E402
from bgtext import load_font  # noqa: E402

REL = "info/title/title_rog_000.ncg"
SRC = os.path.join(os.path.dirname(HERE), "extracted", REL)

TEXT = "to begin!"
CLEAR = (112, 164, 172, 175)   # x0, y0, x1, y1 (exclusive): the Japanese only
FACE, INK = 94, 31             # white face, dark brown (the Japanese's darkest)
TOP = 164                      # glyph row 0 (ascenders); descenders end at 174


def _layout(font, text, bold=1):
    """[(x, y)] ink pixels of `text`, bold = double-struck 1px right."""
    pts, pen = set(), 0
    for ch in text:
        gi = font.cmap.get(ord(ch))
        if gi is not None:
            bits = font.bitmap(gi)
            for r in range(font.cell_h):
                for c in range(font.cell_w):
                    if bits[r][c]:
                        for dx in range(bold + 1):
                            pts.add((pen + c + dx, r))
        pen += font.advance(ord(ch)) + bold
    return pts, pen - bold


def paint(data):
    d = bytearray(data)
    off, size = nbg.blocks(d)[b"CHAR"]
    base = off + size - 768 * 64

    def at(x, y):
        return base + ((y // 8) * 32 + x // 8) * 64 + (y % 8) * 8 + x % 8

    x0, y0, x1, y1 = CLEAR
    for y in range(y0, y1):
        for x in range(x0, x1):
            d[at(x, y)] = FACE
    pts, width = _layout(load_font(), TEXT)
    left = x0 + (x1 - x0 - width) // 2
    for px, py in pts:
        x, y = left + px, TOP + py
        assert x0 <= x < x1 and y0 <= y < y1, (TEXT, x, y)
        d[at(x, y)] = INK
    return bytes(d)


def build():
    with open(SRC, "rb") as fh:
        return REL, paint(fh.read())


def preview(out_png, zoom=3):
    import ngfx
    d = build()[1]
    off, size = nbg.blocks(d)[b"CHAR"]
    tiles = d[off + size - 768 * 64:off + size]
    pal = nbg.read_nccl(SRC[:-4] + ".ncl")
    x0, y0, x1, y1 = 72, 156, 184, 182
    rows = []
    for y in range(y0, y1):
        row = []
        for x in range(x0, x1):
            v = tiles[((y // 8) * 32 + x // 8) * 64 + (y % 8) * 8 + x % 8]
            row += list(pal[v]) * zoom
        rows += [row] * zoom
    ngfx.write_png(out_png, (x1 - x0) * zoom, (y1 - y0) * zoom, rows)


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "preview":
        preview(sys.argv[2])
    else:
        print(__doc__)
