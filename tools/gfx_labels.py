#!/usr/bin/env python3
"""Repaint Japanese sprite labels as English across the title-screen banks.

Two styles occur, and they need different handling:

"framed"   -- a button with a frame and a flat face (title menu). The face
              colour is detected as the most common opaque index in the cell;
              the interior bounding box is cleared, inset so the frame and its
              bevel survive, and text is drawn in a single ink colour.

"outlined" -- a free-standing styled word sitting directly on the background
              (options menu). There is no face to clear, so the whole cell is
              cleared to transparent and the text redrawn with an outline.
              These come in pairs: an unselected version and a highlighted one.

Text is drawn with the game's own LCFont glyphs at 2x, dropping to 1x only if
2x will not fit.

    gfx_labels.py preview          render every patched cell to work/gfx/en/
    gfx_labels.py apply <outdir>   write patched .NCGR files to outdir
"""

import collections
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from gfxtext import Bank, TITLE_DIR, FONT  # noqa: E402
from nftr import Nftr  # noqa: E402

FRAMED_INK = 5          # dark brown lettering on the title buttons

# bank -> cell -> spec
LABELS = {
    "tito_menu_obj": {
        # large buttons, then the same four in the small style
        1: {"style": "framed", "text": "New Game"},
        2: {"style": "framed", "text": "Continue"},
        3: {"style": "framed", "text": "Options"},
        4: {"style": "framed", "text": "Password", "margin_clean": True},
        5: {"style": "framed", "text": "New Game"},
        6: {"style": "framed", "text": "Continue"},
        7: {"style": "framed", "text": "Options"},
        8: {"style": "framed", "text": "Password", "margin_clean": True},
    },
    # The Options list: 0-2 selected (orange band, dark edge), 3-5 unselected
    # (brown band), all with the grey drop shadow -- see "styled" below.
    "tiop_top_obj": {
        0: {"style": "styled", "lines": ["System"]},
        1: {"style": "styled", "lines": ["Credits"]},
        2: {"style": "styled", "lines": ["Erase", "Save Data"]},
        3: {"style": "styled", "lines": ["System"]},
        4: {"style": "styled", "lines": ["Credits"]},
        5: {"style": "styled", "lines": ["Erase", "Save Data"]},
        # 6 is the greyed-out (disabled) Erase Save Data, drawn as an opaque overlay
        # (entries 0-6) over a copy of cell 5's tiles (entries 7-13). Only the
        # overlay may be written: writing through every covering entry would
        # repaint cell 5's shared tiles grey too. Its colours are given because
        # by the time it is painted, cell 5 (showing through) is already English.
        6: {"style": "styled", "lines": ["Erase", "Save Data"], "only": range(7),
            "roles": (13, 8, None, 3)},
    },
    # The Continue menu reached when a save exists. Cells 1-4 are the selected
    # state (orange band), cells 5-8 the same four unselected (brown band).
    "time_mode_obj": {
        1: {"style": "styled", "lines": ["Play", "Alone"]},
        2: {"style": "styled", "lines": ["Multi", "Player"]},
        3: {"style": "styled", "lines": ["World", "Cross"]},  # マージ (Merge) -- was "Connect"
        4: {"style": "styled", "lines": ["Co-op", "Quest"]},
        5: {"style": "styled", "lines": ["Play", "Alone"]},
        # unselected Multi/Player is only 48px tall: at the usual 2px shadow
        # only pitch 20 fit, where the M's foot met the l's top (hardware).
        # A 1px-shorter shadow lets it use pitch 21, as the selected cell does.
        6: {"style": "styled", "lines": ["Multi", "Player"], "shadow": (2, 1),
            "pitch": (21,), "weights": ((1, 2), (0, 2))},
        7: {"style": "styled", "lines": ["World", "Cross"]},
        8: {"style": "styled", "lines": ["Co-op", "Quest"]},
    },
}



def interior_colour(bank, ci):
    """The button face: the most common opaque palette index in the cell."""
    w, h = bank.size(ci)
    hist = collections.Counter()
    for y in range(h):
        for x in range(w):
            v = bank.get(ci, x, y)
            if v:
                hist[v] += 1
    return hist.most_common(1)[0][0] if hist else None


