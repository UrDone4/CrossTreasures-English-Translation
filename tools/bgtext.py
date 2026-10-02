#!/usr/bin/env python3
"""Paint English labels into NCCG/NCSC background layers.

Unlike a sprite bank, a background layer addresses its tiles through a screen
map, and several cells may point at the same tile. Painting such a tile would
change every cell that references it, so every write is guarded: `check_box`
reports whether the tiles under a region are private to it, and `put` refuses to
touch a shared tile unless explicitly allowed.

Coordinates are screen pixels (the layer is w*8 by h*8).
"""

import collections
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from nbg import (read_nccg, read_nccl, read_ncsc, write_nccg,  # noqa: E402
                 write_ncsc, grow_nccg, tile_pixels, set_tile_pixels, TILE)
from nftr import Nftr  # noqa: E402


# How far the lettering erase looks for a clean pixel to fill from, and so how
# far past a label's box the Japanese must be detected: anything in reach that
# is not known to be lettering counts as backdrop and gets copied in.
FILL_REACH = 24


class BgLayer:
    def __init__(self, nccg, nccl, ncsc, also=()):
        self.nccg_path = nccg
        self.ncsc_path = ncsc
        tiles, self.tw, self.th, self.bpp = read_nccg(nccg)
        self.tiles = bytearray(tiles)
        self.palette = read_nccl(nccl)
        self.cells, self.sw, self.sh = read_ncsc(ncsc)
        self.width, self.height = self.sw * TILE, self.sh * TILE
        self.n_tiles = self.tw * self.th
        self.extra_rows = 0
        self.snap = False
        self.users = collections.Counter(c["tile"] for c in self.cells)
        self.tile_users = collections.defaultdict(set)
        for i, c in enumerate(self.cells):
            self.tile_users[c["tile"]].add(i)
        # Other screens that share this tile set (two NCSCs over one NCCG). Their
        # cells are recorded as negative "users": a tile they use counts as
        # shared, so it is copied before being painted and is never freed or
        # merged away underneath them.
        self.others = []
        for k, path in enumerate(also):
            other, _w, _h = read_ncsc(path)
            self.others.append({"path": path, "cells": other})
            for i, c in enumerate(other):
                self.tile_users[c["tile"]].add(-(k * 100000 + i) - 1)
        # Tiles past the last one any screen refers to in the original. They are
        # in the file but not safe to spend: on the Medals screen tiles 346-351
        # showed as a transparent square on hardware -- the game evidently
        # loads something else over them. Unused tiles in gaps *below* the last
        # used one are fine (everything up to it is loaded). Whether the
        # trailing ones are safe depends on the screen (battle layers use them
        # fine on hardware), so bg_labels decides per archive (TRAILING_UNSAFE).
        last = max((t for t in range(self.n_tiles) if self.tile_users[t]), default=-1)
        self.never_used = set(range(last + 1, self.n_tiles))
        self.use_never_used = False
        # first tile index no cell refers to -- where fresh copies are placed
        self.next_free = max(
            (t for t in range(self.n_tiles) if not self.tile_users[t]),
            default=self.n_tiles)
        self.blocked = 0
        self.starved = 0
        self.free_pool = []

    # ---- addressing ------------------------------------------------------
    def cell_at(self, x, y):
        return self.cells[(y // TILE) * self.sw + (x // TILE)]

    def _in_tile(self, cell, x, y):
        col, row = x % TILE, y % TILE
        if cell["flip_h"]:
            col = TILE - 1 - col
        if cell["flip_v"]:
            row = TILE - 1 - row
        return row * TILE + col

    def get(self, x, y):
        if not (0 <= x < self.width and 0 <= y < self.height):
            return 0
        cell = self.cell_at(x, y)
        return tile_pixels(self.tiles, cell["tile"], self.bpp)[
            self._in_tile(cell, x, y)]

    def put(self, x, y, index, allow_shared=False):
        if not (0 <= x < self.width and 0 <= y < self.height):
            return
        cell = self.cell_at(x, y)
        if self.users[cell["tile"]] > 1 and not allow_shared:
            self.blocked += 1
            return
        px = tile_pixels(self.tiles, cell["tile"], self.bpp)
        px[self._in_tile(cell, x, y)] = index
        set_tile_pixels(self.tiles, cell["tile"], self.bpp, px)

    # ---- private tiles ---------------------------------------------------
    def cells_in(self, box):
        """Indices of the cells a screen-pixel box touches."""
        x0, y0, x1, y1 = box
        out = set()
        for y in range(y0, y1):
            for x in range(x0, x1):
                out.add((y // TILE) * self.sw + (x // TILE))
        return out

    def reserve(self, extra):
        """Add room for `extra` more tiles, as whole tile rows.

        NOTE: only safe if the game uploads the whole graphic to VRAM. Cross
        Treasures does not -- it uploads the original tile count, so cells
        pointing past it display whatever else occupies that VRAM (observed
        in-game as coloured blocks and other layers' animation bleeding
        through). Prefer free_by_dedupe() and stay within the original budget.
        """
        rows = -(-extra // self.tw)
        added = rows * self.tw
        per = 32 if self.bpp == 4 else 64
        self.tiles += bytearray(added * per)
        self.n_tiles += added
        self.extra_rows += rows

    def free_by_dedupe(self, protect=frozenset(), tol=0, shared=False,
                       keep_other=frozenset(), perceptual=True):
        """Point cells with byte-identical tiles at one copy; free the rest.

        Clearing a Japanese label turns each of its glyph tiles into the same
        flat background, so deduplicating afterwards hands back a pool of tiles
        that can be spent giving shared cells a private copy -- all without
        growing the graphic (which this game cannot tolerate: it uploads only
        the original tile count to VRAM).

        `protect` lists cells that must keep a tile of their own -- the cells the
        English text is about to be drawn into. Collapsing those would defeat
        the purpose, since a shared tile cannot receive text.
        """
        # A tile also duplicates another if it is that tile mirrored -- borders,
        # bevels and gradients are full of these -- so match all four
        # orientations and let the cell's flip bits carry the difference.
        seen = {}
        freed = []
        for t in range(self.n_tiles):
            if not self.tile_users[t] or (self.tile_users[t] & protect):
                continue
            px = tile_pixels(self.tiles, t, self.bpp)
            hit = seen.get(tuple(px))
            if hit is None:
                rows = [px[r * 8:(r + 1) * 8] for r in range(8)]
                for fh in (0, 1):
                    for fv in (0, 1):
                        rr = rows[::-1] if fv else rows
                        img = tuple(v for row in rr
                                    for v in (row[::-1] if fh else row))
                        seen.setdefault(img, (t, fh, fv))
                continue
            keep, fh, fv = hit
            for ci in list(self.tile_users[t]):
                c = self._cell_of(ci)
                c["tile"] = keep
                c["flip_h"] = bool(c["flip_h"]) ^ bool(fh)
                c["flip_v"] = bool(c["flip_v"]) ^ bool(fv)
                self.tile_users[keep].add(ci)
                self.users[keep] += 1
            self.tile_users[t] = set()
            self.users[t] = 0
            freed.append(t)
        if tol:
            # Last resort: merge tiles that differ by at most `tol` pixels. On
            # the 96-192 tile layers the map art leaves nothing else to spend.
            # Only this screen's own cells are redirected unless `shared`:
            # moving another screen's cell (`also`) onto a near-copy damaged
            # that screen -- a pixel column of a letter lost, a separator
            # turned to dots -- so that is kept for when nothing else is left.
            live = [t for t in range(self.n_tiles)
                    if self.tile_users[t] and not (self.tile_users[t] & protect)]
            pix = {t: tile_pixels(self.tiles, t, self.bpp) for t in live}
            for i, a in enumerate(live):
                if not self.tile_users[a]:
                    continue
                for b in live[i + 1:]:
                    if not self.tile_users[b] or (not shared and min(self.tile_users[b]) < 0):
                        continue
                    # `keep_other`: cell positions whose tiles on another screen
                    # hold that screen's own painted text (a near-copy merge
                    # there broke "Bronze Medal"'s e and d)
                    if any(u < 0 and (-u - 1) % 100000 in keep_other
                           for u in self.tile_users[b]):
                        continue
                    if (self._near_copy(a, b, pix, tol) if perceptual else
                            sum(x != y for x, y in zip(pix[a], pix[b])) <= tol):
                        for ci in list(self.tile_users[b]):
                            self._cell_of(ci)["tile"] = a
                            self.tile_users[a].add(ci)
                            self.users[a] += 1
                        self.tile_users[b] = set()
                        self.users[b] = 0
                        freed.append(b)
        for t in range(self.n_tiles):
            if not self.tile_users[t] and t not in freed:
                if t in self.never_used and not self.use_never_used:
                    continue
                freed.append(t)
        self.free_pool = sorted(set(freed))
        return self.free_pool

    # a near-copy merge may only swap a pixel for a similar colour: swapping an
    # orange letter pixel for white, or a dark grey edge for green, showed up
    # as a broken letter or a gap in a line
    NEAR_RGB = 60

    def _tile_bank(self, t):
        for u in self.tile_users[t]:
            return self._cell_of(u)["palette"] * 16
        return 0

    def _near_copy(self, a, b, pix, tol):
        diff = [(x, y) for x, y in zip(pix[a], pix[b]) if x != y]
        if len(diff) > tol:
            return False
        ba, bb = self._tile_bank(a), self._tile_bank(b)
        pal = self.palette
        for x, y in diff:
            if x == 0 or y == 0:
                return False              # transparency against a colour
            if ba + x >= len(pal) or bb + y >= len(pal):
                return False
            ca, cb = pal[ba + x][:3], pal[bb + y][:3]
            if sum((p - q) ** 2 for p, q in zip(ca, cb)) > self.NEAR_RGB ** 2:
                return False
        return True

    def text_cells(self, font, text, box, scale, align="center"):
        """Cells the glyphs of `text` would touch if drawn in `box`."""
        x0, y0, x1, y1 = box
        width = self.text_width(font, text, scale)
        pen = (x1 - width if align == "right" else self._pen(width, x0, x1)) \
            if x1 - x0 >= width else x0
        top = y0 + (y1 - y0 - font.cell_h * scale) // 2
        out = set()
        px0, px1 = pen, pen + width
        py0, py1 = top, top + font.cell_h * scale
        for y in range(max(0, py0), min(self.height, py1)):
            for x in range(max(0, px0), min(self.width, px1)):
                out.add((y // TILE) * self.sw + (x // TILE))
        return out

    def privatise_cells(self, cells):
        """Give each listed cell its own tile, spending the free pool."""
        per = 32 if self.bpp == 4 else 64
        done = 0
        for ci in sorted(cells):
            if self.exclusive(ci):
                continue
            if not self.free_pool:
                self.starved += 1
                continue
            new = self.free_pool.pop(0)
            old = self.cells[ci]["tile"]
            self.tiles[new * per:(new + 1) * per] = \
                self.tiles[old * per:(old + 1) * per]
            self.cells[ci]["tile"] = new
            self.tile_users[old].discard(ci)
            self.users[old] -= 1
            self.tile_users[new] = {ci}
            self.users[new] = 1
            done += 1
        return done

    def rgb_at(self, x, y):
        """Colour of a pixel, or None where it is transparent (index 0)."""
        idx = self.get(x, y)
        if not idx:
            return None
        i = self.cell_at(x, y)["palette"] * 16 + idx
        return tuple(self.palette[i][:3]) if i < len(self.palette) else None

    def inpaint_targets(self, box, keep, reach=10, axis="row", spare_icons=True,
                        only_ink=False):
        """Per-pixel fill for a label sitting on a mixed background.

        Pixels already transparent or equal to `keep` (a colour, or several -- a strip can be two-tone) are backdrop and stay.
        Every other pixel (the lettering and its antialiasing) takes the nearest
        backdrop pixel along its own row -- so lettering that straddles the edge
        of the strip is erased into cream on one side and transparency on the
        other, instead of a single flat fill lighting up a block.

        `axis` picks the scan direction: "col" for horizontal lettering over an
        illustration (the strokes are thin, so a row above or below is backdrop).

        `only_ink` narrows "lettering" to the brown hint ink and the pixels
        touching it. Several hint strips carry faint diagonal stripes whose
        colours are too rare to make the `keep` list; without this they count
        as lettering and get patched over, leaving dashes beside the word.
        """
        x0, y0, x1, y1 = box
        keeps = {keep} if isinstance(keep[0], int) else set(keep)
        keep = next(iter(keep)) if isinstance(keep[0], int) else keep[0]

        def is_icon(c):
            # button icons are green or orange with white lettering; the hint
            # lettering and its shadow are brown. The box reaches a few pixels
            # past the lettering to catch its antialiasing, and must not eat
            # the icon.
            if c is None or c in keeps:
                return False
            lum = 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]
            # (a green button is muted, g/r ~2; with only_ink, a vivid green --
            # the dark stripes on the Options strip, g/r 3 -- is backdrop)
            return ((c[1] - c[0] >= 45 and lum < 160
                     and (not only_ink or c[1] <= 2.4 * c[0]))
                    # an icon's white letter; with only_ink, near-white cream
                    # antialiasing on a white pill ((247,247,222)) is not one
                    or (min(c) >= 235 if only_ink else c[2] > 220)
                    # orange badge and its shading: g/r <= ~.72, b <= ~57. The
                    # gold fringe of hint lettering is g/r ~.75 up, or bluer
                    # ((255,165,66) beside the Japanese on transparency)
                    or (c[0] >= 190 and 60 <= c[1] <= 0.72 * c[0] and c[2] <= 60))

        def near_icon(x, y, r=1):
            # r=2 for lettering seeds: an icon's drop shadow is brown and gold
            # like the lettering, and reaches 2px out (the Japanese always sits
            # 3px or more from its icon)
            return any(0 <= x + dx < self.width and 0 <= y + dy < self.height
                       and is_icon(self.rgb_at(x + dx, y + dy))
                       for dx in range(-r, r + 1) for dy in range(-r, r + 1))

        lettering = None
        if only_ink:
            def is_ink(c):
                # the brown lettering and its mid-brown shading, plus the gold
                # fringe it carries where it was drawn for a light layer below a
                # transparent hole; light colours (strip, stripes, cream --
                # cream is far less saturated than the fringe) and the icons are
                # not lettering
                if c is None or c in keeps or is_icon(c) or not c[0] >= c[1] >= c[2]:
                    return False
                # (the greyer antialiasing, e.g. (148,115,90) and (189,165,115)
                # under the Japanese on the cream strip, is r-b ~50-75; cream
                # and the pale inner band are lum > 185)
                return ((0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2] <= 175
                         and c[0] - c[2] >= 50) or c[0] - c[2] >= 100)
            # look past the box too: a fill taken from the nearest non-lettering
            # pixel must not pick up Japanese lying just outside it (a
            # left-aligned word's text box is narrower than the Japanese)
            # (as far as the fill search itself reaches -- see _fill_between)
            ink = {(x, y) for y in range(y0 - 1, y1 + 1)
                   for x in range(x0 - FILL_REACH, x1 + FILL_REACH)
                   if 0 <= x < self.width and 0 <= y < self.height
                   and is_ink(self.rgb_at(x, y)) and not near_icon(x, y, 2)}
            if ink:
                lettering = {(x + dx, y + dy) for x, y in ink
                             for dx in (-1, 0, 1) for dy in (-1, 0, 1)}
                # over a transparent hole the lettering's fringe (blended for
                # the light layer beneath) runs 2px out; take that second ring
                # only where it touches transparency, so opaque strips and
                # their stripes are left alone
                def by_hole(x, y):
                    return any(0 <= x + dx < self.width and 0 <= y + dy < self.height
                               and self.rgb_at(x + dx, y + dy) is None
                               for dx in (-1, 0, 1) for dy in (-1, 0, 1))
                ring = {(x + dx, y + dy) for x, y in lettering
                        for dx in (-1, 0, 1) for dy in (-1, 0, 1)} - lettering
                lettering |= {(x, y) for x, y in ring
                              if 0 <= x < self.width and 0 <= y < self.height
                              and self.rgb_at(x, y) is not None
                              and self.rgb_at(x, y) not in keeps
                              and not is_icon(self.rgb_at(x, y))
                              and not near_icon(x, y) and by_hole(x, y)}

        def is_bg(x, y):
            if not (0 <= x < self.width):
                return False
            c = self.rgb_at(x, y)
            if lettering is not None:
                return c is None or ((x, y) not in lettering and not is_icon(c))
            return c is None or c in keeps

        def is_bg_at(x, y):
            return 0 <= y < self.height and is_bg(x, y)

        out = {}
        for y in range(y0, y1):
            for x in range(x0, x1):
                if lettering is not None and (x, y) not in lettering:
                    out[(x, y)] = self.rgb_at(x, y)
                    continue
                if is_bg(x, y) or (spare_icons and is_icon(self.rgb_at(x, y))):
                    out[(x, y)] = self.rgb_at(x, y)
                    continue
                out[(x, y)] = keep
                # with only_ink, "backdrop" is anything that is not lettering --
                # which includes an icon's pale rim; take the fill from a pixel
                # clear of any icon first, so the rim is not smeared into the gap
                # (a strip colour itself is safe to copy even beside an icon)
                tests = ((lambda xx, yy: is_bg(xx, yy)
                          and (self.rgb_at(xx, yy) in keeps or not near_icon(xx, yy))),
                         is_bg) if lettering is not None else (is_bg,)
                if lettering is not None and axis == "row":
                    got = None
                    for test in tests:
                        # dense lettering can leave no clean pixel within
                        # `reach` on the row; the fallback `keep` colour then
                        # showed (a lime line through "Move" on a green strip)
                        got = self._fill_between(x, y, test, max(reach, FILL_REACH))
                        if got is not None:
                            out[(x, y)] = got[0]
                            break
                    continue
                for test in tests:
                    hit = None
                    for d in range(1, reach + 1):
                        if axis == "row":
                            hit = [(xx, y) for xx in (x - d, x + d)
                                   if 0 <= xx < self.width and test(xx, y)]
                        else:
                            hit = [(x, yy) for yy in (y - d, y + d)
                                   if 0 <= yy < self.height and test(x, yy)]
                        if hit:
                            out[(x, y)] = self.rgb_at(*hit[0])
                            break
                    if hit:
                        break
        return out

    def _fill_between(self, x, y, test, reach):
        """(colour,) for an erased lettering pixel, or None if nothing in reach.

        Looks both ways along the row, the column and the two diagonals, and
        takes the closest pair whose two ends agree: a pixel inside a stripe or
        on one side of a curve has the same backdrop on both sides along the
        stripe or curve, but not across it. Taking the nearest row pixel instead
        moved curves (biting into the strip beside the word) and broke diagonal
        stripes where a word crossed them.
        """
        def nearest(dx, dy):
            for d in range(1, reach + 1):
                xx, yy = x + dx * d, y + dy * d
                if not (0 <= xx < self.width and 0 <= yy < self.height):
                    return None
                if test(xx, yy):
                    return d, self.rgb_at(xx, yy)
            return None
        best = None
        hits = []
        for (ax, ay) in ((1, 0), (0, 1), (1, 1), (1, -1)):
            a, b = nearest(-ax, -ay), nearest(ax, ay)
            hits += [v for v in (a, b) if v]
            if a and b and a[1] == b[1] and (best is None or a[0] + b[0] < best[0]):
                best = (a[0] + b[0], a[1])
        if best:
            return (best[1],)
        pick = min(hits, key=lambda t: t[0], default=None)
        return (pick[1],) if pick else None

    def dirty_cells(self, box, rgb):
        """Cells in `box` holding any pixel that is not already the fill colour.

        These are the cells carrying the Japanese lettering. Pure background
        cells inside the box need no work, so excluding them keeps the number
        of tiles that must be privatised down to what the free pool can cover.
        """
        x0, y0, x1, y1 = box
        out = set()
        for y in range(y0, y1):
            for x in range(x0, x1):
                ci = (y // TILE) * self.sw + (x // TILE)
                if ci in out:
                    continue
                want = rgb[(x, y)] if isinstance(rgb, dict) else rgb
                if isinstance(rgb, dict) and want == self.rgb_at(x, y):
                    continue
                if want is None:
                    want_idx = 0          # transparent: raw index 0, no palette lookup
                else:
                    want_idx = self.nearest(self.cell_at(x, y)["palette"], want)
                if self.get(x, y) != want_idx:
                    out.add(ci)
        return out

    def _cell_of(self, u):
        """The cell dict for a user id: >= 0 is this screen, < 0 another screen."""
        if u >= 0:
            return self.cells[u]
        k, i = divmod(-u - 1, 100000)
        return self.others[k]["cells"][i]

    def save_others(self, out_paths):
        """Write the other screens' maps (their tiles may have been merged)."""
        for o, out in zip(self.others, out_paths):
            write_ncsc(o["path"], out, o["cells"])

    def exclusive(self, ci):
        """True if cell `ci`'s tile can be painted in place.

        A tile is safe when no other cell uses it -- except the *same cell* on
        another screen sharing this tile set (`also`), which shows the same
        label at the same position and is meant to change with it.
        """
        forced = ci in getattr(self, "force_private", ())
        for u in self.tile_users[self.cells[ci]["tile"]]:
            if u == ci:
                continue
            if u < 0 and not forced and (-u - 1) % 100000 == ci:
                continue
            return False
        return True

    def paintable(self, box):
        """Cells in `box` whose tile is theirs alone (safe to paint as-is)."""
        return {ci for ci in self.cells_in(box)
                if self.exclusive(ci)}

    def clear_private(self, box, rgb):
        """Clear only the cells in `box` that already own their tile.

        `rgb` (or a per-pixel dict value) may be `None` for genuine transparency
        (raw palette index 0) instead of an opaque colour -- for text that sits
        directly on a lower layer showing through, not a filled pill/panel.
        """
        ok = self.paintable(box)
        x0, y0, x1, y1 = box
        for y in range(y0, y1):
            for x in range(x0, x1):
                if (y // TILE) * self.sw + (x // TILE) in ok:
                    want = rgb[(x, y)] if isinstance(rgb, dict) else rgb
                    if want is None:
                        self.put(x, y, 0)
                    else:
                        self.put_rgb(x, y, want)

    def make_private(self, box):
        """Give every cell in `box` a tile of its own, spending the free pool.

        Any cell whose tile has more than one user needs its own copy --
        including two cells *inside* the same box sharing a tile, since text
        painted into one would otherwise appear in the other.
        """
        inside = self.cells_in(box)
        per = 32 if self.bpp == 4 else 64
        needed = [ci for ci in sorted(inside)
                  if not self.exclusive(ci)]
        if not needed:
            return 0
        done = 0
        for ci in needed:
            if not self.free_pool:
                self.starved += 1
                continue
            new = self.free_pool.pop(0)
            old = self.cells[ci]["tile"]
            self.tiles[new * per:(new + 1) * per] = \
                self.tiles[old * per:(old + 1) * per]
            self.cells[ci]["tile"] = new
            self.tile_users[old].discard(ci)
            self.users[old] -= 1
            self.tile_users[new] = {ci}
            self.users[new] = 1
            done += 1
        return done


    # ---- safety ----------------------------------------------------------
    def check_box(self, box):
        """(tiles_in_box, shared_tiles) for a screen-pixel box."""
        x0, y0, x1, y1 = box
        involved = set()
        for y in range(y0, y1, 1):
            for x in range(x0, x1, 1):
                involved.add(self.cell_at(x, y)["tile"])
        shared = {t for t in involved if self.users[t] > 1}
        return involved, shared

    # ---- painting --------------------------------------------------------
    def fill(self, box, index, allow_shared=False):
        x0, y0, x1, y1 = box
        for y in range(y0, y1):
            for x in range(x0, x1):
                self.put(x, y, index, allow_shared)

    def palette_of(self, box):
        """The palette bank the cells under a box use (for colour matching)."""
        x0, y0, x1, y1 = box
        banks = collections.Counter(
            self.cell_at(x, y)["palette"]
            for y in range(y0, y1) for x in range(x0, x1))
        return banks.most_common(1)[0][0]

    def _pen(self, width, x0, x1):
        """Left edge of centred text. With `snap`, start at the box's left
        margin and slide within +-4px to cover the fewest tile columns -- each column spent is a tile taken from
        a pool that is tiny on the 96-tile layers."""
        mid = x0 + (x1 - x0 - width) // 2
        if not self.snap:
            return mid
        # a hint reads icon-then-word, so start where the Japanese started
        # (the label box reaches 4px left of it) plus a 3px gap, rather than floating mid-gap
        mid = min(mid, x0 + 7)
        best = min(range(max(x0, mid - 2), min(max(x0, x1 - width), mid + 2) + 1),
                   key=lambda p: ((p + width - 1) // TILE - p // TILE,
                                  abs(p - mid)))
        return best

    def text_width(self, font, text, scale):
        # "\b" in a label pulls the pen back one pixel (hand kerning)
        return sum(-1 if c == "\b" else font.advance(ord(c)) for c in text) * scale

    def draw_text(self, font, text, box, ink, scale=1, align="center",
                  allow_shared=False):
        """Draw one line inside a screen-pixel box. False if it will not fit."""
        x0, y0, x1, y1 = box
        width = self.text_width(font, text, scale)
        if width > x1 - x0:
            return False
        if align == "left":
            pen = x0
        else:
            pen = x0 + (x1 - x0 - width) // 2
        top = y0 + (y1 - y0 - font.cell_h * scale) // 2
        for ch in text:
            if ch == "\b":
                pen -= scale
                continue
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
                            self.put(pen + col * scale + sx,
                                     top + row * scale + sy, ink, allow_shared)
            pen += font.advance(ord(ch)) * scale
        return True

    # ---- colour resolution ----------------------------------------------
    def nearest(self, bank, rgb):
        """Index within `bank` whose colour is closest to rgb (skipping 0).
        rgb=None means transparent: index 0."""
        if rgb is None:
            return 0
        best, best_d = 1, 1 << 30
        for i in range(1, 16):
            c = self.palette[bank * 16 + i] if bank * 16 + i < len(self.palette) \
                else (255, 0, 255, 255)
            d = (c[0] - rgb[0]) ** 2 + (c[1] - rgb[1]) ** 2 + (c[2] - rgb[2]) ** 2
            if d < best_d:
                best, best_d = i, d
        return best

    def put_rgb(self, x, y, rgb):
        """Write a colour, resolved against the palette bank of that cell.

        Cells in one region may use different palette banks, so a fixed index
        renders as different colours across the region -- the fix is to pick the
        index per cell.
        """
        if not (0 <= x < self.width and 0 <= y < self.height):
            return
        bank = self.cell_at(x, y)["palette"]
        self.put(x, y, self.nearest(bank, rgb))

    def fill_rgb(self, box, rgb):
        x0, y0, x1, y1 = box
        for y in range(y0, y1):
            for x in range(x0, x1):
                self.put_rgb(x, y, rgb)

    def draw_text_rgb(self, font, text, box, rgb, scale=1, align="center"):
        """Draw one line, resolving the ink colour per cell. False if too wide."""
        x0, y0, x1, y1 = box
        width = self.text_width(font, text, scale)
        if width > x1 - x0:
            return False
        pen = (x0 if align == "left" else x1 - width if align == "right"
               else self._pen(width, x0, x1))
        top = y0 + (y1 - y0 - font.cell_h * scale) // 2
        for ch in text:
            if ch == "\b":
                pen -= scale
                continue
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
                            self.put_rgb(pen + col * scale + sx,
                                         top + row * scale + sy, rgb)
            pen += font.advance(ord(ch)) * scale
        return True

    # ---- output ----------------------------------------------------------
    def render(self, out_png):
        from ngfx import write_png
        rows = [bytearray(self.width * 4) for _ in range(self.height)]
        for i, cell in enumerate(self.cells):
            cx, cy = (i % self.sw) * TILE, (i // self.sw) * TILE
            px = tile_pixels(self.tiles, cell["tile"], self.bpp)
            bank = cell["palette"] * 16
            for row in range(TILE):
                for col in range(TILE):
                    sr = TILE - 1 - row if cell["flip_v"] else row
                    sc = TILE - 1 - col if cell["flip_h"] else col
                    idx = px[sr * TILE + sc]
                    if idx == 0:
                        continue
                    colour = self.palette[bank + idx] \
                        if bank + idx < len(self.palette) else (255, 0, 255, 255)
                    o = (cx + col) * 4
                    rows[cy + row][o:o + 4] = bytes(colour)
        write_png(out_png, self.width, self.height, rows)

    def save(self, out_nccg, out_ncsc=None):
        """Write the graphic (grown if tiles were added) and the screen map."""
        src = open(self.nccg_path, "rb").read()
        if self.extra_rows:
            src = grow_nccg(src, self.extra_rows * self.tw)
            tmp = out_nccg + ".grown"
            with open(tmp, "wb") as fh:
                fh.write(src)
            write_nccg(tmp, out_nccg, bytes(self.tiles))
            os.remove(tmp)
        else:
            write_nccg(self.nccg_path, out_nccg, bytes(self.tiles))
        if out_ncsc:
            write_ncsc(self.ncsc_path, out_ncsc, self.cells)


def load_font():
    return Nftr(os.path.join(os.path.dirname(HERE), "extracted", "LCFont.NFTR"))
