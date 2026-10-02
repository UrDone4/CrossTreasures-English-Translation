#!/usr/bin/env python3
"""Sub-menu labels: repaint the flat-coloured caption pills on the menu screens.

Every sub-menu (Equipment, Items, Map, Medallion, Quest, shops ...) is a
background layer whose captions sit on flat pills: brown lettering on cream,
white on brown/green/pink/blue. Measuring each caption by hand is what made the
earlier layers slow, so this takes only a *seed* -- a rough box somewhere inside
the Japanese -- and measures the rest:

  1. bg   = commonest colour in the seed; ink = the colour farthest from it.
  2. tight = bounding box of the pixels that differ clearly from bg (the lettering
     plus its antialiasing), looked for within 2px of the seed.
  3. the box = tight, widened sideways across columns that are still plain bg (the
     pill interior) and grown up/down by the free rows, so the English has room
     and the clear cannot reach the pill's border.

English is centred in the box, or set at the Japanese's left edge with
align="left" (captions that start at the pill's left end).

    submenu_labels.py <archive> <member>     print what each seed resolves to
"""

import collections
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def dist(a, b):
    return sum((p - q) ** 2 for p, q in zip(a, b)) ** 0.5


def analyse(layer, seed, tol=12, reach_x=60, reach_y=10):
    """Measure the caption around `seed`. Returns (tight, box, bg, ink) or None.

    The seed only has to sit on the pill's plain fill (bg = its commonest
    colour). The pill interior is the connected area of bg around it; the
    lettering is whatever is enclosed inside that area's bounding box without
    reaching its edge (the rounded corners and outline do reach it, so they are
    not mistaken for text). `box` is the interior at the lettering's rows.
    """
    x0, y0, x1, y1 = seed
    hist = collections.Counter()
    for y in range(y0, y1):
        for x in range(x0, x1):
            c = layer.rgb_at(x, y)
            if c is not None:
                hist[c] += 1
    if not hist:
        return None
    bg = hist.most_common(1)[0][0]
    far = [(dist(c, bg), c) for c, n in hist.items() if n >= 3]
    if not far:
        return None
    reach, ink = max(far)
    if reach < 60:
        return None

    wx0, wx1 = max(0, x0 - reach_x), min(layer.width, x1 + reach_x)
    wy0, wy1 = max(0, y0 - reach_y), min(layer.height, y1 + reach_y)

    # a fill can be two-tone or dithered: every substantial colour of the seed
    # that is nearer the fill than the ink counts as backdrop
    area = (x1 - x0) * (y1 - y0)
    fills = [c for c, n in hist.items()
             if n >= max(3, area * 0.08) and dist(c, bg) < reach * 0.5] or [bg]

    def is_bg(x, y):
        c = layer.rgb_at(x, y)
        return c is not None and any(dist(c, f) <= tol for f in fills)

    # start from every backdrop pixel near the seed, not just inside it: a seed
    # sitting in a glyph's counter would otherwise flood only that counter
    region, stack = set(), []
    for y in range(y0 - 6, y1 + 6):
        for x in range(x0 - 6, x1 + 6):
            if is_bg(x, y) and (x, y) not in region:
                region.add((x, y))
                stack.append((x, y))
    while stack:
        x, y = stack.pop()
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if (wx0 <= nx < wx1 and wy0 <= ny < wy1 and (nx, ny) not in region
                    and is_bg(nx, ny)):
                region.add((nx, ny))
                stack.append((nx, ny))
    if len(region) < 20:
        return None
    bx0 = min(x for x, _ in region)
    bx1 = max(x for x, _ in region) + 1
    by0 = min(y for _, y in region)
    by1 = max(y for _, y in region) + 1

    # non-region pixels inside the bounding box, split into connected pieces;
    # a piece that never reaches the box edge is lettering
    seen, text = set(), []
    for y in range(by0, by1):
        for x in range(bx0, bx1):
            if (x, y) in region or (x, y) in seen:
                continue
            piece, stack, edge = [], [(x, y)], False
            seen.add((x, y))
            while stack:
                px, py = stack.pop()
                piece.append((px, py))
                if px in (bx0, bx1 - 1) or py in (by0, by1 - 1):
                    edge = True
                for nx, ny in ((px + 1, py), (px - 1, py), (px, py + 1), (px, py - 1)):
                    if (bx0 <= nx < bx1 and by0 <= ny < by1
                            and (nx, ny) not in region and (nx, ny) not in seen):
                        seen.add((nx, ny))
                        stack.append((nx, ny))
            small = False
            if edge:
                # a glyph can sit right against the pill's edge (the Description
                # and Name captions on the power screens do); outlines are
                # thin lines (a few px high) or tall verticals, glyph runs are 6-13px high
                qx = [px for px, _ in piece]
                qy = [py for _, py in piece]
                hh = max(qy) - min(qy) + 1
                small = 6 <= hh <= 13 and max(qx) - min(qx) < 48
            if not edge or small:
                # only lettering near the seed: neighbouring captions and input
                # boxes on the same pill are separate pieces and must be left alone
                px0 = min(px for px, _ in piece)
                px1 = max(px for px, _ in piece)
                py0 = min(py for _, py in piece)
                py1 = max(py for _, py in piece)
                if px1 >= x0 - 3 and px0 <= x1 + 3 and py1 >= y0 - 3 and py0 <= y1 + 3:
                    text += piece
    if not text:
        return None
    tx0 = min(x for x, _ in text)
    tx1 = max(x for x, _ in text) + 1
    ty0 = min(y for _, y in text)
    ty1 = max(y for _, y in text) + 1
    tight = (tx0, ty0, tx1, ty1)

    # the free run around the lettering: sideways until something else (another
    # caption, an input box, the outline) interrupts the fill; up/down by one row
    rows = range(max(by0, ty0 - 1), min(by1, ty1 + 1))
    xl, xr = tx0, tx1
    while xl - 1 >= bx0 and all((xl - 1, y) in region for y in rows):
        xl -= 1
    while xr < bx1 and all((xr, y) in region for y in rows):
        xr += 1
    # centre on the Japanese: a caption on an open panel (no pill) has free run
    # far wider than the word, and the English belongs where the Japanese was
    half = min(tx0 - xl, xr - tx1)
    if xr - xl > (tx1 - tx0) + 24:
        xl, xr = tx0 - half, tx1 + half
    box = (xl, rows.start, xr, rows.stop)
    return tight, box, bg, ink, (by0, by1)


