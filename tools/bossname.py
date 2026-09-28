#!/usr/bin/env python3
"""The boss-intro nameplates (info/bossname/bossname0NN.ncg + .ncl), in English.

Before a boss fight a short animation shows a stylised plate: an epithet on the
top line (いかりのじゃりゅう) and the boss's name below it in large letters
(ティアマット). There are 30 plates, one per boss family (the knight plates name
both knights of a pair). Each is a 4bpp NCCG of 16x4 tiles (128x32 px) laid out
in reading order, no screen map, one 16-colour palette.

The lettering is always the same dark brown, RGB (90,57,0), with a lighter brown
drop shadow (+1,+1), on a textured light panel; the frame art (swords, anchors,
chains...) differs per plate. So, per plate:

  1. ink = the palette slot closest to (90,57,0); shadow = the most common
     other brown just below-right of ink pixels;
  2. inside the text box (the ink's bounding box, +1px), every ink pixel and
     every shadow pixel touching ink is erased, filled from the nearest
     untouched pixel on the same row (the panel texture runs horizontally);
  3. the English is drawn with the game font: the epithet on the top line and
     the name (bold) below it, both centred where the Japanese was, in the same
     ink with the same shadow.

The game font at 1x is used for both lines: the Japanese name is ~16px tall,
the font's capitals 10px, and a 2x name would not fit 128px. Width is checked
against the original text box.

    python tools/bossname.py preview OUT.png    contact sheet (original | English)
    build()                                     {rel_path: bytes} for build_patch
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import nbg  # noqa: E402
from bgtext import load_font  # noqa: E402

DIR = "info/bossname"
INK_RGB = (90, 57, 0)

# plate -> (epithet, name). Epithets translate the Japanese; names follow the
# boss table (work/enemy_names.py).
PLATES = {
    1: ("Dragon of Wrath", "Tiamat"),          # いかりのじゃりゅう
    2: ("Frost Beast", "Hydras"),        # ひょうけつまじゅう
    3: ("Ruin Guardian", "Daitarn"),           # いせきのしゅごりゅう
    4: ("Living Legend", "God Dragon"),        # いきてるでんせつ
    5: ("Magnet Knights", "Enura Esra"),      # じしゃくのきし
    7: ("Flower Knights", "Leafla Flora"),    # フラワーナイト
    9: ("Knights of Light", "Lighton Nighton"),  # ひかりのきし
    11: ("Shining Knights", "Gold Silva"),    # かがやくきし
    13: ("Blue Destroyer", "Drill Marlin"),    # あおきはかいしゃ
    14: ("Space Monster", "Big Burn"),         # うちゅうかいじゅう
    15: ("Ancient Weapon", "Daedalus"),        # こだいへいき
    16: ("Noble Light", "Supernova"),          # けだかきひかり
    17: ("Swift Warship", "Nagato"),           # こうそくせんかん
    18: ("Giant Warship", "Musashi"),          # きょだいせんかん
    19: ("Mightiest Ship", "Yamato"),       # さいきょうせんかん
    20: ("Treasure Ship", "Koganemaru"),       # たからぶね
    21: ("Vengeful Zombie", "King Lich"),      # おんねんゾンビ
    22: ("Venom Demon", "Beelzebub"),          # もうどくまじん
    23: ("Ice Devil", "Deathrokia"),           # こおりのあくま
    24: ("Unknown Being", "Nest Queen"),       # みちのせいぶつ
    25: ("Herald of Death", "Belials"),        # しをつげるもの
    26: ("Giant of Ruin", "Colossus"),         # はかいのきょじん
    27: ("Golden Scorpion", "Antares"),        # おうごんのさそり
    28: ("Cyber Watcher", "Spyware"),          # でんしのかんししゃ
    29: ("Hell's Watchdog", "Cerberus"),       # じごくのばんけん
    30: ("Dark Beast", "Dark Wonder"),  # やみのまじゅう
    31: ("Candy Watchdog", "Cookie"),          # おかしのばんけん
    32: ("Death Incarnate", "Mad Lander"),     # しのけしん
    33: ("Masked Sorcerer", "Demon King"),     # かめんのまどうし / まおう
    34: ("Power Bearer", "Demon King"),        # ちからをえしもの / まおう
}

EPITHET_TOP, NAME_TOP = 3, 15      # glyph row 0 of each line
# the text area per plate where frame art reaches into the default 14-114
BOX = {5: (22, 108), 7: (22, 108), 9: (22, 108), 11: (22, 108)}


def _load(n):
    path = os.path.join(BASE, "extracted", DIR, "bossname%03d.ncg" % n)
    tiles, w, h, bpp = nbg.read_nccg(path)
    assert (w, h, bpp) == (16, 4, 4), (n, w, h, bpp)
    pal = nbg.read_nccl(path[:-4] + ".ncl")
    idx = [[0] * 128 for _ in range(32)]
    for t in range(64):
        px = nbg.tile_pixels(tiles, t, 4)
        for i, v in enumerate(px):
            idx[(t // 16) * 8 + i // 8][(t % 16) * 8 + i % 8] = v
    return path, idx, pal[:16]


def _pack(path, idx):
    data = bytearray(open(path, "rb").read())
    off, size = nbg.blocks(data)[b"CHAR"]
    start = off + size - 64 * 32
    for t in range(64):
        for i in range(32):
            y, x = (t // 16) * 8 + (2 * i) // 8, (t % 16) * 8 + (2 * i) % 8
            data[start + t * 32 + i] = idx[y][x] | (idx[y][x + 1] << 4)
    return bytes(data)


def _layout(font, text, bold, tight=False):
    """Ink points and width. Bold thickens each stroke 1px to the right, but
    only where that does not close a 1px gap inside the glyph (M, m, W, w keep
    their counters). `tight` bold adds no extra advance and never thickens a
    glyph's rightmost column, so it is as wide as plain text."""
    pts, pen = set(), 0
    for ch in text:
        gi = font.cmap.get(ord(ch))
        if gi is not None:
            bits = font.bitmap(gi)
            on = {(c, r) for r in range(font.cell_h) for c in range(font.cell_w) if bits[r][c]}
            right = max((c for c, r in on), default=0)
            for (c, r) in on:
                pts.add((pen + c, r))
                if bold and (c + 1, r) not in on and (c + 2, r) not in on:
                    if not (tight and c >= right):
                        pts.add((pen + c + 1, r))
        pen += font.advance(ord(ch)) + (1 if bold and not tight else 0)
    return pts, pen - (1 if bold and not tight else 0)


