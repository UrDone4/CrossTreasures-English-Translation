#!/usr/bin/env python3
"""The hand-redrawn battle-triangle art, stored without any of the game's art.

`battle_panels.load_redraw` reads two PNGs per class and skill page:

  work/redraw/<cls>_page<N>.png       the original assembled triangles (layer rows
                                      512-767 of madu_battle_<cls>.narc page N) with
                                      the lettering pixels painted magenta
  work/redraw_done/<cls>_page<N>.png  the same image with the magenta filled in by
                                      hand (plus a row of palette swatches)

The first is the game's art plus a mask, and the second is that plus the redraw.
So the public repository keeps only what is *not* the game's:

  art/<cls>_page<N>_mask.png   white where the lettering was (1-bit shape)
  art/<cls>_page<N>_paint.png  the pixels the artist changed; alpha 0 = unchanged,
                               alpha 1 = made transparent

and `rebuild()` recreates both folders from a ROM dump (`tools/prepare.py`).
Checked 2026-09-26: every original is the ROM render exactly, 0 pixels off.

    redraw_art.py encode <outdir>     work/redraw* -> <outdir>/art/   (dev repo)
    redraw_art.py rebuild             art/ + extracted/ -> work/redraw*  (public)
"""

import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from ngfx import read_png, write_png  # noqa: E402

CLASSES = ("magic", "priest", "soldier", "thief")
PAGES = range(3)
BAND_Y, SIZE = 512, 256
MAGENTA = (255, 0, 255, 255)
CLEAR = (0, 0, 0, 0)


def _rows(path):
    w, h, rows = read_png(path)
    assert (w, h) == (SIZE, SIZE), (path, w, h)
    return [[tuple(r[x * 4:x * 4 + 4]) for x in range(w)] for r in rows]


def _write(path, px):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    write_png(path, SIZE, SIZE, [bytes(v for p in row for v in p) for row in px])


def _opaque(p):
    return p[3] == 255


def _same(a, b):
    """Equal as battle_panels sees them: both transparent, or the same colour."""
    if not _opaque(a) or not _opaque(b):
        return _opaque(a) == _opaque(b)
    return a[:3] == b[:3]


def render(cls, page, root=None):
    """The original assembled triangles from a ROM dump, as RGBA rows."""
    from narc import Narc
    from bgtext import BgLayer
    root = root or os.path.join(BASE, "extracted")
    narc = Narc(os.path.join(root, "info", "subgraphics", "madu_battle_%s.narc" % cls))
    tmp = tempfile.mkdtemp()
    paths = []
    for m in (page * 3, page * 3 + 1, page * 3 + 2):
        p = os.path.join(tmp, str(m))
        with open(p, "wb") as fh:
            fh.write(narc.file(m))
        paths.append(p)
    layer = BgLayer(*paths)
    out = []
    for y in range(SIZE):
        row = []
        for x in range(SIZE):
            c = layer.rgb_at(x, y + BAND_Y)
            row.append(CLEAR if c is None else tuple(c) + (255,))
        out.append(row)
    return out


def encode(outdir):
    for cls in CLASSES:
        for page in PAGES:
            name = "%s_page%d" % (cls, page)
            orig = render(cls, page)
            a = _rows(os.path.join(BASE, "work", "redraw", name + ".png"))
            b = _rows(os.path.join(BASE, "work", "redraw_done", name + ".png"))
            mask, paint = [], []
            for y in range(SIZE):
                mrow, prow = [], []
                for x in range(SIZE):
                    hole = a[y][x] == MAGENTA
                    if not hole and not _same(a[y][x], orig[y][x]):
                        raise SystemExit("%s: original differs from the ROM at %d,%d"
                                         % (name, x, y))
                    mrow.append((255, 255, 255, 255) if hole else CLEAR)
                    if _same(a[y][x], b[y][x]):
                        prow.append(CLEAR)
                    elif not _opaque(b[y][x]):
                        prow.append((0, 0, 0, 1))
                    else:
                        prow.append(b[y][x][:3] + (255,))
                mask.append(mrow)
                paint.append(prow)
            _write(os.path.join(outdir, "art", name + "_mask.png"), mask)
            _write(os.path.join(outdir, "art", name + "_paint.png"), paint)
    print("encoded %d pages to %s" % (len(CLASSES) * len(PAGES), os.path.join(outdir, "art")))


def rebuild(root=BASE):
    for cls in CLASSES:
        for page in PAGES:
            name = "%s_page%d" % (cls, page)
            orig = render(cls, page, os.path.join(root, "extracted"))
            mask = _rows(os.path.join(root, "art", name + "_mask.png"))
            paint = _rows(os.path.join(root, "art", name + "_paint.png"))
            a = [[MAGENTA if mask[y][x][3] else orig[y][x] for x in range(SIZE)]
                 for y in range(SIZE)]
            b = [[a[y][x] if paint[y][x][3] == 0 else
                  CLEAR if paint[y][x][3] == 1 else paint[y][x]
                  for x in range(SIZE)] for y in range(SIZE)]
            _write(os.path.join(root, "work", "redraw", name + ".png"), a)
            _write(os.path.join(root, "work", "redraw_done", name + ".png"), b)
    print("rebuilt work/redraw and work/redraw_done (%d pages)"
          % (len(CLASSES) * len(PAGES)))


def main(argv):
    if len(argv) >= 3 and argv[1] == "encode":
        encode(argv[2])
    elif len(argv) >= 2 and argv[1] == "rebuild":
        rebuild()
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