def colours(layer, seed):
    """(bg, ink) of a seed without measuring it -- for boxes given by hand."""
    x0, y0, x1, y1 = seed
    hist = collections.Counter(layer.rgb_at(x, y) for x in range(x0, x1)
                               for y in range(y0, y1))
    hist.pop(None, None)
    bg = hist.most_common(1)[0][0]
    ink = max((c for c, n in hist.items() if n >= 3), key=lambda c: dist(c, bg))
    return bg, ink


class Labels(list):
    """paint_layer labels plus the boxes whose cells must get private tiles."""
    private = ()


def labels_for(layer, font, seeds, report=True):
    """Turn [(seed, english[, align[, {"box": ...}]])] into paint_layer labels.

    `bg` / `ink` / `box` overrides give colours or the box by hand.
    An `inpaint: True` override erases into a shaded backdrop row by row.
    A `private: True` override marks a caption that differs between screens
    sharing tiles: its cells get their own tiles.
    A `grow: "left"` override widens a tab pill leftwards to fit the English.
    An `indent: n` override starts left-aligned text n px inside the box.
    A `rowfill: (x0, x1)` override fills each cleared row with its commonest
    colour across x0-x1 (a shaded pill); `dy: n` moves the text down n px.
    A `box` override is for captions the measurement cannot isolate -- a header
    whose lettering fills its column edge to edge, so it touches the dividers.
    """
    out = Labels()
    out.private = []
    for item in seeds:
        seed, english = item[0], item[1]
        align = item[2] if len(item) > 2 else "center"
        over = item[3] if len(item) > 3 else {}
        got = analyse(layer, seed)
        if got is None and "box" not in over:
            print("    !! seed %s holds no lettering (%r)" % (seed, english))
            continue
        pill = None
        if got is not None:
            tight, box, bg, ink, pill = got
        elif "bg" in over and not english:
            bg, ink = over["bg"], over["bg"]      # a plain patch: nothing to measure
        else:
            bg, ink = colours(layer, seed)
            tight = over["box"]
        if "bg" in over:                  # colours given: the seed is mostly lettering
            bg = over["bg"]
        if "ink" in over:
            ink = over["ink"]
        if "box" in over:
            box = over["box"]
            tight = (box[0], tight[1], tight[2], tight[3]) if got else box
        if "indent" in over:
            # left-aligned text starts this far inside the box: the box must
            # reach the Japanese's first antialiased pixel, but the English
            # should keep the original's gap after the button icon
            tight = (tight[0] + over["indent"],) + tuple(tight[1:])
        width = sum(-1 if c == "\b" else font.advance(ord(c)) for c in english)
        if over.get("grow") == "left" and pill:
            # the tab pill is sized for the Japanese: widen it leftwards (over
            # whatever is there) to the full height of the pill, with a margin
            x0 = min(box[0], box[2] - width - 12)
            box = (x0, pill[0], box[2], pill[1])
            tight = (x0 + 6, tight[1], tight[2], tight[3])
        if over.get("inpaint"):
            # the caption sits over a shaded backdrop (two greens, a curve): keep
            # every substantial light colour of the region and erase the lettering
            # into the nearest of them, row by row, instead of one flat fill
            cx0, cy0, cx1, cy1 = box
            hist = collections.Counter()
            for yy in range(cy0 - 1, cy1 + 1):
                for xx in range(cx0 - 2, cx1 + 2):
                    c = layer.rgb_at(xx, yy)
                    if c and 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2] > 180:
                        hist[c] += 1
            keeps = tuple(c for c, n in hist.most_common() if n >= 60) or (bg,)
            bg = ("auto", keeps)
        if "rowfill" in over:
            # a shaded pill (light rim, darker centre, lighter bands): a flat
            # fill shows as a darker box. Fill each row with that row's
            # commonest colour across the pill's own span `rowfill` = (x0, x1)
            # -- the lettering is too sparse to win it. Measured on the
            # untouched art (prepare() runs before any painting).
            sx0, sx1 = over["rowfill"]
            dy = over.get("dy", 0)
            fill = {}
            for yy in range(box[1], box[3] + max(dy, 0)):
                row = collections.Counter(layer.rgb_at(xx, yy) for xx in range(sx0, sx1))
                mode = row.most_common(1)[0][0]
                for xx in range(box[0], box[2]):
                    fill[(xx, yy)] = mode
            bg = fill
        if "pillfill" in over:
            # a rounded pill with a white outline and white lettering (the
            # Equipment screen's Total Attack / Defense / Resist tabs): on each
            # row, repaint only the span between the first and last pixel of
            # the pill's own colour -- the outline, the rounded ends and
            # everything outside stay as drawn. A flat box squared the pills
            # off and left a grey strip (hardware 2026-09-26)
            colour = tuple(over["pillfill"])
            fill = {}
            for yy in range(box[1], box[3] + max(over.get("dy", 0), 0)):
                xs = [xx for xx in range(box[0], box[2])
                      if layer.rgb_at(xx, yy) and tuple(layer.rgb_at(xx, yy)[:3]) == colour]
                for xx in range(box[0], box[2]):
                    inside = xs and min(xs) <= xx <= max(xs)
                    fill[(xx, yy)] = colour if inside else layer.rgb_at(xx, yy)
            bg = fill
        if "fillfrom" in over:
            # another screen has this very plate without the lettering (the
            # Invite title plate = time_mode_mlt_inv2_bg's blank one): take the
            # background pixel for pixel from it, soft glow and all, instead of
            # a flat box (hardware 2026-09-26: the flat Invite box showed)
            root = os.path.join(os.path.dirname(HERE), "extracted", "info")
            from bgtext import BgLayer
            ref = BgLayer(*(os.path.join(root, over["fillfrom"] + e)
                            for e in (".ncg", ".ncl", ".nsc")))
            bg = {(xx, yy): ref.rgb_at(xx, yy)
                  for yy in range(box[1], box[3]) for xx in range(box[0], box[2])}
        if over.get("private"):
            out.private.append(box)
        if width > box[2] - box[0]:
            print("    !! %r is %dpx, room is %dpx" % (english, width, box[2] - box[0]))
        dy = over.get("dy", 0)
        if align == "left":
            out.append((box, "", bg, ink, 1))
            out.append(((tight[0], box[1] + dy, tight[0] + width + 1, box[3] + dy),
                        english, bg, ink, 1))
        elif dy:
            # `dy` moves the text (not the clear) down: the box is centred for
            # the Japanese, which sat a pixel lower than centred English does
            out.append((box, "", bg, ink, 1))
            out.append(((box[0], box[1] + dy, box[2], box[3] + dy),
                        english, bg, ink, 1))
        else:
            out.append((box, english, bg, ink, 1))
        if report:
            print("    %-16s tight=%s box=%s bg=%s ink=%s"
                  % (english, tight, box, bg, ink))
    return out


