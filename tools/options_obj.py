#!/usr/bin/env python3
"""Repaint text on the loose OBJ banks of the options / title sub-screens.

Unlike the sub-menu banks these are separate files (info/title/<name>.NCGR/NCLR/
NCER), so the result is written to work/gfx_out/<name>.NCGR, which build_patch.py
already installs. The painter itself is skill_obj.paint_label (write only through
a cell's own OAM entries; see that module for why).

  title_start         cell 0   the title's "START to begin!" pill   をおしてね！！
  tiop_sys_obj        cell 1   the System screen's green title bar  システム
  tiop_save_conf_obj  cell 0   the "Erase Save Data" tag            セーブデータをけす
                      cells 2, 3  the Yes / No buttons              はい / いいえ

(The System / Credits / Erase Save Data entries on the Options list are handled by
gfx_labels.py; the hint bars and captions on the option screens are background
layers, done through work/submenu_seeds.py as loose files.)

    options_obj.py apply <outdir>     write the patched NCGR files
    options_obj.py preview            contact sheet in work/gfx/options_obj/
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import skill_obj as so  # noqa: E402
from gfxtext import Bank  # noqa: E402
from bgtext import load_font  # noqa: E402
from equip_obj import paint_tag, QUALITIES, EFFECTS  # noqa: E402

BASE = os.path.dirname(HERE)
TITLE_DIR = os.path.join(BASE, "extracted", "info", "title")

# the greyed four-word hint strips of the merge map (256 px): icons x 7-25,
# 61-76, 111-127, 172-187; lettering starts 28 / 79 / 129 / 190 (かいそう runs
# to x 167)
_GREENS = (3, 5, 1, 11, 14)
# the cream pills' face colours (darker bands, lighter centre): lettering is
# anything else. The pale band (4) and the rim (a) are left out -- the
# Japanese antialiasing uses them too -- and handled by _pill's own passes.
# -- the pill's edge columns are a different shade from its rows, so an
# edge-bounded clear left the Japanese's first and last glyphs
_PILL = (0xe, 7)


# a loudspeaker with two sound waves, for the Character Creator's voice
# playback button (きく, "listen"): no word fitted the 18px after the X icon
# ("Hear" crowded it), so the user chose an icon
SPEAKER = (
    "....#.....#..",
    "...##..#...#.",
    "######..#...#",
    "######..#...#",
    "######..#...#",
    "...##..#...#.",
    "....#.....#..",
)


# 7-row pixel letters for faces too short for the font (10px capitals)
TINY = {
    "I": ("###", ".#.", ".#.", ".#.", ".#.", ".#.", "###"),
    "t": (".#.", ".#.", "###", ".#.", ".#.", ".#.", "..#"),
    "e": ("....", "....", ".##.", "#..#", "####", "#...", ".###"),
    "m": (".....", ".....", "####.", "#.#.#", "#.#.#", "#.#.#", "#.#.#"),
    "s": ("...", "...", ".##", "#..", ".#.", "..#", "##."),
}


def tiny_rows(word):
    """The word in TINY letters, one blank column between them, as rows."""
    rows = [""] * 7
    for k, ch in enumerate(word):
        for r in range(7):
            rows[r] += ("." if k else "") + TINY[ch][r]
    return tuple(rows)


def _pill(cell, word, band13=0xA):
    """Clear the pale band rows (2, 12 and 13) into the band colour and the
    right rim (the Japanese reaches it), then the face, then draw."""
    return [
        {"cell": cell, "box": (4, 2, 88, 3), "lines": [""], "inpaint": (4,)},
        {"cell": cell, "box": (4, 12, 88, 13), "lines": [""], "inpaint": (4,)},
        # row 13 carries the Japanese drop shadow too (band colours 4 / a):
        # its dots showed under the Cross Plaza / Co-op Quest / Invite titles
        # (hardware 2026-09-26). Each pill's row 13 is one band colour.
        {"cell": cell, "box": ((8, 13, 84, 14) if band13 == 4 else (6, 13, 86, 14)),
         "lines": [""], "inpaint": (band13,)},
        # (wide enough that every rim pixel finds a clean one on its row)
        {"cell": cell, "box": (76, 3, 88, 12), "lines": [""], "inpaint": (7, 4, 0xe)},
        {"cell": cell, "box": (4, 3, 86, 14), "lines": [word], "inpaint": _PILL, "ink": 1},
    ]


def _strip4(a_word):
    # the GREYED strip (grey icons, colour 10): the BG layer under it is the
    # enabled one. Words on cell rows 5-14 = screen 175-184, the same rows as
    # the BG words and centred on the icons (rows 171-187); both start at
    # x 29, 5px after the icon. (2026-09-26: the boxes had been moved down
    # on the belief this was the enabled state -- the two drifted 4px apart.)
    # かいそう is "Preview" (user: it shows each floor's state and treasure
    # points, no editing happens)
    boxes = ((27, 1, 59, 20, "Move"), (78, 1, 110, 20, a_word),
             (128, 1, 170, 20, "Preview"), (189, 1, 230, 20, "Back"))
    return [{"box": (x0, y0, x1, y1), "lines": [w], "align": "left", "indent": 2,
             "bg": 13, "ink": 12}
            for x0, y0, x1, y1, w in boxes]


BANKS = {
    # Title screen: a pill with an English "START" badge on its left end, then
    # をおしてね！！ ("press it!!") on the plain face, which is all this repaints.
    # Every tile in the cell is its own, so nothing else shares the change.
    "title_start": [
        {"cell": 0, "box": (47, 3, 135, 18), "lines": ["to begin!"], "bold": True,
         "align": "left", "indent": 5},
    ],
    # the password screen's green title tab ひみつのじゅもん ("secret spell"),
    # named "Password" after the title-menu button that opens it: face 3 on
    # rows 1-16, x 0-96 (entries 0-3; the lettering starts at x 3)
    "tise_m1_obj": [
        {"cell": 0, "entries": range(4), "box": (0, 1, 97, 17), "lines": ["Password"]},
    ],
    "tiop_sys_obj": [
        {"cell": 1, "entries": range(4), "box": (0, 1, 95, 17), "lines": ["System"]},
    ],
    "tiin_make_seles_obj": [
        # the voice-playback button: the old lettering (x 19-35, rows 5-12 on
        # the white face) cleared, a speaker icon stamped in its place
        {"cell": 6, "style": "icon", "box": (18, 4, 36, 14), "bg": 5,
         "icon": SPEAKER, "at": (21, 6), "ink": 9},
    ],
    "tiin_make_fixs_obj": [
        {"cell": 4, "box": (44, 46, 102, 61), "lines": ["Yes"]},
        {"cell": 4, "box": (152, 46, 212, 61), "lines": ["No"]},
    ],
    "chr_make/chrmake_panel": [
        {"cell": 1, "box": (3, 4, 50, 20), "lines": ["Gender"]},
        {"cell": 2, "box": (3, 4, 50, 20), "lines": ["Face"]},
        {"cell": 3, "box": (3, 4, 50, 20), "lines": ["Hairstyle"]},
        {"cell": 4, "box": (3, 4, 50, 20), "lines": ["Hair Hue"]},
        {"cell": 5, "box": (3, 4, 54, 20), "lines": ["Class"]},
        {"cell": 6, "box": (3, 4, 50, 20), "lines": ["Voice"]},
    ],
    "islet/maho_shop_m_obj": [
        # face rows 1-16 only; rows 17-19 are the bottom border and shadow,
        # which the old (2, 2, 98, 20) box painted over (hardware, 2026-09-24)
        {"cell": 0, "box": (0, 1, 98, 17), "lines": ["Shop"], "keep_edges": True},
    ],
    "islet/maho_ship_m_obj": [
        # the Ship menu's green title bar ふね: face colour 4 on rows 1-16,
        # x 0-95 (entries 0-3); rows 17-19 are its white edge and shadow
        {"cell": 0, "entries": range(4), "box": (0, 1, 96, 17), "lines": ["Ship"]},
    ],
    "cook/maho_cook_selem_obj": [
        # face rows 1-16 only; rows 17-19 are the bottom border and shadow,
        # which the old (2, 2, 98, 20) box painted over (hardware, 2026-09-24)
        {"cell": 0, "box": (0, 1, 98, 17), "lines": ["Cooking"], "keep_edges": True},
    ],
    "cook/maho_cook_seles1_obj": [
        # cell 1: R-toggle state showing "Items" (matches the BG header's own
        # "Items" translation) -- this OBJ overlaps that BG text when this
        # toggle state is active, which is why leaving it in Japanese looked
        # like leftover untranslated fragments beside the English BG caption
        # The white face is x 0-45, rows 0-16 (the orange R pill starts at
        # x 46). The old (2, 4, 50, 20) box painted white over the R's left
        # columns, centred the word too far right and too low, and left the
        # Japanese tops on row 3 (hardware 2026-09-26).
        {"cell": 1, "box": (0, 0, 46, 17), "lines": ["Items"]},
        # cell 3: the list's column headers とれるワールド / ばしょ ("World" /
        # "Floor" -- its entries read 1~5F), as on the Workshop's tab bar (see there): painted only through
        # the private entries under each word, 14-19 and 4-7 (16 rows + 8 rows).
        # The face is rows 10-18 between bands on rows 9 and 19 that the
        # Japanese also crosses, so rowfill.
        {"cell": 3, "entries": range(14, 20), "box": (24, 9, 104, 20),
         "lines": ["World"], "rowfill": True, "shared_ok": False},
        {"cell": 3, "entries": (4, 5, 6, 7), "box": (152, 9, 192, 20),
         "lines": ["Floor"], "rowfill": True, "shared_ok": False},
        # cell 4: the R-hint pill back to Items. Its face is only rows 4-11 (the
        # old 1-15 box cleared the pill's borders and right end, seen on hardware
        # 2026-09-24); the font's capitals are 10px, so the tops of I/t clip
        # Hardware then showed it low and right, with the tops of the Japanese
        # left on the band row above: now drawn in 7-row pixel letters (TINY)
        # on rows 4-10, centred where the Japanese sat (x 24-65), and the band
        # row 3 cleaned of the Japanese tops.
        {"cell": 4, "style": "icon", "box": (17, 4, 81, 12), "bg": 1,
         "band": (3, (17, 81), 14), "icon": tiny_rows("Items"), "at": (34, 4),
         "ink": 9},
    ],
    "product/maat_make_top_obj": [
        # face rows only: rows 16-23 are one bottom-border/shadow strip (tile 0)
        # shared with the Craft and Upgrade pills, and clearing it painted their
        # white border and grey shadow pink
        {"cell": 0, "box": (2, 1, 96, 16), "lines": ["Workshop"]},
        # the pill's face is x 1-45, y 1-16; keep_edges clears only inside it
        # (the old 2-20 box squared the rounded ends and cut the outline, and
        # the two pills share their end-cap tiles, so each damaged the other)
        {"cell": 2, "box": (1, 1, 46, 17), "lines": ["Craft"], "keep_edges": True},
        {"cell": 3, "box": (1, 1, 46, 17), "lines": ["Upgrade"], "keep_edges": True},
        # cell 6: the greyed copy of the hint bar shown while the Craft /
        # Upgrade confirm is up. It sits exactly over the BG strip (same x,
        # y + 168) on an opaque pink band, so it takes the BG seeds' boxes and
        # indents (work/submenu_seeds.py maat_make_top_bg): the old boxes
        # stopped short of the Japanese (":" / "(" / "も" left, hardware
        # 2026-09-25) and centred OK away from its icon.
        {"cell": 6, "box": (26, 2, 62, 22), "lines": ["Move"], "align": "left", "indent": 3},
        {"cell": 6, "box": (85, 2, 128, 22), "lines": ["OK"], "align": "left", "indent": 2},
        {"cell": 6, "box": (149, 2, 184, 22), "lines": ["Back"], "align": "left", "indent": 3},
    ],
    "product/maat_make_rcp_obj": [
        # the Japanese sits on rows 6-15 (top=2 put the English 4px high, seen
        # on hardware 2026-09-24) and starts at x 2 (x 3 left a sliver)
        {"cell": 0, "box": (1, 0, 56, 24), "lines": ["Attack"], "ink_rgb": (255, 255, 255),
         "style": "flat", "top": 6},
        {"cell": 1, "box": (1, 0, 56, 24), "lines": ["Defense"], "ink_rgb": (255, 255, 255),
         "style": "flat", "top": 6},
        # cell 2: the list's column headers とれるワールド / ばしょ ("World" /
        # "Floor" -- its entries read 1~5F). The bar's plain stretches are one 8x16 tile (52) and one
        # 16x8 tile (54) repeated 7 and 11 times, so painting through them
        # repeated the lettering as ticks along the bar and browned its cream
        # border. The Japanese lies wholly on private entries -- 17-19 (x 24-103)
        # and 9-10 (x 152-191) -- so only those are painted, on the face rows
        # 9-19. The right one is 40px: "Location" (43px) does not fit.
        {"cell": 2, "entries": (17, 18, 19), "box": (24, 9, 104, 20),
         "lines": ["World"], "shared_ok": False},
        {"cell": 2, "entries": (9, 10), "box": (152, 9, 192, 20),
         "lines": ["Floor"], "shared_ok": False},
        # face rows 3-12 only; the old 1-15 box cleared the pill's borders and
        # right end (the same template as cooking's R-hint pill, cell 4 there)
        {"cell": 3, "box": (17, 3, 82, 14), "lines": ["Materials"], "keep_edges": True},
    ],
    "islet/maho_job_sele_obj": [
        # In-dungeon Class-change screen's title banner (a single cell, 8 OAM
        # entries, holding just this pill -- see README's Style/Class-change
        # section). Not the Character Creator's "Style"->"Class" chrmake_panel
        # cell; the menu-list art (Mage/Thief/Priest/Cancel) is a separate,
        # still-unidentified archive.
        # face rows 1-16 only (see the Shop pill)
        {"cell": 0, "box": (0, 1, 98, 17), "lines": ["Class Change"], "keep_edges": True},
    ],
    "islet/maho_isart_sele_obj": [
        # face x 3-87, y 3-12; rows 2 and 13 are the pill's highlight bands, which
        # the old 4-20 box painted over (the damaged left end and lower edge)
        {"cell": 2, "box": (3, 2, 88, 14), "lines": ["Done!"], "keep_edges": True},
        # cell 4: the grey/dimmed hint bar shown while the exit confirm dialog is
        # up (a separate baked-text sprite from the normal coloured BG hint strip;
        # easy to miss since it's blank until that state is triggered). Unlike the
        # other labels here, the words sit directly on transparency (the icons
        # show through beneath/around them, not a filled pill) -- paint_label's
        # "only repaint pixels that were already opaque" rule leaves any new-glyph
        # pixel landing on that transparent gap unclipped, i.e. dropped. "outlined"
        # style (clear the icon-free x-gap to transparent, then stamp the new
        # glyphs directly, same as gfx_labels.py's free-standing captions) is the
        # right tool here instead. Gaps between the D-pad/A/B icons (checked
        # pixel-by-pixel, not eyeballed -- the old text sat closer to the icons
        # than it looked): 17-56 (Move), 73-119 (OK), 135-168 (Back), all full
        # cell height (0-16).
        # The greyed words must land exactly on the BG strip's words, which they
        # cover (maho_isart_sele_bg: pens at x 30 / 84 / 146). This cell is
        # drawn 7px right of its own coordinates (its icons end at 17/72/134,
        # the BG's at 24/80/141), so the pens here are 23 / 77 / 139. Centred
        # in the gaps, "OK" missed and both showed (hardware 2026-09-24).
        # Hardware then showed the BG words peeking out 1px: the pens (from
        # the static comparison, 23 / 77 / 139) move 1px left and 1px down.
        {"cell": 4, "style": "outlined", "box": (17, 0, 56, 16), "pen": 22, "dy": 1,
         "lines": ["Move"], "ink": 9, "outline": 14},
        {"cell": 4, "style": "outlined", "box": (73, 0, 119, 16), "pen": 76, "dy": 1,
         "lines": ["OK"], "ink": 9, "outline": 14},
        {"cell": 4, "style": "outlined", "box": (135, 0, 168, 16), "pen": 138, "dy": 1,
         "lines": ["Back"], "ink": 9, "outline": 14},
    ],
    # ---- wireless multiplayer / merge sprite labels (never painted until
    # 2026-09-24). Gradient pills use rowfill (each row keeps its own colour);
    # the greyed hint strips sit over a curve of greens, so only lettering
    # pixels are replaced (inpaint = the strip's backdrop indices). Words start
    # 3px after their icon, as the Japanese does. かいそう is "Edit" (arranging
    # the world); "Remodel" did not fit the 36px after the X icon.
    "connect/time_mode_mlt_inv_obj": [
        *_pill(4, "Cross Plaza"),
        {"cell": 5, "box": (15, 2, 56, 15), "lines": ["Start"], "align": "left", "indent": 2, "rowfill": True, "ink": 4},
        {"cell": 6, "box": (5, 2, 89, 13), "lines": ["Start!"], "keep_edges": True, "rowfill": True, "ink": 4},
        *_pill(7, "Invite", 4),
        *_pill(8, "Go Visit"),
        *_pill(9, "Present"),
        *_pill(10, "Co-op Quest", 4),
    ],
    "connect/time_mode_mrg_mapm_obj": [
        {"cell": 2, "box": (0, 2, 96, 16), "lines": ["Dungeon Merge"], "inpaint": (4,), "ink": 11},
    ] + [dict(w, cell=c) for c, words in ((8, ("Merge",)), (9, ("OK",)), (10, ("Erase",)))
         for w in _strip4(words[0])],
    "merge/time_mode_mrg_mapm_obj": [
        {"cell": 2, "box": (0, 2, 96, 16), "lines": ["World Cross"], "inpaint": (1,), "ink": 10},
    ] + [dict(w, cell=c) for c, words in ((8, ("Cross",)), (9, ("OK",)), (10, ("Erase",)))
         for w in _strip4(words[0])],
    "merge/time_mode_mrg_maps_obj": [
        # the greyed strip: words on cell rows 5-14, as _strip4
        # the backdrop behind Move is plain colour 3: keeping the curve's greens
        # (11 among them) kept the Japanese's own colour-11 pixels -- a dash
        # after "Move" (hardware 2026-09-26)
        {"cell": 0, "box": (27, 1, 60, 21), "lines": ["Move"], "align": "left", "indent": 2,
         "inpaint": (3,), "ink": 4},
        # up to x 112 the backdrop is plain colour 3 too: clear the Japanese
        # there first (its colour-11 pixels survive the curve's palette)
        {"cell": 0, "box": (79, 1, 112, 22), "lines": [""], "inpaint": (3,)},
        {"cell": 0, "box": (112, 8, 118, 9), "lines": [""], "bg": 3},
        {"cell": 0, "box": (79, 1, 172, 21), "lines": ["Pick Dungeon"], "align": "left", "indent": 1,
         "inpaint": _GREENS, "ink": 4},
    ],
    "title/time_mode_mlt_obj": [
        {"cell": 0, "box": (0, 2, 97, 16), "lines": ["Multiplayer"], "inpaint": (7,), "ink": 8},
        {"cell": 6, "box": (0, 2, 97, 16), "lines": ["Gift Trade"], "inpaint": (7,), "ink": 8},
        {"cell": 1, "box": (5, 5, 148, 23), "lines": ["Invite"], "keep_edges": True, "ink": 8},
        {"cell": 2, "box": (5, 5, 148, 23), "lines": ["Go Visit"], "keep_edges": True, "ink": 8},
        {"cell": 3, "box": (4, 4, 116, 18), "lines": ["Invite"], "keep_edges": True, "ink": 4},
        {"cell": 4, "box": (4, 4, 116, 18), "lines": ["Go Visit"], "keep_edges": True, "ink": 4},
    ],
    "title/time_mode_mrg_obj": [
        # the mode tab: マージ (Merge), called World Cross like the feature itself
        {"cell": 0, "box": (0, 2, 97, 16), "lines": ["World Cross"], "inpaint": (7,), "ink": 8},
        # "Host", not "Create": unselected, this pill is short and a console
        # icon (a separate sprite) covers it from x ~98, so the words must end
        # by ~96 -- "Create Cross Plaza" (96px) ran under it (hardware)
        {"cell": 1, "box": (5, 5, 148, 23), "lines": ["Host Cross Plaza"], "keep_edges": True, "ink": 8},
        {"cell": 2, "box": (5, 5, 148, 23), "lines": ["Go to Cross Plaza"], "keep_edges": True, "ink": 8},
        # unselected: left-aligned from x 5 as the Japanese was, clear of the icon
        {"cell": 3, "box": (4, 4, 116, 18), "lines": ["Host Cross Plaza"], "keep_edges": True, "ink": 4,
         "align": "left", "indent": 1},
        {"cell": 4, "box": (4, 4, 116, 18), "lines": ["Go to Cross Plaza"], "keep_edges": True, "ink": 4,
         "align": "left", "indent": 1},
    ],
    "title/time_mode_qst_obj": [
        {"cell": 0, "box": (0, 2, 97, 16), "lines": ["Co-op Quest"], "inpaint": (1,), "ink": 14},
    ],
    # The Workshop's quality and effect tags (never painted until 2026-09-24).
    # Cells 0-4: わるい / ふつう / よい / すごい / さいこう (the equipment screen's
    # ladder, plus "Bad"). Cells 5-36: the 32 effect nicknames in effect-id
    # order (cell = 5 + id; キラキラ at 14 is the kill-restores-MP effect, as on
    # the Sparkle Fan); only the ids with lettering are painted, with
    # equip_obj's short forms. Cell 36 is id 31, パチパチ (Sleep resist): the
    # nicknames are listed in data_item/equip_effect.dat.
    "product/item_effect": [
        {"cell": ci, "style": "flat", "box": (2, 2, 44, 12), "lines": [w],
         "ink_rgb": (132, 82, 8), "top": 2}
        for ci, w in enumerate(("Bad",) + tuple(QUALITIES[:4]))
    ] + [
        {"cell": 5 + i, "style": "banded", "box": (1, 1, 31, 13), "lines": [EFFECTS[i][1]],
         "bgcol": 1, "ink_rgb": (132, 82, 8), "top": 2}
        for i in (0, 1, 2, 3, 4, 9, 10, 12, 13, 15, 16, 17, 18, 31)
    ],
    # Tailor: げんざい / したてご on the two scrolls (the lettering sits in a
    # lower-priority entry under the transparent middle of the scroll art)
    "tailor/maho_tail_m1_obj": [
        {"cell": 1, "box": (13, 7, 84, 21), "lines": ["Current"], "rowfill": True},
        {"cell": 2, "box": (13, 7, 84, 21), "lines": ["After"], "rowfill": True},
    ],
    "tiop_save_conf_obj": [
        # from x 0: the Japanese's antialiasing reaches x 1 (rows 7-8), and the
        # old x 2 start left it as a grey line before the text (hardware)
        {"cell": 0, "entries": range(4), "box": (0, 2, 96, 16),
         "lines": ["Erase Save Data"]},
        {"cell": 2, "entries": range(2), "box": (5, 5, 68, 24), "lines": ["Yes"]},
        {"cell": 3, "entries": range(2), "box": (5, 5, 68, 24), "lines": ["No"]},
    ],
}


def paint_bank(name):
    sub, _, base = name.rpartition("/")
    bank = Bank(os.path.join(TITLE_DIR if not sub else
                             os.path.join(os.path.dirname(TITLE_DIR), sub), base))
    font = load_font()
    for spec in BANKS[name]:
        spec = dict(spec)
        ci = spec["cell"]
        if spec.get("style") == "outlined":
            bank.fill(ci, spec["box"], 0)
            box = spec["box"]
            if "pen" in spec:
                # draw from this x rather than centred in the cleared box, so
                # the word lands exactly on a BG word it must cover
                width = bank.text_width(font, spec["lines"][0], 1)
                dy = spec.get("dy", 0)
                box = (spec["pen"], box[1] + dy, spec["pen"] + width, box[3] + dy)
            ok = bank.draw_outlined(ci, font, spec["lines"], box,
                                    spec["ink"], spec["outline"], scale=1)
            print("  cell %2d  %-14s outlined ink=%d outline=%d%s"
                  % (ci, "/".join(spec["lines"]), spec["ink"], spec["outline"],
                     "" if ok else "  !! does not fit"))
            continue
        if spec.get("style") == "icon":
            # clear the box to the face colour, then stamp a small bitmap;
            # `band` = (row, (x0, x1), colour) also resets one band row
            bank.fill(ci, spec["box"], spec["bg"])
            if "band" in spec:
                by, (bx0, bx1), bc = spec["band"]
                bank.fill(ci, (bx0, by, bx1, by + 1), bc)
            ax, ay = spec["at"]
            for dy, row in enumerate(spec["icon"]):
                for dx, ch in enumerate(row):
                    if ch == "#":
                        bank.put(ci, ax + dx, ay + dy, spec["ink"])
            print("  cell %2d  icon" % ci)
            continue
        if spec.get("style") == "banded":
            # a two-tone pill (lighter top band, darker bottom band): each row's
            # fill is read from the pill's own edge column (equip_obj.paint_tag)
            ok = paint_tag(bank, font, ci, spec["lines"][0], spec["box"],
                           bgcol=spec.get("bgcol"), ink_rgb=spec["ink_rgb"],
                           top=spec.get("top", 2))
            print("  cell %2d  %-14s banded%s" % (ci, spec["lines"][0],
                                                "" if ok else "  !! does not fit"))
            continue
        if spec.get("style") == "flat":
            # a gradient/coloured pill with light (usually white) lettering and
            # no dark ink -- see equip_obj.paint_tag's ink_rgb docstring
            ok = paint_tag(bank, font, ci, spec["lines"][0], spec["box"],
                           ink_rgb=spec["ink_rgb"], flat=True,
                           top=spec.get("top", 2))
            print("  cell %2d  %-14s flat ink_rgb=%s%s"
                  % (ci, spec["lines"][0], spec["ink_rgb"], "" if ok else "  !! does not fit"))
            continue
        # a spec may limit itself to some of the cell's OAM entries (a bar
        # whose plain stretches reuse one tile; see the Workshop tab bar)
        spec["entries"] = list(spec.get("entries", range(len(bank.cells[ci]))))
        spec.setdefault("shared_ok", True)
        so.paint_label(bank, font, spec)
    return bank


def apply(outdir):
    os.makedirs(outdir, exist_ok=True)
    for name in BANKS:
        bank = paint_bank(name)
        dest = os.path.join(outdir, name + ".NCGR")
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        bank.save(dest)
        print("  wrote", dest)


def preview():
    from PIL import Image
    out = os.path.join(BASE, "work", "gfx", "options_obj")
    os.makedirs(out, exist_ok=True)
    ims = []
    for name, specs in BANKS.items():
        bank = paint_bank(name)
        for spec in specs:
            ims.append(so.render(bank, spec["cell"]))
    sheet = Image.new("RGBA", (max(i.width for i in ims) * 3 + 8,
                               sum(i.height * 3 + 8 for i in ims)), (110, 110, 110, 255))
    y = 4
    for im in ims:
        j = im.resize((im.width * 3, im.height * 3), Image.NEAREST)
        sheet.paste(j, (4, y), j)
        y += j.height + 8
    sheet.save(os.path.join(out, "options_obj.png"))
    print("wrote", os.path.join(out, "options_obj.png"))


def main(argv):
    if len(argv) >= 3 and argv[1] == "apply":
        apply(argv[2])
        return 0
    if len(argv) >= 2 and argv[1] == "preview":
        preview()
        return 0
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