def paint(n, font):
    """(path, new indices, warnings) for plate n."""
    path, idx, pal = _load(n)
    lum = lambda v: 0.3 * pal[v][0] + 0.59 * pal[v][1] + 0.11 * pal[v][2]
    dist = lambda v: sum((a - b) ** 2 for a, b in zip(pal[v][:3], INK_RGB))
    ink = min(range(1, 16), key=dist)
    # every slot as dark as the ink counts as lettering (palettes repeat the
    # brown in more than one slot)
    dark = {v for v in range(1, 16) if lum(v) <= lum(ink) + 22}
    X0, X1 = BOX.get(n, (14, 114))
    inkpts = [(x, y) for y in range(4, 29) for x in range(X0, X1) if idx[y][x] == ink]
    xs = [x for x, y in inkpts]
    ys = [y for x, y in inkpts]
    x0, x1 = max(min(xs) - 3, X0), min(max(xs) + 4, X1)
    y0, y1 = max(min(ys) - 2, 1), min(max(ys) + 3, 31)
    core = {(x, y) for y in range(y0, y1) for x in range(x0, x1) if idx[y][x] in dark}
    erase = {(x + dx, y + dy) for (x, y) in core for dx in (-1, 0, 1) for dy in (-1, 0, 1)
             if x0 <= x + dx < x1 and y0 <= y + dy < y1}
    # the drop shadow: the commonest colour just below-right of the ink
    from collections import Counter
    sh = Counter(idx[y + 1][x + 1] for x, y in inkpts
                 if y + 1 < 32 and x + 1 < 128 and idx[y + 1][x + 1] not in dark and idx[y + 1][x + 1])
    shadow = sh.most_common(1)[0][0] if sh else None
    # lettering colours besides the ink (shadow, highlight): far more common
    # within 2px of the dark core than anywhere else in the text box
    box = [(x, y) for y in range(y0, y1) for x in range(x0, x1)]
    ring = {(x + dx, y + dy) for (x, y) in core for dx in range(-2, 3) for dy in range(-2, 3)}
    near = [(x, y) for (x, y) in box if (x, y) in ring and (x, y) not in core]
    far = [(x, y) for (x, y) in box if (x, y) not in ring]
    cn = Counter(idx[y][x] for x, y in near)
    cf = Counter(idx[y][x] for x, y in far)
    text_cols = {c for c, k in cn.items() if c and k >= 6 and
                 k / max(len(near), 1) > 2.5 * (cf.get(c, 0) / max(len(far), 1))}
    if shadow is not None:
        text_cols.add(shadow)
    erase |= {(x, y) for (x, y) in near if idx[y][x] in text_cols}
    new = [row[:] for row in idx]
    for y in range(y0, y1):
        x = x0
        while x < x1:
            if (x, y) not in erase:
                x += 1
                continue
            a = x
            while x < x1 and (x, y) in erase:
                x += 1
            b = x                      # run a..b-1 is erased
            for k in range(a, b):
                # mirror the texture in from the nearer edge
                if k - a < b - k:
                    src = a - 1 - (k - a)
                else:
                    src = b + (b - 1 - k)
                src = min(max(src, x0), x1 - 1)
                if (src, y) in erase:
                    src = a - 1 if a - 1 >= 0 else b
                v = idx[y][min(max(src, 0), 127)]
                if v in text_cols or v in dark:
                    # never copy a lettering colour: nearest clean pixel on the row
                    for d in range(1, 64):
                        cand = [xx for xx in (k - d, k + d) if 0 <= xx < 128 and
                                (xx, y) not in erase and idx[y][xx] not in text_cols
                                and idx[y][xx] not in dark and idx[y][xx]]
                        if cand:
                            v = idx[y][cand[0]]
                            break
                new[y][k] = v
    cx = (x0 + x1) // 2
    warn = []
    epithet, name = PLATES[n]
    for text, top, bold in ((epithet, EPITHET_TOP, 0), (name, NAME_TOP, 1)):
        pts, width = _layout(font, text, bold)
        if bold and width > x1 - x0:           # too wide: bold without extra spacing
            pts, width = _layout(font, text, bold, tight=True)
        left = cx - width // 2
        if left < x0 - 2 or left + width > x1 + 2:
            warn.append("%s: %r is %dpx, text box %d-%d" % (n, text, width, x0, x1))
        for (px, py) in pts:
            x, y = left + px + 1, top + py + 1
            if shadow is not None and 0 <= x < 128 and 0 <= y < 32 and (x - 1 - left, y - 1 - top) not in pts:
                new[y][x] = shadow
        for (px, py) in pts:
            x, y = left + px, top + py
            if 0 <= x < 128 and 0 <= y < 32:
                new[y][x] = ink
    return path, idx, new, pal, warn


