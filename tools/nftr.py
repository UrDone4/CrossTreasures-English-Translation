#!/usr/bin/env python3
"""NFTR (Nintendo font) reader: glyph metrics, rendering, and text measurement.

Cross Treasures uses LCFont.NFTR -- 11x11 1bpp proportional glyphs with a
character map that already covers ASCII U+0020..U+007E, so Latin text renders
natively. This module exposes the per-glyph advance widths needed to re-wrap
translated lines to the game's textbox.
"""

import re
import struct

# Control tags used by the Cross Treasures script engine:
#   <c2< ... </c<      colour span open / close
#   <pn>, <item_0>     runtime substitution (player name, item name)
#   #insitem#          inline runtime substitution token
#   #c ... #z          legacy colour span (rare, older files)
#
# The shipped script also contains developer typos that the engine evidently
# tolerates, so they are matched here and must be preserved verbatim when
# translating:
#   >pn>               mis-typed <pn>
#   >host>              a second player-name substitution, same mis-typed
#                       bracket as >pn> but its own token -- found only in the
#                       ev70000-ev75002 (Demon King/Sasha) family, nowhere
#                       else in the script corpus. Originally missing from
#                       this regex entirely, which meant scripttext.py's
#                       tag-mismatch checker was silently blind to it (an
#                       English line could drop or duplicate >host> and the
#                       checker would not notice); a manual per-block count
#                       audit after the fact found zero actual mismatches in
#                       the translated batches, but the gap itself is fixed
#                       here so future work is checked automatically.
#   </c                mis-typed </c< (missing the final '<')
TAG_RE = re.compile(
    rb"</?c\d?<"                      # <c2<  <c<  </c<
    rb"|</c(?!<)"                     # </c   -- typo, no trailing '<'
    rb"|(?P<var>#ins[a-z]+#|<pn>|>pn>|>host>|<item_\d+>)"
    rb"|#[cz]",
)

# <pn>/<item_N> expand at runtime to names of unknown length. Charge a nominal
# width when wrapping so lines do not overflow on long substitutions.
VAR_ESTIMATE_PX = 48


class Nftr:
    def __init__(self, path):
        self.d = d = open(path, "rb").read()
        assert d[:4] == b"RTFN", "not an NFTR file"
        self.blocks = {}
        p = 16
        while p < len(d) - 8:
            tag = d[p:p + 4]
            size = struct.unpack_from("<I", d, p + 4)[0]
            if size == 0:
                break
            self.blocks.setdefault(tag, []).append((p, size))
            p += size

        gp, gsz = self.blocks[b"PLGC"][0]
        self.cell_w = d[gp + 8]
        self.cell_h = d[gp + 9]
        self.cell_size = struct.unpack_from("<H", d, gp + 10)[0]
        self.glyph_base = gp + 16
        self.glyph_count = (gsz - 16) // self.cell_size

        hp, _ = self.blocks[b"HDWC"][0]
        self.hdwc_first, self.hdwc_last = struct.unpack_from("<HH", d, hp + 8)
        self.hdwc_base = hp + 16

        self.line_feed = d[self.blocks[b"FNIF"][0][0] + 9]
        self.cmap = self._read_cmaps()

    # ---- character map ---------------------------------------------------
    def _read_cmaps(self):
        """Return {codepoint: glyph_index}. Codepoints are Shift-JIS values
        (single byte for ASCII/half-width, two bytes packed big-endian)."""
        d = self.d
        cmap = {}
        for p, size in self.blocks.get(b"PAMC", []):
            first, last, kind = struct.unpack_from("<HHI", d, p + 8)
            kind &= 0xFFFF
            # header is firstChar(2) lastChar(2) mapType(4) nextOffset(4)
            body = p + 20
            if kind == 0:                      # contiguous run
                start = struct.unpack_from("<H", d, body)[0]
                for i, code in enumerate(range(first, last + 1)):
                    cmap[code] = start + i
            elif kind == 1:                    # per-code index table
                for i, code in enumerate(range(first, last + 1)):
                    gi = struct.unpack_from("<H", d, body + i * 2)[0]
                    if gi != 0xFFFF:
                        cmap[code] = gi
            elif kind == 2:                    # sparse pairs
                n = struct.unpack_from("<H", d, body)[0]
                for i in range(n):
                    code, gi = struct.unpack_from("<HH", d, body + 2 + i * 4)
                    cmap[code] = gi
        return cmap

    # ---- metrics ---------------------------------------------------------
    def metrics(self, glyph_index):
        """(left_bearing, glyph_width, advance) for a glyph index."""
        if not (self.hdwc_first <= glyph_index <= self.hdwc_last):
            return (0, 0, 0)
        o = self.hdwc_base + (glyph_index - self.hdwc_first) * 3
        return self.d[o], self.d[o + 1], self.d[o + 2]

    def advance(self, code):
        gi = self.cmap.get(code)
        if gi is None:
            return 0
        return self.metrics(gi)[2]

    def measure(self, sjis_bytes, var_px=VAR_ESTIMATE_PX):
        """Pixel width of a Shift-JIS line.

        Control tags render as nothing and are skipped; runtime substitutions
        (<pn>, <item_N>, #insitem#) have no fixed width, so each is charged
        var_px as a wrapping estimate.
        """
        text = bytes(sjis_bytes)
        total, i, n = 0, 0, len(text)
        while i < n:
            m = TAG_RE.match(text, i)
            if m:
                if m.group("var") is not None:
                    total += var_px
                i = m.end()
                continue
            b = text[i]
            if (0x81 <= b <= 0x9F or 0xE0 <= b <= 0xEF) and i + 1 < n:
                total += self.advance((b << 8) | text[i + 1])
                i += 2
            else:
                total += self.advance(b)
                i += 1
        return total

    def strip_tags(self, sjis_bytes):
        """Remove control tags, leaving only rendered characters."""
        return TAG_RE.sub(b"", bytes(sjis_bytes))

    # ---- rendering -------------------------------------------------------
    def bitmap(self, glyph_index):
        """Return cell_h rows of cell_w booleans for a 1bpp glyph."""
        off = self.glyph_base + glyph_index * self.cell_size
        cell = self.d[off:off + self.cell_size]
        bits = []
        for byte in cell:
            for k in range(7, -1, -1):
                bits.append((byte >> k) & 1)
        return [
            [bool(bits[y * self.cell_w + x]) for x in range(self.cell_w)]
            for y in range(self.cell_h)
        ]

    def ascii_art(self, ch):
        code = ch.encode("shift_jis")
        code = code[0] if len(code) == 1 else (code[0] << 8) | code[1]
        gi = self.cmap.get(code)
        if gi is None:
            return ["<unmapped>"]
        return ["".join("#" if px else "." for px in row) for row in self.bitmap(gi)]


if __name__ == "__main__":
    import sys
    f = Nftr(sys.argv[1] if len(sys.argv) > 1 else "extracted/LCFont.NFTR")
    print("glyphs=%d cell=%dx%d lineFeed=%d mapped=%d"
          % (f.glyph_count, f.cell_w, f.cell_h, f.line_feed, len(f.cmap)))