def interior_box(bank, ci, colour, inset=2):
    """Bounding box of the button's interior colour, inset by a safe margin."""
    w, h = bank.size(ci)
    xs, ys = [], []
    for y in range(h):
        for x in range(w):
            if bank.get(ci, x, y) == colour:
                xs.append(x)
                ys.append(y)
    if not xs:
        return None
    return (min(xs) + inset, min(ys) + inset, max(xs) + 1 - inset, max(ys) + 1 - inset)


def do_framed(bank, font, name, ci, spec):
    face = interior_colour(bank, ci)
    box = interior_box(bank, ci, face) if face else None
    if box is None:
        print("  %s cell %d: no interior found, skipped" % (name, ci))
        return
    # the inset box can leave the ends of a long caption in its 2px margin, over
    # the face's shaded border (ひみつのじゅもん's first and last glyphs showed
    # beside "Password"). That border runs in vertical bands of one colour, so
    # repaint the margin columns, in the lettering's rows, from a clean row
    # above it. Opt-in: the other buttons' captions stay clear of the margin
    # (and are hardware-verified as they are).
    w, _h = bank.size(ci)
    lettering = [y for y in range(box[1], box[3])
                 if any(bank.get(ci, x, y) != face for x in range(box[0], box[2]))]
    bank.fill(ci, box, face)
    if lettering and spec.get("margin_clean"):
        ref = min(lettering) - 1
        margin = (list(range(max(0, box[0] - 4), box[0]))
                  + list(range(box[2], min(w, box[2] + 4))))
        for y in lettering:
            for x in margin:
                want = bank.get(ci, x, ref)
                if want and bank.get(ci, x, y) != want:
                    bank.put(ci, x, y, want)
    for scale in (2, 1):
        if bank.draw_text(ci, font, spec["text"], box, FRAMED_INK, scale=scale):
            print("  %-14s cell %d  framed    %-20s face=%2d scale=%dx"
                  % (name, ci, repr(spec["text"]), face, scale))
            return
    print("  %s cell %d: %r does not fit" % (name, ci, spec["text"]))


def do_outlined(bank, font, name, ci, spec):
    w, h = bank.size(ci)
    bank.only = set(spec["only"]) if "only" in spec else None
    try:
        _do_outlined(bank, font, name, ci, spec, w, h)
    finally:
        bank.only = None


def _do_outlined(bank, font, name, ci, spec, w, h):
    bank.clear(ci, 0)
    box = (0, 0, w, h)
    for scale in (2, 1):
        if bank.draw_outlined(ci, font, spec["lines"], box,
                              spec["ink"], spec["outline"], scale=scale):
            print("  %-14s cell %d  outlined  %-20s ink=%2d out=%2d scale=%dx"
                  % (name, ci, "/".join(spec["lines"]), spec["ink"],
                     spec["outline"], scale))
            return
    print("  %s cell %d: %r does not fit in %dpx" % (name, ci, spec["lines"], w))


# ---- "styled": the title menus' chunky display words ---------------------
# The original words (ひとりで あそぶ, システム ...) are heavy lettering: a white
# core, a wide coloured band round it (orange when selected, brown when not),
# on the selected ones a thin dark-brown edge outside the band, and a grey
# drop shadow down and to the right. The plain 1px outline used before read as
# a different game. This rebuilds that construction around the English: the
# font at 2x with letters 1px closer (so the band runs between them, as it
# does between the Japanese glyphs), then band / edge / shadow as rings grown
# from the letters. The colours are read from each cell's own art, so every
# state keeps its palette.

SHADOW_RGB = (99, 99, 99)


def _lum(c):
    return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]