def build():
    font = load_font()
    out = {}
    for n in PLATES:
        path, _old, new, _pal, warn = paint(n, font)
        for w in warn:
            print("  bossname " + w)
        out["%s/bossname%03d.ncg" % (DIR, n)] = _pack(path, new)
    return out


def preview(out_png, zoom=2):
    from PIL import Image, ImageDraw
    font = load_font()
    rows = []
    for n in PLATES:
        path, old, new, pal, warn = paint(n, font)
        for w in warn:
            print("  " + w)
        im = Image.new("RGB", (128 * 2 + 6, 32), (60, 60, 60))
        for k, grid in enumerate((old, new)):
            for y in range(32):
                for x in range(128):
                    v = grid[y][x]
                    im.putpixel((k * 134 + x, y), pal[v][:3] if v else (60, 60, 60))
        rows.append(im)
    cols = 2
    W, H = rows[0].width * zoom + 8, 32 * zoom + 6
    sheet = Image.new("RGB", (cols * W, ((len(rows) + cols - 1) // cols) * H), (30, 30, 30))
    for k, im in enumerate(rows):
        sheet.paste(im.resize((im.width * zoom, 32 * zoom), Image.NEAREST),
                    ((k % cols) * W, (k // cols) * H))
    sheet.save(out_png)


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "preview":
        preview(sys.argv[2])
    else:
        print(__doc__)