def prepare(layer, font, key):
    """Measure this layer's seeds on the *untouched* art.

    Screens that share a tile set are painted one after another, and a later
    screen's lettering may already have been altered by an earlier one. So every
    measurement is taken up front, on the original, and paint() just applies it.
    """
    sys.path.insert(0, os.path.join(os.path.dirname(HERE), "work"))
    from submenu_seeds import SEEDS
    labels = labels_for(layer, font, SEEDS[key], report=False)
    # the per-pixel erase too: resolved later, a screen painted after a sibling
    # sees the sibling's English through their shared tiles and takes it for
    # Japanese (stray pixels beside "OK"), or no longer sees the Japanese a
    # leftover fringe pixel belonged to
    out = Labels(
        (box, text,
         layer.inpaint_targets(box, bg[1], only_ink=True)
         if isinstance(bg, tuple) and bg and bg[0] == "auto" else bg,
         ink, scale)
        for box, text, bg, ink, scale in labels)
    out.private = labels.private
    return out


def paint(layer, font, key, labels=None):
    """paint hook for bg_labels: repaint this layer from its (pre-measured) seeds."""
    from bg_labels import paint_layer
    if labels is None:
        labels = prepare(layer, font, key)
    # captions that differ between screens sharing this tile set must not be
    # painted through the shared tiles, or the last screen painted wins
    layer.force_private = set()
    for box in getattr(labels, "private", ()):
        layer.force_private |= layer.cells_in(box)
    # areas whose tiles must never be merged with a near-copy (the pool can
    # run short and near-copy merges then change art away from any label)
    from submenu_seeds import KEEP_EXACT
    layer.keep_exact = set()
    for box in KEEP_EXACT.get(key, ()):
        layer.keep_exact |= layer.cells_in(box)
    return paint_layer(layer, labels, font, lossy=True)


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 1
    import tempfile
    from bgtext import BgLayer, load_font
    from narc import Narc
    from bg_labels import paint_layer
    sys.path.insert(0, os.path.join(os.path.dirname(HERE), "work"))
    from submenu_seeds import SEEDS
    root = os.path.dirname(HERE)
    archive, member = argv[1], int(argv[2])
    narc = Narc(os.path.join(root, "extracted", "info", "subgraphics",
                             archive + ".narc"))
    tmp = tempfile.mkdtemp()
    paths = []
    for k in range(3):
        p = os.path.join(tmp, "%d.bin" % k)
        with open(p, "wb") as fh:
            fh.write(narc.file(member + k))
        paths.append(p)
    layer = BgLayer(*paths)
    font = load_font()
    labels = labels_for(layer, font, SEEDS[(archive, member)])
    print(paint_layer(layer, labels, font, lossy=True))
    out = os.path.join(root, "work", "gfx", "submenu")
    os.makedirs(out, exist_ok=True)
    layer.render(os.path.join(out, "%s_%d.png" % (archive, member)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