def styled_roles(bank, ci):
    """(fill, band, edge, shadow) palette indices, from the cell's art."""
    w, h = bank.size(ci)
    e = bank.cells[ci][0]
    rgb = lambda i: tuple(bank.palette[e["palette"] * 16 + i][:3])
    hist = collections.Counter(bank.get(ci, x, y) for y in range(h) for x in range(w))
    hist.pop(0, None)
    used = list(hist)
    shadow = next((i for i in used if rgb(i) == SHADOW_RGB), None)
    fill = max(used, key=lambda i: (_lum(rgb(i)), hist[i]))
    rest = [i for i in used if i not in (fill, shadow) and _lum(rgb(i)) < 200]
    band = max(rest, key=lambda i: hist[i])
    edge = min(rest, key=lambda i: _lum(rgb(i)))
    return fill, band, (None if edge == band else edge), shadow


def _grow(mask, r):
    out = set()
    for (x, y) in mask:
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                if dx * dx + dy * dy <= r * r + r:      # a rounded disc
                    out.add((x + dx, y + dy))
    return out


def styled_mask(font, lines, pitch, scale=2, tighten=1, bold=0):
    """Lit pixels of the lines at `scale` (centred on x = 0, first line's top
    at 0). `bold` widens every stroke that many px to the right, and the
    letters are spaced that much further apart so they never touch."""
    pix = set()
    for li, line in enumerate(lines):
        step = lambda c: font.advance(ord(c)) * scale - tighten + bold
        width = sum(step(c) for c in line) + tighten - bold
        pen = -width // 2
        top = li * pitch
        for ch in line:
            gi = font.cmap.get(ord(ch))
            if gi is not None:
                bits = font.bitmap(gi)
                for r in range(font.cell_h):
                    for c in range(font.cell_w):
                        if bits[r][c]:
                            for sy in range(scale):
                                for sx in range(scale + bold):
                                    pix.add((pen + c * scale + sx, top + r * scale + sy))
            pen += step(ch)
    return pix


# heaviest first: (bold, band) -- the first that fits the cell is used
STYLED_WEIGHTS = ((1, 3), (1, 2), (0, 3), (0, 2))


def do_styled(bank, font, name, ci, spec):
    w, h = bank.size(ci)
    bank.only = set(spec["only"]) if "only" in spec else None
    try:
        fill, band, edge, shadow = spec.get("roles") or styled_roles(bank, ci)
        sx, sy = spec.get("shadow", (2, 2))
        fit = None
        for bold, rb in spec.get("weights", STYLED_WEIGHTS):
            re_ = 1 if edge is not None else 0
            for pitch in spec.get("pitch", (21, 20)):
                core = styled_mask(font, spec["lines"], pitch, bold=bold)
                outer = _grow(core, rb + re_)
                shade = ({(x + sx, y + sy) for x, y in outer}
                         if shadow is not None else set())
                everything = outer | shade
                x0 = min(x for x, _ in everything); x1 = max(x for x, _ in everything)
                y0 = min(y for _, y in everything); y1 = max(y for _, y in everything)
                if x1 - x0 < w and y1 - y0 < h:
                    fit = (bold, rb, pitch)
                    break
            if fit:
                break
        if not fit:
            print("  !! %s cell %d: %r does not fit %dx%d" % (name, ci, spec["lines"], w, h))
            return
        bold, rb, pitch = fit
        ox = (w - (x1 - x0 + 1)) // 2 - x0
        oy = (h - (y1 - y0 + 1)) // 2 - y0
        bank.clear(ci, 0)
        bandset = _grow(core, rb)
        for layer, colour in ((shade - outer, shadow), (outer - bandset, edge),
                              (bandset - core, band), (core, fill)):
            if colour is None:
                continue
            for x, y in layer:
                if 0 <= x + ox < w and 0 <= y + oy < h:
                    bank.put(ci, x + ox, y + oy, colour)
        print("  %-14s cell %d  styled    %-20s fill=%d band=%d edge=%s shadow=%s "
              "bold=%d band=%dpx pitch=%d" % (name, ci, "/".join(spec["lines"]), fill,
                                            band, edge, shadow, bold, rb, pitch))
    finally:
        bank.only = None


