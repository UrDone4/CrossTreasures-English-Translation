#!/usr/bin/env python3
"""Screen-header words (Battle / Island / Menu) in the original's circled style.

The Japanese headers set each kana in its own white circle: a white disc, a
1px ring in the banner colour, a pale outer border, and a soft shadow
underneath. Neighbouring circles overlap like a cloud, and their rings cross
inside the overlap. The English is drawn the same way, one uppercase letter per
circle, from a small hand-drawn bold capital set (the game font looked weak
inside the rings). Designed with the user in rounds; the prototype and preview
are in work/banner_circles/.

`design()` returns the target colours for the header region.
`paint(layer, ...)` writes them into a background layer by building each cell's
tile from the target image: an identical (or mirrored) tile already in the
layer is reused, otherwise a free tile is spent. The layer never grows.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from nbg import tile_pixels, set_tile_pixels, TILE  # noqa: E402

WHITE = (255, 255, 255)

# 13-row bold capitals (3px strokes) for the 23/25px circles
CAPS = {
    "B": ["########...", "#########..", "###....###.", "###....###.", "###...###..",
          "########...", "#########..", "###....###.", "###.....###", "###.....###",
          "###....###.", "##########.", "#########.."],
    "A": ["....###....", "...#####...", "...#####...", "..###.###..", "..###.###..",
          ".###...###.", ".###...###.", ".#########.", "###########", "###.....###",
          "###.....###", "###.....###", "###.....###"],
    "T": ["###########", "###########", "###########", "....###....", "....###....",
          "....###....", "....###....", "....###....", "....###....", "....###....",
          "....###....", "....###....", "....###...."],
    "L": ["###......", "###......", "###......", "###......", "###......", "###......",
          "###......", "###......", "###......", "###......", "#########", "#########",
          "#########"],
    "E": ["#########", "#########", "###......", "###......", "###......", "########.",
          "########.", "########.", "###......", "###......", "#########", "#########",
          "#########"],
    "I": ["#########", "#########", "...###...", "...###...", "...###...", "...###...",
          "...###...", "...###...", "...###...", "...###...", "...###...", "#########",
          "#########"],
    "S": ["..#######..", ".#########.", "###.....###", "###........", "####.......",
          ".#######...", "..#######..", "......####.", "........###", "###.....###",
          "###.....###", ".#########.", "..#######.."],
    "N": ["###.....###", "####....###", "#####...###", "######..###", "###.##..###",
          "###.###.###", "###..##.###", "###..######", "###...#####", "###....####",
          "###.....###", "###.....###", "###.....###"],
    "D": ["########...", "#########..", "###...####.", "###....###.", "###.....###",
          "###.....###", "###.....###", "###.....###", "###.....###", "###....###.",
          "###...####.", "#########..", "########..."],
    "M": ["###.....###", "####...####", "#####.#####", "###########", "###.###.###",
          "###.###.###", "###..#..###", "###.....###", "###.....###", "###.....###",
          "###.....###", "###.....###", "###.....###"],
    "U": ["###.....###", "###.....###", "###.....###", "###.....###", "###.....###",
          "###.....###", "###.....###", "###.....###", "###.....###", "###.....###",
          "####...####", ".#########.", "..#######.."],
}

# 11-row set (2px bars) for Battle's smaller 21px circles
CAPS_S = {
    "B": ["#######..", "########.", "###...###", "###...###", "########.", "#######..",
          "########.", "###...###", "###...###", "########.", "#######.."],
    "A": ["...###...", "..#####..", "..##.##..", ".###.###.", ".##...##.", "###...###",
          "#########", "#########", "###...###", "###...###", "###...###"],
    "T": ["#########", "#########", "...###...", "...###...", "...###...", "...###...",
          "...###...", "...###...", "...###...", "...###...", "...###..."],
    "L": ["###......", "###......", "###......", "###......", "###......", "###......",
          "###......", "###......", "###......", "#########", "#########"],
    "E": ["#########", "#########", "###......", "###......", "########.", "########.",
          "###......", "###......", "###......", "#########", "#########"],
}

# optical centring: D's weight sits left (heavy stem, thin curve) -- user
OPTICAL_DX = {"D": 1}

STYLE = {
    # banner colour, outer border, shadow tint. The outer border was a pale tint
    # of the banner colour at first; it read much softer than the originals,
    # so it is white (user)
    "green": dict(bg=(82, 156, 82), outer=(255, 255, 255), shadow=(123, 189, 107)),
    "brown": dict(bg=(156, 107, 16), outer=(255, 255, 255), shadow=(206, 181, 132)),
}

SS = 4             # supersamples per pixel per axis
SHADOW_DY = 0.75   # 1.5 looked bottom-heavy (user)


def glyph(ch, caps):
    g = caps[ch]
    h, w = len(g), len(g[0])
    assert h % 2 and w % 2, (ch, w, h)
    ox = OPTICAL_DX.get(ch, 0)
    return [(c - w // 2 + ox, r - h // 2)
            for r in range(h) for c in range(w) if g[r][c] == "#"]


def design(word, x0, x1, style, d, pitch, caps, cy=14, rows=(0, 29)):
    """{(x, y): rgb} for every pixel of x0..x1 x rows (exclusive ends)."""
    st = STYLE[style]
    bg, outer, shadow = st["bg"], st["outer"], st["shadow"]
    n = len(word)
    total = pitch * (n - 1) + d
    assert total <= x1 - x0, (word, total, x1 - x0)
    left = x0 + (x1 - x0 - total) // 2
    centres = [left + d // 2 + i * pitch for i in range(n)]
    r3 = d / 2.0
    r2, r1 = r3 - 1.25, r3 - 2.25
    solid = set()
    for ch, cx in zip(word, centres):
        solid |= {(cx + dx, cy + dy) for dx, dy in glyph(ch, caps)}
    halo = {}
    for (x, y) in solid:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                q = (x + dx, y + dy)
                if q not in solid:
                    halo[q] = halo.get(q, 0) + (2 if dx == 0 or dy == 0 else 1)

    def sample(px, py):
        ds = [((px - cx - 0.5) ** 2 + (py - cy - 0.5) ** 2) ** 0.5 for cx in centres]
        if any(r1 <= v < r2 for v in ds):
            return bg                      # every ring on top: they cross
        if any(v < r1 for v in ds):
            return WHITE
        if any(v < r3 for v in ds):
            return outer
        if any(((px - cx - 0.5) ** 2 + (py - cy - 0.5 - SHADOW_DY) ** 2) ** 0.5 < r3
               for cx in centres):
            return shadow
        return bg

    out = {}
    for y in range(*rows):
        for x in range(x0, x1):
            if (x, y) in solid:
                out[(x, y)] = bg
                continue
            cs = [sample(x + (i + 0.5) / SS, y + (j + 0.5) / SS)
                  for i in range(SS) for j in range(SS)]
            c = tuple(sum(v[k] for v in cs) / len(cs) for k in range(3))
            if (x, y) in halo:                         # soft letter edge
                t = min(1.0, halo[(x, y)] / 10.0)
                c = tuple(c[k] * (1 - t) + bg[k] * t for k in range(3))
            out[(x, y)] = c
    return out


def _orients(px):
    rows = [px[r * TILE:(r + 1) * TILE] for r in range(TILE)]
    for fh in (0, 1):
        for fv in (0, 1):
            rr = rows[::-1] if fv else rows
            yield tuple(v for row in rr for v in (row[::-1] if fh else row)), fh, fv


def paint(layer, word, x0, x1, style, d, pitch, caps, cy=14, rows=(0, 29)):
    """Write the design into `layer`. Returns (starved, cells_touched)."""
    target = design(word, x0, x1, style, d, pitch, caps, cy, rows)
    cells = sorted({(y // TILE) * layer.sw + x // TILE for (x, y) in target})
    banks = sorted({layer.cells[ci]["palette"] for ci in cells})

    def bank_rgb(b):
        return [(i, tuple(layer.palette[b * 16 + i][:3])) for i in range(1, 16)
                if b * 16 + i < len(layer.palette)]

    # per cell: the wanted 8x8 in screen orientation, as (bank, indices)
    wanted = {}
    for ci in cells:
        cx, cy0 = (ci % layer.sw) * TILE, (ci // layer.sw) * TILE
        pix = []
        for yy in range(TILE):
            for xx in range(TILE):
                p = (cx + xx, cy0 + yy)
                pix.append(target[p] if p in target else layer.rgb_at(*p))
        best = None
        for b in banks:
            pal = bank_rgb(b)
            idx, err = [], 0
            for c in pix:
                if c is None:
                    idx.append(0)
                    continue
                i, rgb = min(pal, key=lambda e: sum((e[1][k] - c[k]) ** 2 for k in range(3)))
                idx.append(i)
                err += sum((rgb[k] - c[k]) ** 2 for k in range(3))
            if best is None or err < best[0]:
                best = (err, b, tuple(idx))
        wanted[ci] = (best[1], best[2])

    # detach the header cells from their tiles, then harvest the pool
    for ci in cells:
        t = layer.cells[ci]["tile"]
        layer.tile_users[t].discard(ci)
        layer.users[t] -= 1
    pool = layer.free_by_dedupe()
    pool = [t for t in pool if not layer.tile_users[t]]
    have = {}
    for t in range(layer.n_tiles):
        if layer.tile_users[t]:
            for img, fh, fv in _orients(tile_pixels(layer.tiles, t, layer.bpp)):
                have.setdefault(img, (t, fh, fv))
    starved = 0
    for ci in cells:
        bank, img = wanted[ci]
        hit = have.get(img)
        if hit is None:
            if not pool:
                starved += 1
                hit = min(have.items(), key=lambda kv: sum(a != b for a, b in zip(kv[0], img)))[1]
            else:
                t = pool.pop(0)
                set_tile_pixels(layer.tiles, t, layer.bpp, list(img))
                for o, fh, fv in _orients(list(img)):
                    have.setdefault(o, (t, fh, fv))
                hit = (t, 0, 0)
        t, fh, fv = hit
        c = layer.cells[ci]
        c["tile"], c["flip_h"], c["flip_v"], c["palette"] = t, bool(fh), bool(fv), bank
        layer.tile_users[t].add(ci)
        layer.users[t] += 1
    layer.free_pool = pool
    return starved, len(cells)
