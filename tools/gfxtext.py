#!/usr/bin/env python3
"""Paint English labels into NCGR sprite banks using the game's own font.

Title-screen and menu labels are sprites, not text, so translating them means
repainting pixels. This renders glyphs from LCFont.NFTR straight into the
tilesheet, which keeps the lettering consistent with the rest of the game and
needs no external art.

Writing back is the inverse of the 1D-mapped cell render in ngfx.py: a cell
pixel is located by finding the last OAM entry that covers it (later entries
draw over earlier ones), then walking that entry's consecutive tiles.

    gfxtext.py preview <name> <cell> <text>     render to a PNG, change nothing
    gfxtext.py list    <name>                   show cells and their geometry
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from ngfx import (read_nclr, read_ncgr, read_ncer, write_png,  # noqa: E402
                  write_ncgr_like, render_cell, TILE)
from nftr import Nftr  # noqa: E402

TITLE_DIR = os.path.join(os.path.dirname(HERE), "extracted", "info", "title")
FONT = os.path.join(os.path.dirname(HERE), "extracted", "LCFont.NFTR")


class Bank:
    """An NCGR/NCLR/NCER trio, editable in cell space."""

    def __init__(self, base):
        self.base = base
        self.palette, _ = read_nclr(base + ".NCLR")
        self.flat, self.w, self.h, self.bpp = read_ncgr(base + ".NCGR")
        self.cells = read_ncer(base + ".NCER")
        self.tiles_w = self.w // TILE
        self.only = None        # restrict writes to these OAM entries (see gfx_labels)
        while len(self.palette) < 16:
            self.palette.append((255, 0, 255, 255))

    # ---- cell-space addressing -----------------------------------------
    def origin(self, ci):
        entries = self.cells[ci]
        return (min(e["x"] for e in entries), min(e["y"] for e in entries))

    def size(self, ci):
        entries = self.cells[ci]
        ox, oy = self.origin(ci)
        return (max(e["x"] + e["w"] for e in entries) - ox,
                max(e["y"] + e["h"] for e in entries) - oy)

    def _covering(self, ci, cx, cy):
        """Every OAM entry of the cell that covers this pixel, with its offset.

        Sprites within a cell overlap. When compositing, a later entry only
        wins where it is opaque, so an earlier entry showing through is normal.
        That means a write must touch *all* covering entries: clearing only the
        topmost leaves the lower one's pixels visible (seen in-game as a ghost
        of the original lettering's drop shadow).
        """
        ox, oy = self.origin(ci)
        ax, ay = cx + ox, cy + oy
        out = []
        for k, e in enumerate(self.cells[ci]):
            if self.only is not None and k not in self.only:
                continue
            if e["x"] <= ax < e["x"] + e["w"] and e["y"] <= ay < e["y"] + e["h"]:
                col, row = ax - e["x"], ay - e["y"]
                if e["flip_h"]:
                    col = e["w"] - 1 - col
                if e["flip_v"]:
                    row = e["h"] - 1 - row
                span = e["w"] // TILE
                t = e["tile"] + (row // TILE) * span + (col // TILE)
                sx = (t % self.tiles_w) * TILE + col % TILE
                sy = (t // self.tiles_w) * TILE + row % TILE
                pos = sy * self.w + sx
                if pos < len(self.flat):
                    out.append(pos)
        return out

    def _sheet_pos(self, ci, cx, cy):
        """Sheet offset for a cell pixel in the topmost covering entry."""
        positions = self._covering(ci, cx, cy)
        return positions[-1] if positions else None

    def get(self, ci, cx, cy):
        pos = self._sheet_pos(ci, cx, cy)
        return self.flat[pos] if pos is not None else 0

    def put(self, ci, cx, cy, index):
        for pos in self._covering(ci, cx, cy):
            self.flat[pos] = index

    # ---- painting --------------------------------------------------------
    def fill(self, ci, box, index):
        x0, y0, x1, y1 = box
        for y in range(y0, y1):
            for x in range(x0, x1):
                self.put(ci, x, y, index)

    def text_width(self, font, text, scale):
        return sum(font.advance(ord(c)) for c in text) * scale

    def draw_text(self, ci, font, text, box, ink, scale=1, shadow=None):
        """Draw text centred in box=(x0,y0,x1,y1). Returns False if too wide."""
        x0, y0, x1, y1 = box
        width = self.text_width(font, text, scale)
        if width > x1 - x0:
            return False
        pen = x0 + (x1 - x0 - width) // 2
        top = y0 + (y1 - y0 - font.cell_h * scale) // 2
        for ch in text:
            gi = font.cmap.get(ord(ch))
            if gi is None:
                pen += font.advance(ord(" ")) * scale
                continue
            bits = font.bitmap(gi)
            for row in range(font.cell_h):
                for col in range(font.cell_w):
                    if not bits[row][col]:
                        continue
                    for sy in range(scale):
                        for sx in range(scale):
                            px, py = pen + col * scale + sx, top + row * scale + sy
                            if shadow is not None:
                                self.put(ci, px + scale, py + scale, shadow)
                            self.put(ci, px, py, ink)
            pen += font.advance(ord(ch)) * scale
        return True

    def clear(self, ci, index=0):
        w, h = self.size(ci)
        for y in range(h):
            for x in range(w):
                self.put(ci, x, y, index)

    def _glyph_pixels(self, font, lines, box, scale):
        """Yield (x, y) for every lit pixel of centred, stacked lines."""
        x0, y0, x1, y1 = box
        line_h = font.cell_h * scale
        total_h = line_h * len(lines)
        top = y0 + (y1 - y0 - total_h) // 2
        for li, line in enumerate(lines):
            width = self.text_width(font, line, scale)
            if width > x1 - x0:
                return None
            pen = x0 + (x1 - x0 - width) // 2
            base = top + li * line_h
            for ch in line:
                gi = font.cmap.get(ord(ch))
                if gi is None:
                    pen += font.advance(ord(" ")) * scale
                    continue
                bits = font.bitmap(gi)
                for row in range(font.cell_h):
                    for col in range(font.cell_w):
                        if bits[row][col]:
                            for sy in range(scale):
                                for sx in range(scale):
                                    yield (pen + col * scale + sx, base + row * scale + sy)
                pen += font.advance(ord(ch)) * scale

    def draw_outlined(self, ci, font, lines, box, ink, outline, scale=2):
        """Draw stacked lines with a 1px (x scale) outline, as the styled
        free-standing menu words do. Returns False if any line is too wide."""
        for line in lines:
            if self.text_width(font, line, scale) > box[2] - box[0]:
                return False
        pixels = list(self._glyph_pixels(font, lines, box, scale))
        if not pixels:
            return False
        solid = set(pixels)
        for (x, y) in pixels:                       # outline first, underneath
            for dy in range(-scale, scale + 1):
                for dx in range(-scale, scale + 1):
                    if (x + dx, y + dy) not in solid:
                        self.put(ci, x + dx, y + dy, outline)
        for (x, y) in pixels:
            self.put(ci, x, y, ink)
        return True

    # ---- output ----------------------------------------------------------
    def preview(self, ci, path):
        pal = list(self.palette)
        while len(pal) < 256:
            pal.append((255, 0, 255, 255))
        w, h, rows = render_cell(self.flat, self.w, pal, self.cells[ci])
        write_png(path, w, h, rows)

    def save(self, out_ncgr):
        write_ncgr_like(self.base + ".NCGR", out_ncgr, self.flat, self.w, self.h)


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 1
    bank = Bank(os.path.join(TITLE_DIR, argv[2]))
    if argv[1] == "list":
        for i in range(len(bank.cells)):
            if not bank.cells[i]:
                continue
            w, h = bank.size(i)
            print("  cell %d: %dx%d  %d OAM" % (i, w, h, len(bank.cells[i])))
    elif argv[1] == "preview":
        ci, text = int(argv[3]), argv[4]
        font = Nftr(FONT)
        w, h = bank.size(ci)
        box = (22, 12, w - 32, 36)
        bank.fill(ci, box, 13)
        if not bank.draw_text(ci, font, text, box, 5, scale=2):
            bank.draw_text(ci, font, text, box, 5, scale=1)
        bank.preview(ci, "/tmp/preview_cell%d.png" % ci)
        print("wrote /tmp/preview_cell%d.png" % ci)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