# Cells re-laid out before painting: bank -> cell -> the cell's complete new
# OAM list [(x, y, w, h, tile), ...] (the cell's first original entry is the
# template for the other OAM bits). The tiles must be the cell's OWN original
# tiles: the game uploads only the tiles its cells use, so a tile no cell used
# is not in VRAM -- the first attempt here borrowed the "unused" tiles 617-626
# for an extra 8px strip and showed another graphic's data there (hardware).
# time_mode_obj cell 7 is the unselected マージ button, 88x40 (one Japanese
# line); "World / Cross" needs two, so it becomes 64x48 (y 8-56, like the
# selected cell 3's y 7-55): a 64x32 plus two 32x16, centred on the old cell,
# using 48 of its own 54 tiles (488-535).
RELAYOUT = {
    "time_mode_obj": {
        7: [(-84, 8, 64, 32, 488), (-84, 40, 32, 16, 520), (-52, 40, 32, 16, 528)],
    },
}


def relayout_cells(bank, name):
    """Apply RELAYOUT to a loaded bank; returns the new NCER bytes or None."""
    if name not in RELAYOUT:
        return None
    from ngfx import ncer_raw, oam_words, rebuild_ncer, read_ncer
    src = open(os.path.join(TITLE_DIR, name + ".NCER"), "rb").read()
    raw = ncer_raw(src)

    def tiles_of(ents):
        out = set()
        for e in ents:
            out |= set(range(e["tile"], e["tile"] + (e["w"] // 8) * (e["h"] // 8)))
        return out
    for ci, layout in RELAYOUT[name].items():
        own = tiles_of(bank.cells[ci])
        new = set()
        for x, y, w, h, tile in layout:
            new |= set(range(tile, tile + (w // 8) * (h // 8)))
        assert new <= own, "%s cell %d: tiles %s are not the cell's own" % (
            name, ci, sorted(new - own))
        # (not cleared here: the styled painter samples the cell's colours
        # first, then clears the whole cell itself before drawing)
        template = raw[ci][0]
        raw[ci] = [oam_words(template, x, y, w, h, tile) for x, y, w, h, tile in layout]
    out = rebuild_ncer(src, raw)
    tmp = os.path.join(os.path.dirname(HERE), "work", "gfx", "_relayout_%s.NCER" % name)
    os.makedirs(os.path.dirname(tmp), exist_ok=True)
    open(tmp, "wb").write(out)
    bank.cells = read_ncer(tmp)
    return out


def run(mode, outdir=None):
    font = Nftr(FONT)
    made = []
    for name, cells in LABELS.items():
        bank = Bank(os.path.join(TITLE_DIR, name))
        grown = relayout_cells(bank, name)
        for ci, spec in sorted(cells.items()):
            if not bank.cells[ci]:
                print("  %s cell %d: empty cell, skipped" % (name, ci))
                continue
            if spec["style"] == "framed":
                do_framed(bank, font, name, ci, spec)
            elif spec["style"] == "styled":
                do_styled(bank, font, name, ci, spec)
            else:
                do_outlined(bank, font, name, ci, spec)
        if mode == "preview":
            out = os.path.join(os.path.dirname(HERE), "work", "gfx", "en")
            os.makedirs(out, exist_ok=True)
            for ci in cells:
                if bank.cells[ci]:
                    bank.preview(ci, os.path.join(out, "%s_cell%02d.png" % (name, ci)))
            made.append(out)
        else:
            os.makedirs(outdir, exist_ok=True)
            dest = os.path.join(outdir, name + ".NCGR")
            bank.save(dest)
            made.append(dest)
            if grown is not None:
                ncer = os.path.join(outdir, name + ".NCER")
                open(ncer, "wb").write(grown)
                made.append(ncer)
    return made


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 1
    if argv[1] == "preview":
        for m in dict.fromkeys(run("preview")):
            print("previews -> %s" % m)
    elif argv[1] == "apply":
        for m in run("apply", argv[2]):
            print("wrote %s" % m)
        # the other loose title banks (options / erase-save screens)
        import options_obj
        options_obj.apply(argv[2])
        # loose copies of the Equipment quality / effect tag banks
        import equip_obj
        equip_obj.apply_loose(argv[2])
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
